import os
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
TEST_IMAGES_DIR = os.path.join(PROJECT_ROOT, "test_images")
os.makedirs(TEST_IMAGES_DIR, exist_ok=True)


def get_font(size: int, bold: bool = False):
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


def generate_telecom_notice():
    width, height = 960, 620
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(24, bold=True)
    f_sub = get_font(18, bold=True)
    f_label = get_font(19, bold=False)

    # Header
    draw.text((50, 30), "PACIFIC BROADBAND AND TELECOM NETWORK", fill=(100, 20, 30), font=f_title)
    draw.text((50, 65), "Service Disconnection Notice and Urgent Remittance Demand", fill=(60, 60, 70), font=f_sub)
    draw.line([(50, 95), (width - 50, 95)], fill=(180, 180, 180), width=1)

    fields = [
        ("Subscriber Name", "Carlos Mendez"),
        ("Account Identifier", "TEL-55421-CA"),
        ("Overdue Balance", "$ 89.50"),
        ("Final Disconnection Date", "September 30 2026"),
        ("Service Plan", "Fiber Gigabit Internet"),
        ("Line Status", "SUSPENDED"),
    ]

    y = 115
    for label, val in fields:
        line_str = f"{label}: {val}"
        draw.text((50, y), line_str, fill=(30, 30, 30), font=f_label)
        y += 40

    draw.line([(50, y + 10), (width - 50, y + 10)], fill=(180, 180, 180), width=1)
    f_footer = get_font(16, bold=False)
    draw.text((50, y + 25), "Please remit $ 89.50 before September 30 2026 to restore network access.", fill=(150, 20, 20), font=f_footer)

    out_path = os.path.join(TEST_IMAGES_DIR, "telecom_disconnect_unseen.png")
    img.save(out_path, dpi=(150, 150))
    print(f"Generated {out_path} ({os.path.getsize(out_path)} bytes)")


if __name__ == "__main__":
    generate_telecom_notice()
