"""
Quick local test of the improved field_extractor with Tesseract OCR.
Run from project root:  python3 -m backend.processing.test_local_extraction <image_path>
"""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_extraction(image_path: str):
    print(f"\n{'='*60}")
    print(f"Testing: {image_path}")
    print('='*60)

    from backend.processing.ocr_engine import run_ocr
    from backend.processing.nlp_lang import detect_language
    from backend.processing.field_extractor import extract_fields

    # Step 1: OCR
    print("\n[1] Running OCR (Tesseract fallback)...")
    result = run_ocr(image_path, lang_code="en")
    print(f"    Engine : {result.engine_used}")
    print(f"    Chars  : {len(result.full_text)}")
    print(f"    Min conf: {result.min_confidence:.2f}")
    print(f"\n--- RAW OCR TEXT ---")
    print(result.full_text[:2000])
    print("--- END ---\n")

    # Step 2: Language
    lang = detect_language(result.full_text)
    print(f"[2] Detected language: {lang}")

    # Step 3: Re-run with Indic if needed
    if lang != "en":
        print(f"[3] Re-running OCR with lang={lang} ...")
        result2 = run_ocr(image_path, lang_code=lang)
        if len(result2.full_text.strip()) > len(result.full_text.strip()):
            result = result2
            print("    Using Indic OCR result (longer text).")

    # Step 4: Extract fields
    print("\n[4] Extracting fields...")
    label = extract_fields(result, lang_code=lang)

    print("\n--- EXTRACTED FIELDS ---")
    print(f"  Product Name       : {label.generic_name}")
    print(f"  Manufacturer       : {label.manufacturer_name}")
    print(f"  Address            : {label.manufacturer_address}")
    print(f"  Net Qty            : {label.net_quantity_value} {label.net_quantity_unit}")
    print(f"  MRP                : ₹{label.mrp}")
    print(f"  Mfg Date           : {label.manufacture_month}/{label.manufacture_year}")
    print(f"  Batch No.          : {label.batch_number}")
    print(f"  Expiry / Best Before: {label.expiry_date}")
    print(f"  FSSAI License      : {label.fssai_license}")
    print(f"  Consumer Care      : {label.consumer_care}")
    print(f"  OCR Confidence     : {label.overall_ocr_confidence:.2f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_local_extraction.py <image_path>")
        sys.exit(1)
    test_extraction(sys.argv[1])
