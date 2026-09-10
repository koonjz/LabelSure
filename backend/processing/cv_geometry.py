"""
LabelSure — Computer Vision Geometry Engine
Uses OpenCV to estimate the printed height of numerals/letters on the label.

Approach:
  1. Pre-process: grayscale → threshold → find contours of text regions.
  2. For each text bounding box returned by OCR, measure its pixel height.
  3. Convert pixel height → mm using:
       - Known DPI (if device provides EXIF DPI), or
       - Reference-object calibration (user photographs a ruler or standard card), or
       - Known package height (user enters package dimensions in the app).
  4. Return the minimum measured font height across all MRP/net-quantity numeral boxes.

If calibration data is unavailable, returns None so the rules engine skips Rule 7
and emits an INFO result rather than a false verdict.
"""
from __future__ import annotations
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False
    logger.warning("OpenCV not available — CV geometry measurements will be skipped.")

from backend.processing.ocr_engine import OCRBox


def measure_font_heights_px(image_path: str, ocr_boxes: list[OCRBox]) -> list[float]:
    """
    Measure pixel heights of each OCR bounding box in the image.

    For PaddleOCR boxes: bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    For Tesseract boxes: bbox is [left, top, width, height]

    Returns list of pixel heights, one per OCR box.
    """
    if not _CV2_AVAILABLE:
        return []

    heights_px: list[float] = []
    for box in ocr_boxes:
        bbox = box.bbox
        if not bbox:
            continue
        try:
            if isinstance(bbox[0], (list, tuple)):
                # PaddleOCR quad format: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                ys = [pt[1] for pt in bbox]
                height_px = max(ys) - min(ys)
            else:
                # Tesseract [left, top, width, height]
                height_px = float(bbox[3])
            heights_px.append(float(height_px))
        except (IndexError, TypeError):
            continue

    return heights_px


def px_to_mm(pixels: float, dpi: float) -> float:
    """Convert pixel count to millimetres given DPI."""
    return (pixels / dpi) * 25.4


def calibrate_dpi_from_reference(
    image_path: str,
    reference_width_mm: float,
    reference_width_px: float,
) -> float:
    """
    Compute effective DPI from a reference object photographed alongside the label.

    Args:
        image_path:          Path to the image (unused here but kept for API consistency).
        reference_width_mm:  Known physical width of the reference object (e.g. credit card = 85.6 mm).
        reference_width_px:  Measured pixel width of the reference object in the image.

    Returns:
        Effective DPI (dots per inch).
    """
    if reference_width_mm <= 0 or reference_width_px <= 0:
        raise ValueError("Reference dimensions must be positive.")
    dpi = (reference_width_px / reference_width_mm) * 25.4
    return dpi


def measure_min_font_height_mm(
    image_path: str,
    ocr_boxes: list[OCRBox],
    dpi: Optional[float] = None,
    reference_width_mm: Optional[float] = None,
    reference_width_px: Optional[float] = None,
    package_height_mm: Optional[float] = None,
    package_height_px: Optional[float] = None,
) -> Optional[float]:
    """
    High-level function: measure the minimum font height (mm) across all OCR boxes.

    Calibration priority:
      1. Explicit DPI provided (e.g. from EXIF).
      2. Reference object (known physical width vs. measured pixel width).
      3. Known package dimension (height) vs. measured pixel height.
      4. None — no calibration available; returns None.

    Returns:
        Minimum font height in mm, or None if calibration data is unavailable.
    """
    if not _CV2_AVAILABLE or not ocr_boxes:
        return None

    # Determine DPI
    effective_dpi: Optional[float] = None
    if dpi is not None and dpi > 0:
        effective_dpi = dpi
    elif reference_width_mm and reference_width_px:
        try:
            effective_dpi = calibrate_dpi_from_reference(
                image_path, reference_width_mm, reference_width_px
            )
        except ValueError:
            pass
    elif package_height_mm and package_height_px:
        try:
            effective_dpi = calibrate_dpi_from_reference(
                image_path, package_height_mm, package_height_px
            )
        except ValueError:
            pass

    if effective_dpi is None:
        logger.info("No DPI calibration available — skipping font height measurement.")
        return None

    heights_px = measure_font_heights_px(image_path, ocr_boxes)
    if not heights_px:
        return None

    heights_mm = [px_to_mm(h, effective_dpi) for h in heights_px if h > 0]
    return min(heights_mm) if heights_mm else None


def extract_image_dpi(image_path: str) -> Optional[float]:
    """
    Try to extract DPI from image EXIF data.
    Returns None if not available.
    """
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            info = img.info
            dpi = info.get("dpi")
            if dpi and isinstance(dpi, (tuple, list)) and len(dpi) >= 1:
                return float(dpi[0])
    except Exception:
        pass
    return None


def preprocess_image(image_path: str) -> Optional[np.ndarray]:
    """
    Load and pre-process image for better OCR: grayscale, denoise, threshold.
    Returns preprocessed numpy array or None if load fails.
    """
    if not _CV2_AVAILABLE:
        return None
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        # Adaptive threshold helps with uneven lighting / glare
        thresh = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        return thresh
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        return None
