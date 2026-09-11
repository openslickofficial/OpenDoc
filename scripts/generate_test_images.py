#!/usr/bin/env python3
"""
Test Image Generator for Snapdragon Document Assistant.
Generates 3 realistic synthetic document test images:
1. printed_paragraph.png - Standard printed document paragraph.
2. form_document.png - Form document with labeled fields and key-value pairs.
3. skewed_document.png - Intentionally tilted document (~6.5 degrees) for deskew testing.
"""

import os
from PIL import Image, ImageDraw, ImageFont


def create_printed_paragraph_image(output_path: str):
    width, height = 960, 520
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Load system TrueType font for clear optical character resolution
    font_path = "C:/Windows/Fonts/arial.ttf"
    if os.path.exists(font_path):
        font_header = ImageFont.truetype(font_path, 26)
        font_body = ImageFont.truetype(font_path, 20)
    else:
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()

    lines = [
        "SNAPDRAGON X ELITE NPU ACCELERATION",
        "Document Processing Subsystem Technical Brief",
        "The Hexagon NPU delivers dedicated tensor acceleration for vision.",
        "Executing the TrOCR vision encoder on the Hexagon processor via QNN",
        "achieves high energy efficiency without sending data to the cloud.",
        "Hardware Target: HP OmniBook X running ARM64 Windows 11.",
    ]

    y = 40
    for i, line in enumerate(lines):
        if i == 0:
            draw.text((50, y), line, fill=(10, 30, 80), font=font_header)
            y += 45
        elif i == 1:
            draw.text((50, y), line, fill=(80, 80, 90), font=font_body)
            y += 40
            draw.line([(50, y), (width - 50, y)], fill=(200, 200, 200), width=1)
            y += 25
        else:
            draw.text((50, y), line, fill=(20, 20, 20), font=font_body)
            y += 42

    img.save(output_path, "PNG")
    print(f"Created: {output_path}")


def create_form_document_image(output_path: str):
    width, height = 960, 560
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_path = "C:/Windows/Fonts/arial.ttf"
    if os.path.exists(font_path):
        font_header = ImageFont.truetype(font_path, 24)
        font_label = ImageFont.truetype(font_path, 20)
    else:
        font_header = ImageFont.load_default()
        font_label = ImageFont.load_default()

    # Header
    draw.rectangle([30, 25, width - 30, 75], fill=(235, 240, 250), outline=(180, 190, 210), width=1)
    draw.text((50, 38), "VERIFICATION FORM - SNAPDRAGON X HARDWARE", fill=(15, 30, 90), font=font_header)

    fields = [
        ("Application ID", "SN-2026-X89"),
        ("Applicant Name", "Dr. Arthur Vance"),
        ("Verification Date", "September 11 2026"),
        ("Device Model", "HP OmniBook Snapdragon X"),
        ("Inference Provider", "QNNExecutionProvider"),
        ("Status", "VERIFIED AND APPROVED"),
    ]

    y = 100
    for label, val in fields:
        line_text = f"{label}: {val}"
        draw.text((50, y), line_text, fill=(30, 30, 30), font=font_label)
        y += 50

    img.save(output_path, "PNG")
    print(f"Created: {output_path}")


def create_skewed_document_image(output_path: str, skew_degrees: float = -6.5):
    base_w, base_h = 880, 420
    base_img = Image.new("RGB", (base_w, base_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(base_img)

    font_path = "C:/Windows/Fonts/arial.ttf"
    if os.path.exists(font_path):
        font_header = ImageFont.truetype(font_path, 26)
        font_body = ImageFont.truetype(font_path, 20)
    else:
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()

    draw.text((40, 30), "SKEW CORRECTION TEST DOCUMENT", fill=(20, 20, 90), font=font_header)
    draw.line([(40, 68), (base_w - 40, 68)], fill=(180, 180, 190), width=1)

    lines = [
        "This document is tilted at an intentional skew angle.",
        "The automatic deskew algorithm calculates rotation",
        "and normalizes the image before passing it to TrOCR.",
        "Expected result is clean and legible text recognition.",
    ]

    y = 90
    for line in lines:
        draw.text((40, y), line, fill=(20, 20, 20), font=font_body)
        y += 45

    # Rotate with background fill
    skewed = base_img.rotate(skew_degrees, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(255, 255, 255))
    skewed.save(output_path, "PNG")
    print(f"Created: {output_path} (Skewed at {skew_degrees} deg)")



def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    test_dir = os.path.join(project_root, "test_images")
    os.makedirs(test_dir, exist_ok=True)

    img1 = os.path.join(test_dir, "printed_paragraph.png")
    img2 = os.path.join(test_dir, "form_document.png")
    img3 = os.path.join(test_dir, "skewed_document.png")

    create_printed_paragraph_image(img1)
    create_form_document_image(img2)
    create_skewed_document_image(img3, skew_degrees=-6.5)

    print("\nAll 3 test images successfully generated in:", test_dir)


if __name__ == "__main__":
    main()
