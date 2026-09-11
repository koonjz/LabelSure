"""
LabelSure — OCR Engine
Primary: PaddleOCR (supports English + Indic scripts via multilingual models)
Fallback: Tesseract (pytesseract)

Returns raw OCR results with per-box confidence scores.
If overall confidence is low, the caller should flag the scan as NEEDS_REVIEW.
"""
from __future__ import annotations
import logging
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
_paddle_instance: Optional["PaddleOCR"] = None


def _get_paddle() -> "PaddleOCR":
    global _paddle_instance
    if _paddle_instance is None:
        # lang='en' — switch to 'ml' or 'hi' or 'ch' for Indic/multilingual
        # We use 'en' as default; language is detected first then re-run with correct model
        _paddle_instance = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _paddle_instance


def _get_paddle_for_lang(lang_code: str) -> "PaddleOCR":
    """Return a PaddleOCR instance tuned for the detected language."""
    # PaddleOCR language codes: en, ch, hi (Hindi), ta (Tamil), te (Telugu),
    # kn (Kannada), mr (Marathi — uses hi model), etc.
    paddle_lang_map = {
        "en": "en",
        "hi": "hi",
        "ta": "ta",
        "te": "te",
        "kn": "kn",
        "bn": "en",   # Bengali — use en as fallback (no official Paddle model)
        "ml": "ml",   # Malayalam (if available)
    }
    pl = paddle_lang_map.get(lang_code, "en")
    return PaddleOCR(use_angle_cls=True, lang=pl, show_log=False)


def run_paddleocr(image_path: str, lang_code: str = "en") -> OCRResult:
    """Run PaddleOCR on the image and return an OCRResult."""
    if not _PADDLE_AVAILABLE:
        raise RuntimeError("PaddleOCR is not installed.")

    ocr = _get_paddle_for_lang(lang_code)
    raw = ocr.ocr(image_path, cls=True)

    boxes: list[OCRBox] = []
    if raw and raw[0]:
        for line in raw[0]:
            bbox, (text, conf) = line
            boxes.append(OCRBox(text=text, confidence=float(conf), bbox=bbox))

    return _build_result(boxes, engine="paddleocr")


# ─────────────────────────────────────────────────────────────────────────────
# Tesseract wrapper (fallback)
# ─────────────────────────────────────────────────────────────────────────────

def run_tesseract(image_path: str, lang_code: str = "en") -> OCRResult:
    """Run Tesseract OCR on the image and return an OCRResult."""
    if not _TESSERACT_AVAILABLE:
        raise RuntimeError("pytesseract is not installed.")

    # Always include English ('eng') so Latin numbers & keywords (MRP, Net Qty) are never missed
    tess_lang_map = {
        "en": "eng",
        "hi": "eng+hin",
        "ta": "eng+tam",
        "te": "eng+tel",
        "kn": "eng+kan",
        "bn": "eng+ben",
        "ml": "eng+mal",
        "mr": "eng+mar",
    }
    tess_lang = tess_lang_map.get(lang_code, "eng")

    pil_img = PILImage.open(image_path)
    # Fix smartphone camera EXIF orientation (e.g. 90 deg rotated phone captures)
    try:
        from PIL import ImageOps
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass

    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    raw_text = ""
    boxes: list[OCRBox] = []

    try:
        # Standard full-page text pass
        raw_text = pytesseract.image_to_string(pil_img, lang=tess_lang)
    except Exception as e:
        logger.warning("Tesseract primary OCR failed: %s", e)

    # If raw_text is sparse, attempt contrast enhancement pass
    if len(raw_text.strip()) < 25:
        try:
            from PIL import ImageOps
            gray = ImageOps.grayscale(pil_img)
            enhanced = ImageOps.autocontrast(gray)
            alt_text = pytesseract.image_to_string(enhanced, lang=tess_lang)
            if len(alt_text.strip()) > len(raw_text.strip()):
                raw_text = alt_text
        except Exception:
            pass

    # Extract word boxes
    try:
        df = pytesseract.image_to_data(
            pil_img,
            lang=tess_lang,
            output_type=pytesseract.Output.DATAFRAME,
        )
        df = df[df["conf"] > 0].dropna(subset=["text"])
        df = df[df["text"].str.strip() != ""]
        for _, row in df.iterrows():
            conf_norm = float(row["conf"]) / 100.0
            bbox = [row["left"], row["top"], row["width"], row["height"]]
            boxes.append(OCRBox(text=str(row["text"]), confidence=conf_norm, bbox=bbox))
    except Exception as e:
        logger.warning("Tesseract bounding box extraction failed: %s", e)

    return _build_result(boxes, engine="tesseract", text_override=raw_text)


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
            return run_paddleocr(image_path, lang_code=lang_code)
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


