#!/usr/bin/env python3
"""
Phase 2 Synthetic Test Document Generator.
Generates two realistic document images for testing plain-language simplification
and the fidelity-check safeguard:
1. medical_bill_receipt.png - Medical bill with patient name, Claim ID, Date, Amount, and APPROVED status.
2. legal_notice_deadline.png - Municipal legal citation with Case ID, Fine Amount, Deadline, and PENDING status.
"""

import os
import cv2
import numpy as np
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


def generate_medical_bill():
    """Generates medical_bill_receipt.png."""
    width, height = 1100, 750
    img = Image.new("RGB", (width, height), color=(252, 252, 250))
    draw = ImageDraw.Draw(img)

    f_title = get_font(32, bold=True)
    f_sub = get_font(20, bold=True)
    f_label = get_font(20, bold=True)
    f_val = get_font(20, bold=False)
    f_box = get_font(22, bold=True)

    # Outer border
    draw.rectangle([(25, 25), (width - 25, height - 25)], outline=(180, 180, 180), width=2)

    # Header
    draw.text((60, 50), "METROPOLITAN HEALTHCARE SERVICES", fill=(20, 20, 20), font=f_title)
    draw.text((60, 95), "PATIENT BILLING STATEMENT AND BENEFIT DETERMINATION", fill=(70, 70, 70), font=f_sub)
    draw.line([(60, 130), (width - 60, 130)], fill=(0, 0, 0), width=2)

    fields = [
        ("Patient Full Name :", "Harold Jenkins"),
        ("Service Date :", "October 24 2026"),
        ("Claim Reference ID :", "MED-90821-TX"),
        ("Facility Location :", "Central Ambulatory Clinic"),
        ("Attending Physician :", "Dr. Arthur Vance"),
        ("Total Billed Charges :", "$ 450.00"),
        ("Patient Responsibility :", "$ 0.00 (Copay Paid)"),
    ]

    y = 160
    for label, val in fields:
        draw.text((80, y), label, fill=(40, 40, 40), font=f_label)
        draw.text((380, y), val, fill=(10, 10, 10), font=f_val)
        y += 45

    # Status Box
    draw.line([(60, y + 10), (width - 60, y + 10)], fill=(200, 200, 200), width=1)
    draw.rectangle([(80, y + 30), (width - 80, y + 120)], fill=(240, 248, 240), outline=(50, 150, 50), width=2)
    draw.text((100, y + 45), "CLAIM DETERMINATION STATUS :", fill=(20, 100, 20), font=f_box)
    draw.text((100, y + 80), "APPROVED FOR REIMBURSEMENT", fill=(10, 120, 10), font=f_title)

    # Footer note
    draw.text((80, y + 145), "Official Certification: All inpatient and clinical expenses verified and approved.", fill=(80, 80, 80), font=f_val)

    out_path = os.path.join(TEST_IMAGES_DIR, "medical_bill_receipt.png")
    img.save(out_path, dpi=(300, 300))
    print(f"Generated: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


def generate_legal_notice():
    """Generates legal_notice_deadline.png."""
    width, height = 1100, 750
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(30, bold=True)
    f_sub = get_font(20, bold=True)
    f_label = get_font(20, bold=True)
    f_val = get_font(20, bold=False)
    f_warn = get_font(22, bold=True)

    # Double border for formal citation
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(0, 0, 0), width=3)
    draw.rectangle([(26, 26), (width - 26, height - 26)], outline=(120, 120, 120), width=1)

    # Header
    draw.text((60, 45), "DEPARTMENT OF MUNICIPAL REGULATORY COMPLIANCE", fill=(0, 0, 0), font=f_title)
    draw.text((60, 90), "OFFICIAL CITATION NOTICE AND FINAL SUMMONS", fill=(80, 0, 0), font=f_sub)
    draw.line([(60, 125), (width - 60, 125)], fill=(0, 0, 0), width=2)

    fields = [
        ("Official Docket ID :", "GOV-2026-LAW-77"),
        ("Violation Category :", "Statutory Filing Default"),
        ("Notice Issuance Date :", "October 18 2026"),
        ("Mandatory Due Date :", "November 15 2026"),
        ("Assessed Fine Sum :", "$ 250.00"),
        ("Statutory Action :", "Remittance Required"),
    ]

    y = 155
    for label, val in fields:
        draw.text((80, y), label, fill=(30, 30, 30), font=f_label)
        draw.text((380, y), val, fill=(0, 0, 0), font=f_val)
        y += 45

    # Status / Warning Box
    draw.rectangle([(80, y + 20), (width - 80, y + 115)], fill=(255, 245, 245), outline=(180, 40, 40), width=2)
    draw.text((100, y + 35), "ACCOUNT ADJUDICATION STATUS :", fill=(140, 20, 20), font=f_warn)
    draw.text((100, y + 70), "STATUS : PENDING PAYMENT", fill=(180, 0, 0), font=f_title)

    # Legal Disclaimer
    draw.text((80, y + 140), "Warning: Immediate payment of $ 250.00 required before deadline November 15 2026.", fill=(50, 50, 50), font=f_val)
    draw.text((80, y + 170), "Failure to comply will result in administrative hearing and penalty escalation.", fill=(80, 80, 80), font=f_val)

    out_path = os.path.join(TEST_IMAGES_DIR, "legal_notice_deadline.png")
    img.save(out_path, dpi=(300, 300))
    print(f"Generated: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    generate_medical_bill()
    generate_legal_notice()
