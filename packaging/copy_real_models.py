"""
Copy real model assets directly into dist/SnapdragonDocAssistant/models/
(excludes redundant .zip archive caches to keep distribution clean).
"""

import os
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_MODELS = os.path.join(PROJECT_ROOT, "models")
DEST_MODELS = os.path.join(PROJECT_ROOT, "dist", "SnapdragonDocAssistant", "models")

def copy_real_models():
    print("=" * 80)
    print("  COPYING REAL MODEL ASSETS INTO DISTRIBUTABLE DIRECTORY")
    print("=" * 80)

    os.makedirs(DEST_MODELS, exist_ok=True)

    # 1. Piper TTS model
    src_piper = os.path.join(SRC_MODELS, "piper_hi")
    dest_piper = os.path.join(DEST_MODELS, "piper_hi")
    if os.path.isdir(src_piper):
        print(f"Copying piper_hi from {src_piper} to {dest_piper}...")
        if os.path.exists(dest_piper):
            shutil.rmtree(dest_piper)
        shutil.copytree(src_piper, dest_piper)
        print(f"  [OK] piper_hi copied ({os.path.getsize(os.path.join(dest_piper, 'hi_IN-pratham-medium.onnx')) / 1024 / 1024:.2f} MB)")

    # 2. TrOCR Compiled NPU model
    src_trocr = os.path.join(SRC_MODELS, "trocr-qnn-compiled")
    dest_trocr = os.path.join(DEST_MODELS, "trocr-qnn-compiled")
    if os.path.isdir(src_trocr):
        print(f"Copying trocr-qnn-compiled from {src_trocr} to {dest_trocr}...")
        if os.path.exists(dest_trocr):
            shutil.rmtree(dest_trocr)
        shutil.copytree(src_trocr, dest_trocr, ignore=shutil.ignore_patterns("*.zip"))
        print(f"  [OK] trocr-qnn-compiled copied.")

    # 3. Genie Bundle Qwen 1.7B
    src_genie = os.path.join(SRC_MODELS, "genie_bundle_qwen17")
    dest_genie = os.path.join(DEST_MODELS, "genie_bundle_qwen17")
    if os.path.isdir(src_genie):
        print(f"Copying genie_bundle_qwen17 from {src_genie} to {dest_genie}...")
        if os.path.exists(dest_genie):
            shutil.rmtree(dest_genie)
        shutil.copytree(src_genie, dest_genie)
        print(f"  [OK] genie_bundle_qwen17 copied.")

    # 4. Piper espeak-ng-data phonemization database
    try:
        import piper
        piper_pkg_dir = os.path.dirname(piper.__file__)
        src_espeak = os.path.join(piper_pkg_dir, "espeak-ng-data")
        dest_internal_espeak = os.path.join(PROJECT_ROOT, "dist", "SnapdragonDocAssistant", "_internal", "piper", "espeak-ng-data")
        if os.path.isdir(src_espeak):
            print(f"Copying espeak-ng-data to {dest_internal_espeak}...")
            if os.path.exists(dest_internal_espeak):
                shutil.rmtree(dest_internal_espeak)
            shutil.copytree(src_espeak, dest_internal_espeak)
            print(f"  [OK] espeak-ng-data copied.")
    except Exception as e:
        print(f"  [WARNING] Could not copy espeak-ng-data: {e}")

    # 5. Offline TrOCR Processor & Tokenizer files
    src_proc = os.path.join(SRC_MODELS, "trocr_processor")
    dest_proc = os.path.join(DEST_MODELS, "trocr_processor")
    if os.path.isdir(src_proc):
        print(f"Copying trocr_processor from {src_proc} to {dest_proc}...")
        if os.path.exists(dest_proc):
            shutil.rmtree(dest_proc)
        shutil.copytree(src_proc, dest_proc)
        print(f"  [OK] trocr_processor copied.")

    # 6. Offline Qwen Local Proxy Model (for non-Snapdragon CPU fallback)
    src_qwen = os.path.join(SRC_MODELS, "qwen_local_proxy")
    dest_qwen = os.path.join(DEST_MODELS, "qwen_local_proxy")
    if os.path.isdir(src_qwen):
        print(f"Copying qwen_local_proxy from {src_qwen} to {dest_qwen}...")
        if os.path.exists(dest_qwen):
            shutil.rmtree(dest_qwen)
        shutil.copytree(src_qwen, dest_qwen)
        print(f"  [OK] qwen_local_proxy copied.")

    print("\n" + "=" * 80)
    print("  MODELS COPY COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    copy_real_models()
