"""
Security Audit Test Suite: Input Validation & Malformed-File Robustness
Tests pipeline resilience against:
1. Zero-byte file
2. Corrupted / truncated image
3. Renamed non-image file (text file disguised as .png)
4. Extremely large image (20000x20000 px)
"""

import os
import sys
import time
import traceback
from PIL import Image

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipeline import process_document

MALFORMED_DIR = os.path.join(PROJECT_ROOT, "test_images", "malformed_tests")
os.makedirs(MALFORMED_DIR, exist_ok=True)

def generate_test_files():
    files = {}

    # 1. Zero-byte file
    p_zero = os.path.join(MALFORMED_DIR, "zero_byte.png")
    with open(p_zero, "wb") as f:
        pass
    files["zero_byte"] = p_zero

    # 2. Corrupted / truncated image (valid PNG header + random/truncated bytes)
    p_corrupt = os.path.join(MALFORMED_DIR, "corrupt_truncated.png")
    with open(p_corrupt, "wb") as f:
        # PNG 8-byte magic header followed by truncated junk
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00")
        f.write(b"\xde\xad\xbe\xef\x00\x01\x02\x03corrupted_bytes_without_iend")
    files["corrupt"] = p_corrupt

    # 3. Renamed non-image file (.txt containing ASCII disguised as .png)
    p_fake = os.path.join(MALFORMED_DIR, "fake_image_payload.png")
    with open(p_fake, "w", encoding="utf-8") as f:
        f.write("This is a plain text file containing arbitrary text or executable payload disguised as a png.\n")
    files["fake_png"] = p_fake

    # 4. Extremely large image: Let's create a 20000x20000 image.
    # To save disk and RAM during creation, we can write a blank or minimal 1-bit or compressed PNG
    p_huge = os.path.join(MALFORMED_DIR, "huge_20000x20000.png")
    if not os.path.exists(p_huge):
        print("Generating 20000x20000 test image (mode='1' 1-bit palette for efficient disk storage)...")
        t0 = time.time()
        # 1-bit black/white image of 20000x20000 is ~47MB uncompressed bitmask, highly compressible in PNG
        img = Image.new("1", (20000, 20000), color=1)
        img.save(p_huge, "PNG")
        print(f"Generated {p_huge} ({os.path.getsize(p_huge)/1024:.1f} KB) in {time.time()-t0:.2f}s")
    files["huge_image"] = p_huge

    return files

def test_pipeline_on_file(name: str, path: str):
    print(f"\n=======================================================")
    print(f"TESTING INPUT: {name} -> {os.path.basename(path)}")
    print(f"File size: {os.path.getsize(path)} bytes")
    print(f"=======================================================")
    t_start = time.perf_counter()
    try:
        res = process_document(path, target_lang="hi", strict_fidelity_gate=False)
        dur = (time.perf_counter() - t_start) * 1000.0
        status = res.get("status")
        err = res.get("error")
        print(f"RESULT: Status={status} in {dur:.2f} ms")
        print(f"Error captured in result: {err}")
        return {
            "name": name,
            "path": path,
            "status": status,
            "error": err,
            "duration_ms": dur,
            "crashed": False
        }
    except Exception as e:
        dur = (time.perf_counter() - t_start) * 1000.0
        print(f"UNHANDLED EXCEPTION CRASH: {type(e).__name__}: {e}")
        traceback.print_exc()
        return {
            "name": name,
            "path": path,
            "status": "CRASHED",
            "error": str(e),
            "duration_ms": dur,
            "crashed": True
        }

if __name__ == "__main__":
    files = generate_test_files()
    results = []
    for name, path in files.items():
        r = test_pipeline_on_file(name, path)
        results.append(r)

    print("\n\n" + "="*70)
    print("SUMMARY OF MALFORMED-INPUT TESTING")
    print("="*70)
    for r in results:
        print(f"[{r['name'].upper()}]: Status={r['status']} | Crashed={r['crashed']} | Time={r['duration_ms']:.1f}ms | Error={r['error']}")
