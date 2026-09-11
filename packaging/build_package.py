"""
Automated PyInstaller Packaging Script for Snapdragon Document Assistant.
Builds a standalone --onedir Windows distribution under dist/SnapdragonDocAssistant/.
"""

import os
import sys
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
ENTRY_POINT = os.path.join(PROJECT_ROOT, "scripts", "run_app.py")

def build_package():
    print("=" * 80)
    print("  BUILDING SNAPDRAGON DOCUMENT ASSISTANT WINDOWS DISTRIBUTION")
    print("=" * 80)

    # Verify PyInstaller is installed
    try:
        import PyInstaller
        print(f"[OK] PyInstaller detected: version {PyInstaller.__version__}")
    except ImportError:
        print("[ERROR] PyInstaller is not installed. Please run 'pip install pyinstaller'.")
        sys.exit(1)

    app_name = "SnapdragonDocAssistant"

    # Define hidden imports for native / dynamic extensions
    hidden_imports = [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtMultimedia",
        "onnxruntime",
        "cv2",
        "PIL",
        "PIL.Image",
        "numpy",
        "wave",
        "winsound",
    ]

    # Additional datas: test_images and src/ui styles
    datas = [
        f"{os.path.join(PROJECT_ROOT, 'test_images')};test_images",
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name", app_name,
        "--onedir",
        "--noconfirm",
        "--clean",
        "--windowed", # Windows GUI mode
    ]

    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])

    for d in datas:
        cmd.extend(["--add-data", d])

    cmd.append(ENTRY_POINT)

    print(f"\nExecuting PyInstaller command:\n{' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"\n[ERROR] PyInstaller build failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    out_folder = os.path.join(DIST_DIR, app_name)
    exe_path = os.path.join(out_folder, f"{app_name}.exe")

    # Ensure audio_output directory exists in distributable
    os.makedirs(os.path.join(out_folder, "audio_output"), exist_ok=True)

    # Ensure real model files (NOT symlinks / junctions) are copied into distributable
    script_copy = os.path.join(PROJECT_ROOT, "packaging", "copy_real_models.py")
    subprocess.run([sys.executable, script_copy], check=True)

    print("\n" + "=" * 80)
    print(f"  BUILD COMPLETE: {exe_path}")
    print("=" * 80)

    if os.path.isfile(exe_path):
        size_bytes = os.path.getsize(exe_path)
        print(f"  * Executable Size: {size_bytes:,} bytes ({size_bytes / 1024 / 1024:.2f} MB)")
        print(f"  * Output Directory: {out_folder}")
    else:
        print(f"[WARNING] Executable not found at expected path: {exe_path}")

if __name__ == "__main__":
    build_package()

