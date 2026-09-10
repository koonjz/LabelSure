"""
LabelSure — Sample Label Image Generator
Creates synthetic product label images for pipeline testing.
Run: python -m backend.sample_data.generate_labels

Generates:
  - compliant_label.png  : All required fields present, fonts large enough
  - noncompliant_mrp.png : MRP missing
  - noncompliant_date.png: Manufacture date missing
  - noncompliant_addr.png: Manufacturer address missing
  - blurry_label.png     : Gaussian blur (should trigger NEEDS_REVIEW)
"""
from pathlib import Path
import random

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Pillow not installed. Run: pip install Pillow")


OUTPUT_DIR = Path(__file__).parent


def make_label(
    filename: str,
    product_name: str = "REFINED SUNFLOWER OIL",
    manufacturer: str = "Sunrise Foods Pvt. Ltd.",
    address: str = "Plot 12, MIDC Industrial Area, Pune - 411026",
    net_qty: str = "1 L (1000 ml)",
    mrp: str = "MRP ₹120.00 (Incl. of all taxes)",
    mfg_date: str = "Mfg. Date: 03/2024",
    include_mrp: bool = True,
    include_date: bool = True,
    include_address: bool = True,
    blur: bool = False,
    font_size_small: int = 24,    # ~4mm at 150dpi
) -> None:
    if not PIL_AVAILABLE:
        return

    W, H = 600, 900
    img = Image.new("RGB", (W, H), color=(255, 248, 220))  # cream background
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([10, 10, W - 10, H - 10], outline=(180, 140, 40), width=4)
    draw.rectangle([20, 20, W - 20, H - 20], outline=(220, 180, 60), width=2)

    # Use default PIL fonts (no external font file needed)
    try:
        font_title = ImageFont.truetype("arial.ttf", 48)
        font_body = ImageFont.truetype("arial.ttf", font_size_small)
        font_small = ImageFont.truetype("arial.ttf", 20)
    except (IOError, OSError):
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    y = 50

    # Product name (title)
    draw.text((W // 2, y), product_name, fill=(80, 40, 0), font=font_title, anchor="mt")
    y += 70

    # Decorative line
    draw.line([(40, y), (W - 40, y)], fill=(180, 140, 40), width=2)
    y += 20

    # Net Quantity
    draw.text((40, y), f"Net Contents: {net_qty}", fill=(20, 20, 20), font=font_body)
    y += 50

    # MRP
    if include_mrp:
        draw.text((40, y), mrp, fill=(180, 0, 0), font=font_body)
    else:
        draw.text((40, y), "[MRP MISSING]", fill=(200, 200, 200), font=font_small)
    y += 50

    # Manufacture Date
    if include_date:
        draw.text((40, y), mfg_date, fill=(20, 20, 20), font=font_body)
    else:
        draw.text((40, y), "[DATE MISSING]", fill=(200, 200, 200), font=font_small)
    y += 50

    # Batch number
    draw.text((40, y), f"Batch No: BT{random.randint(10000, 99999)}", fill=(60, 60, 60), font=font_small)
    y += 40

    # Decorative line
    draw.line([(40, y), (W - 40, y)], fill=(180, 140, 40), width=2)
    y += 20

    # Generic name
    draw.text((40, y), "Generic Name: Refined Edible Oil", fill=(20, 20, 20), font=font_small)
    y += 35

    # Manufacturer info
    draw.text((40, y), "Manufactured by:", fill=(20, 20, 20), font=font_small)
    y += 28
    draw.text((40, y), manufacturer, fill=(20, 20, 20), font=font_small)
    y += 28
    if include_address:
        draw.text((40, y), address, fill=(20, 20, 20), font=font_small)
    else:
        draw.text((40, y), "[ADDRESS MISSING]", fill=(200, 200, 200), font=font_small)
    y += 40

    # FSSAI number
    draw.text((40, y), "FSSAI Lic. No: 12123456000123", fill=(60, 60, 60), font=font_small)
    y += 35

    # Ingredients box
    draw.rectangle([40, y, W - 40, y + 100], outline=(180, 140, 40), width=1)
    draw.text((50, y + 5), "Ingredients: 100% Refined Sunflower Oil", fill=(20, 20, 20), font=font_small)
    y += 110

    # Customer care
    draw.text((40, y), "Customer Care: 1800-XXX-XXXX | www.sunrisefoods.in", fill=(80, 80, 80), font=font_small)
    y += 35

    # Recycling symbol placeholder
    draw.ellipse([W - 80, H - 80, W - 40, H - 40], outline=(100, 150, 100), width=2)
    draw.text((W - 60, H - 60), "♻", fill=(100, 150, 100), font=font_small, anchor="mm")

    # Country of origin
    draw.text((40, H - 50), "Country of Origin: India", fill=(80, 80, 80), font=font_small)

    # Apply blur if requested (simulates blurry/glare image)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=4))

    out_path = OUTPUT_DIR / filename
    img.save(str(out_path), "PNG", dpi=(150, 150))
    print(f"Generated: {out_path}")


def generate_all():
    make_label("compliant_label.png")
    make_label("noncompliant_mrp.png", include_mrp=False)
    make_label("noncompliant_date.png", include_date=False)
    make_label("noncompliant_addr.png", include_address=False)
    make_label("blurry_label.png", blur=True)
    print("All sample labels generated successfully.")


if __name__ == "__main__":
    generate_all()
