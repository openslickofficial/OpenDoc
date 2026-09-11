#!/usr/bin/env python3
"""
Phase 3 Synthetic Test Document Generator.
Generates two realistic document images for testing Phase 3 generalization & prose translation:
1. utility_bill_unseen.png - Utility bill with completely unseen field labels (ELEC-98234-NY, $135.50, September 28 2026).
2. flowing_prose_letter.png - Flowing prose notice (TAX-2026-8819, $320.00, October 15 2026, approved, deadline).
"""

import os
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
TEST_IMAGES_DIR = os.path.join(PROJECT_ROOT, "test_images")
os.makedirs(TEST_IMAGES_DIR, exist_ok=True)


def get_font(size: int, bold: bool = False):
    """Loads system TrueType font or falls back to PIL default."""
    font_names = [
        "arialbd.ttf" if bold else "arial.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except IOError:
            continue
    return ImageFont.load_default()


def generate_utility_bill():
    """Generates utility_bill_unseen.png with completely unseen labels."""
    width, height = 960, 620
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(24, bold=True)
    f_sub = get_font(18, bold=True)
    f_label = get_font(19, bold=False)

    # Header
    draw.text((50, 30), "MUNICIPAL POWER & WATER AUTHORITY", fill=(20, 40, 80), font=f_title)
    draw.text((50, 65), "Residential Utility Statement and Consumption Invoice", fill=(60, 60, 70), font=f_sub)
    draw.line([(50, 95), (width - 50, 95)], fill=(180, 180, 180), width=1)

    # Fields with labels NEVER previously seen in OFFICIAL_LABEL_MAP_HI
    fields = [
        ("Consumer Account Number", "ELEC-98234-NY"),
        ("Billing Cycle", "August 2026"),
        ("Meter Reading Units", "420 kWh"),
        ("Net Due Amount", "$ 135.50"),
        ("Payment Due Date", "September 28 2026"),
        ("Account Standing", "CURRENT"),
    ]

    y = 115
    for label, val in fields:
        line_str = f"{label}: {val}"
        draw.text((50, y), line_str, fill=(20, 20, 20), font=f_label)
        y += 42

    draw.line([(50, y + 10), (width - 50, y + 10)], fill=(180, 180, 180), width=1)
    y += 25
    draw.text((50, y), "Important Notice: Please remit $ 135.50 before September 28 2026 to maintain active service.", fill=(50, 50, 50), font=f_label)

    out_path = os.path.join(TEST_IMAGES_DIR, "utility_bill_unseen.png")
    img.save(out_path, "PNG")
    print(f"Generated: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


def generate_flowing_prose():
    """Generates flowing_prose_letter.png with flowing narrative sentences and embedded entities."""
    width, height = 960, 580
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(24, bold=True)
    f_sub = get_font(18, bold=True)
    f_body = get_font(19, bold=False)

    # Header
    draw.text((50, 30), "CITY HOUSING AND MUNICIPAL TAX ADMINISTRATION", fill=(10, 30, 80), font=f_title)
    draw.text((50, 65), "Official Property Tax Assessment Determination", fill=(80, 80, 90), font=f_sub)
    draw.line([(50, 95), (width - 50, 95)], fill=(200, 200, 200), width=1)

    # Flowing letter paragraphs
    lines = [
        "Dear Resident,",
        "Please be advised that your municipal assessment for Case TAX-2026-8819",
        "for the period ending October 15 2026 has been verified and approved.",
        "The evaluated statutory remittance fee of $ 320.00 is due within thirty days.",
        "Your account status is currently pending receipt of this required payment.",
        "You must submit payment before the mandatory deadline of November 15 2026.",
        "Failure to remit payment on time will result in administrative penalties.",
    ]

    y = 120
    for line in lines:
        draw.text((50, y), line, fill=(20, 20, 20), font=f_body)
        y += 44

    out_path = os.path.join(TEST_IMAGES_DIR, "flowing_prose_letter.png")
    img.save(out_path, "PNG")
    print(f"Generated: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    generate_utility_bill()
    generate_flowing_prose()
