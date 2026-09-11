"""
LabelSure — NLP Language Detection
Detects the script/language on the label so the correct OCR model is used.

Primary: langdetect (fast, works on short text snippets)
Indic: Uses Unicode script ranges to detect specific Indic scripts reliably,
       since langdetect can confuse Devanagari / Tamil / Telugu etc.
"""
from __future__ import annotations
import logging
import re
import unicodedata

from typing import Optional

logger = logging.getLogger(__name__)

try:
    from langdetect import detect, DetectorFactory, LangDetectException
    DetectorFactory.seed = 42  # reproducible results
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not available — defaulting to 'en'.")


# ─────────────────────────────────────────────────────────────────────────────
# Unicode script range detection (more reliable for short Indic texts)
# ─────────────────────────────────────────────────────────────────────────────

INDIC_SCRIPT_RANGES = {
    "hi": (0x0900, 0x097F),  # Devanagari (Hindi, Marathi, Sanskrit)
    "ta": (0x0B80, 0x0BFF),  # Tamil
    "te": (0x0C00, 0x0C7F),  # Telugu
    "kn": (0x0C80, 0x0CFF),  # Kannada
    "ml": (0x0D00, 0x0D7F),  # Malayalam
    "bn": (0x0980, 0x09FF),  # Bengali
    "gu": (0x0A80, 0x0AFF),  # Gujarati
    "pa": (0x0A00, 0x0A7F),  # Gurmukhi (Punjabi)
    "or": (0x0B00, 0x0B7F),  # Odia
}


def _count_chars_in_range(text: str, lo: int, hi: int) -> int:
    return sum(1 for c in text if lo <= ord(c) <= hi)


def detect_script_from_unicode(text: str) -> Optional[str]:
    """
    Detect Indic script by counting characters in Unicode ranges.
    Returns ISO-639-1 code of the dominant script, or None if not Indic.
    """
    counts = {
        lang: _count_chars_in_range(text, lo, hi)
        for lang, (lo, hi) in INDIC_SCRIPT_RANGES.items()
    }
    best_lang = max(counts, key=lambda k: counts[k])
    if counts[best_lang] > 3:  # at least 4 Indic chars → confident detection
        return best_lang
    return None


def detect_language(text: str) -> str:
    """
    Detect the primary language of the given text.

    Strategy:
      1. Check Unicode ranges for Indic scripts (most reliable for short texts).
      2. Fall back to langdetect for Latin/other scripts.
      3. Default to 'en' if detection fails.

    Returns:
        ISO-639-1 language code (e.g. 'en', 'hi', 'ta', 'te', 'kn', 'bn').
    """
    if not text or len(text.strip()) < 3:
        return "en"

    # Step 1: Unicode-based Indic detection (fast and reliable)
    indic_lang = detect_script_from_unicode(text)
    if indic_lang:
        logger.debug(f"Detected Indic script: {indic_lang}")
        return indic_lang

    # Step 2: langdetect for non-Indic
    if _LANGDETECT_AVAILABLE:
        try:
            lang = detect(text)
            # langdetect returns zh-cn, zh-tw etc. — normalise
            lang_short = lang.split("-")[0].lower()
            logger.debug(f"langdetect result: {lang_short}")
            return lang_short
        except (LangDetectException, Exception) as e:
            logger.debug(f"langdetect failed: {e}")

    return "en"


def normalise_indic_text(text: str, lang_code: str) -> str:
    """
    Light normalisation for Indic text:
    - Normalise Unicode to NFC (composed form).
    - Strip zero-width joiners/non-joiners that confuse field extraction.
    - Additional script-specific normalisation can be added here.
    """
    # NFC normalisation
    text = unicodedata.normalize("NFC", text)

    # Remove zero-width characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text
