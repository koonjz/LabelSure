"""
LabelSure — OCR Engine
Primary: PaddleOCR (supports English + Indic scripts via multilingual models)
         Runs TWICE — once with 'en' model and once with an Indic model —
         then merges the results for maximum field coverage.
Fallback: Tesseract (pytesseract) with multiple pre-processing passes.

Returns raw OCR results with per-box confidence scores.
If overall confidence is low, the caller should flag the scan as NEEDS_REVIEW.
"""
from __future__ import annotations
import logging
import re
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Lazy imports — PaddleOCR / Tesseract may not be installed in all environments
# ─────────────────────────────────────────────────────────────────────────────
try:
    from paddleocr import PaddleOCR
    _PADDLE_AVAILABLE = True
except ImportError:
    _PADDLE_AVAILABLE = False
    logger.warning("PaddleOCR not available — will use Tesseract fallback.")

try:
    import pytesseract
    from PIL import Image as PILImage
    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available — no OCR fallback.")

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────
from dataclasses import dataclass, field


@dataclass
class OCRBox:
    """Single text region detected by OCR."""
    text: str
    confidence: float           # 0.0 – 1.0
    bbox: list                  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] or [x,y,w,h]


@dataclass
class OCRResult:
    """Aggregated OCR output for a whole image."""
    boxes: list[OCRBox] = field(default_factory=list)
    full_text: str = ""
    min_confidence: float = 1.0
    avg_confidence: float = 1.0
    engine_used: str = "none"


# ─────────────────────────────────────────────────────────────────────────────
# PaddleOCR wrapper
# ─────────────────────────────────────────────────────────────────────────────
# Cache one instance per language to avoid redundant model downloads
_paddle_instances: dict[str, "PaddleOCR"] = {}

# PaddleOCR language codes for common Indian languages
_PADDLE_LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "kn": "kn",
    "bn": "en",   # Bengali — use en as fallback (no official Paddle model)
    "ml": "ml",   # Malayalam
    "mr": "hi",   # Marathi uses Hindi model
    "gu": "en",   # Gujarati — fallback
    "pa": "en",   # Punjabi — fallback
}


def _get_paddle(lang_code: str = "en") -> "PaddleOCR":
    """Return a cached PaddleOCR instance for the given language."""
    pl = _PADDLE_LANG_MAP.get(lang_code, "en")
    if pl not in _paddle_instances:
        _paddle_instances[pl] = PaddleOCR(use_angle_cls=True, lang=pl, show_log=False)
    return _paddle_instances[pl]


def run_paddleocr(image_path: str, lang_code: str = "en") -> OCRResult:
    """
    Run PaddleOCR on the image.

    For Indian food labels we ALWAYS run the English model first (captures
    Latin text, numbers, MRP, weight) and then merge with an Indic model if
    the detected language is non-English.  This prevents either model from
    dropping fields that the other can read.
    """
    if not _PADDLE_AVAILABLE:
        raise RuntimeError("PaddleOCR is not installed.")

    # --- Pass 1: English model (always run for Latin text / numbers) ---
    en_ocr = _get_paddle("en")
    raw_en = en_ocr.ocr(image_path, cls=True)
    boxes_en: list[OCRBox] = []
    if raw_en and raw_en[0]:
        for line in raw_en[0]:
            bbox, (text, conf) = line
            boxes_en.append(OCRBox(text=text, confidence=float(conf), bbox=bbox))

    # --- Pass 2: Indic model (only if language is non-English) ---
    boxes_indic: list[OCRBox] = []
    if lang_code != "en":
        try:
            indic_ocr = _get_paddle(lang_code)
            raw_indic = indic_ocr.ocr(image_path, cls=True)
            if raw_indic and raw_indic[0]:
                for line in raw_indic[0]:
                    bbox, (text, conf) = line
                    boxes_indic.append(OCRBox(text=text, confidence=float(conf), bbox=bbox))
        except Exception as exc:
            logger.warning("PaddleOCR Indic pass (%s) failed: %s", lang_code, exc)

    # --- Merge: prefer whichever has more content, then append unique lines ---
    merged_boxes = _merge_paddle_boxes(boxes_en, boxes_indic)
    return _build_result(merged_boxes, engine="paddleocr")


def _merge_paddle_boxes(boxes_en: list[OCRBox], boxes_indic: list[OCRBox]) -> list[OCRBox]:
    """
    Merge English and Indic OCR boxes.
    Deduplicates by text content (case-insensitive, after stripping whitespace).
    Prefers the higher-confidence box when the same text appears in both.
    """
    if not boxes_indic:
        return boxes_en
    if not boxes_en:
        return boxes_indic

    seen_texts: dict[str, OCRBox] = {}
    for box in boxes_en:
        key = re.sub(r"\s+", " ", box.text.strip().lower())
        if key:
            seen_texts[key] = box

    for box in boxes_indic:
        key = re.sub(r"\s+", " ", box.text.strip().lower())
        if not key:
            continue
        if key in seen_texts:
            # Keep the one with higher confidence
            if box.confidence > seen_texts[key].confidence:
                seen_texts[key] = box
        else:
            seen_texts[key] = box

    return list(seen_texts.values())


# ─────────────────────────────────────────────────────────────────────────────
# Image pre-processing helpers for Tesseract
# ─────────────────────────────────────────────────────────────────────────────

def _preprocess_pil(pil_img) -> list:
    """
    Return a list of pre-processed PIL images to feed to Tesseract in sequence.
    Each variant is optimised for a different image quality scenario.
    """
    from PIL import Image, ImageOps, ImageFilter
    variants = []

    # Fix EXIF rotation from smartphone cameras
    try:
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass

    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    # Variant 0: original (RGB → keep for reference)
    variants.append(pil_img)

    # Variant 1: grayscale + autocontrast
    gray = ImageOps.grayscale(pil_img)
    contrast = ImageOps.autocontrast(gray)
    variants.append(contrast)

    # Variant 2: grayscale + sharpened
    sharpened = gray.filter(ImageFilter.SHARPEN)
    variants.append(sharpened)

    # Variant 3: adaptive threshold via OpenCV (best for printed labels)
    if _CV2_AVAILABLE:
        try:
            import numpy as np
            img_np = np.array(gray)
            thresh = cv2.adaptiveThreshold(
                img_np, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 21, 10
            )
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh, h=10)
            variants.append(Image.fromarray(denoised))
        except Exception:
            pass

    # Variant 4: upscaled 2× (helps with small text)
    try:
        w, h = gray.size
        big = gray.resize((w * 2, h * 2), Image.LANCZOS)
        variants.append(big)
    except Exception:
        pass

    return variants


# ─────────────────────────────────────────────────────────────────────────────
# Tesseract wrapper (fallback)
# ─────────────────────────────────────────────────────────────────────────────

def run_tesseract(image_path: str, lang_code: str = "en") -> OCRResult:
    """Run Tesseract OCR with multiple pre-processing passes. Returns best result."""
    if not _TESSERACT_AVAILABLE:
        raise RuntimeError("pytesseract is not installed.")

    # Always include English ('eng') so Latin numbers & keywords are never missed
    tess_lang_map = {
        "en": "eng",
        "hi": "eng+hin",
        "ta": "eng+tam",
        "te": "eng+tel",
        "kn": "eng+kan",
        "bn": "eng+ben",
        "ml": "eng+mal",
        "mr": "eng+mar",
        "gu": "eng+guj",
        "pa": "eng+pan",
    }
    tess_lang = tess_lang_map.get(lang_code, "eng")

    pil_img = PILImage.open(image_path)
    variants = _preprocess_pil(pil_img)

    best_text = ""
    all_texts: list[str] = []

    for variant in variants:
        try:
            t = pytesseract.image_to_string(
                variant,
                lang=tess_lang,
                config="--oem 3 --psm 3",
            )
            all_texts.append(t)
            if len(t.strip()) > len(best_text.strip()):
                best_text = t
        except Exception as exc:
            logger.debug("Tesseract variant pass failed: %s", exc)

    # Merge all texts: keep unique lines across all passes
    merged_text = _merge_ocr_texts(all_texts)
    if len(merged_text.strip()) > len(best_text.strip()):
        best_text = merged_text

    # Extract word boxes (use original image for accurate coords)
    boxes: list[OCRBox] = []
    try:
        df = pytesseract.image_to_data(
            variants[1],  # autocontrast variant usually most stable
            lang=tess_lang,
            output_type=pytesseract.Output.DATAFRAME,
            config="--oem 3 --psm 3",
        )
        df = df[df["conf"] > 20].dropna(subset=["text"])
        df = df[df["text"].str.strip() != ""]
        for _, row in df.iterrows():
            conf_norm = float(row["conf"]) / 100.0
            bbox = [row["left"], row["top"], row["width"], row["height"]]
            boxes.append(OCRBox(text=str(row["text"]), confidence=conf_norm, bbox=bbox))
    except Exception as exc:
        logger.warning("Tesseract bounding box extraction failed: %s", exc)

    return _build_result(boxes, engine="tesseract", text_override=best_text)


def _merge_ocr_texts(texts: list[str]) -> str:
    """
    Merge multiple OCR text outputs by collecting unique non-empty lines.
    Lines already present (case-insensitive, stripped) are de-duplicated.
    """
    seen: set[str] = set()
    merged: list[str] = []
    for text in texts:
        for line in text.splitlines():
            normalized = re.sub(r"\s+", " ", line.strip().lower())
            if normalized and normalized not in seen:
                seen.add(normalized)
                merged.append(line.strip())
    return "\n".join(merged)


# ─────────────────────────────────────────────────────────────────────────────
# Unified entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_ocr(image_path: str, lang_code: str = "en") -> OCRResult:
    """
    Run OCR with PaddleOCR (preferred) or Tesseract (fallback).

    Args:
        image_path: Absolute or relative path to the image file.
        lang_code:  ISO-639-1 language code (e.g. 'en', 'hi', 'ta').

    Returns:
        OCRResult with per-box text, confidence scores, and full concatenated text.
    """
    if _PADDLE_AVAILABLE:
        try:
            result = run_paddleocr(image_path, lang_code=lang_code)
            # If PaddleOCR extracted very little text, also try Tesseract and merge
            if _TESSERACT_AVAILABLE and len(result.full_text.strip()) < 50:
                logger.info("PaddleOCR got sparse text (%d chars), also running Tesseract.",
                            len(result.full_text.strip()))
                try:
                    tess_result = run_tesseract(image_path, lang_code=lang_code)
                    if len(tess_result.full_text.strip()) > len(result.full_text.strip()):
                        # Merge: use Tesseract text but keep PaddleOCR boxes if better
                        merged_text = _merge_ocr_texts([result.full_text, tess_result.full_text])
                        combined_boxes = result.boxes + tess_result.boxes
                        return _build_result(combined_boxes, engine="paddleocr+tesseract",
                                             text_override=merged_text)
                except Exception as te:
                    logger.warning("Tesseract merge pass failed: %s", te)
            return result
        except Exception as e:
            logger.warning(f"PaddleOCR failed ({e}), falling back to Tesseract.")

    if _TESSERACT_AVAILABLE:
        return run_tesseract(image_path, lang_code=lang_code)

    # Neither available — return empty result (triggers NEEDS_REVIEW)
    logger.error("No OCR engine available (PaddleOCR and Tesseract both failed/missing).")
    return OCRResult(
        boxes=[],
        full_text="",
        min_confidence=0.0,
        avg_confidence=0.0,
        engine_used="none",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_result(boxes: list[OCRBox], engine: str, text_override: Optional[str] = None) -> OCRResult:
    if text_override and text_override.strip():
        full_text = text_override.strip()
    else:
        full_text = "\n".join(b.text for b in boxes)

    if boxes:
        confidences = [b.confidence for b in boxes]
        min_conf = min(confidences)
        avg_conf = sum(confidences) / len(confidences)
    elif full_text:
        min_conf = 0.85
        avg_conf = 0.85
    else:
        min_conf = 0.0
        avg_conf = 0.0

    return OCRResult(
        boxes=boxes,
        full_text=full_text,
        min_confidence=min_conf,
        avg_confidence=avg_conf,
        engine_used=engine,
    )
