# Installation & Setup Guide (Windows)

This guide provides simple, step-by-step instructions for anyone—including evaluators and users with **zero prior Python or Machine Learning experience**—to install and run the **Snapdragon Document Assistant** on Windows.

---

## 1. System Requirements

- **Operating System**: Windows 11 (ARM64 on Snapdragon X Elite or standard x64) or Windows 10 (64-bit).
- **Processor**: Snapdragon® X Elite / Plus, or Intel / AMD 64-bit processor.
- **Memory**: Minimum 8 GB RAM (16 GB recommended).
- **Storage**: ~8 GB free disk space (for models and virtual environment).
- **Audio**: Working speakers or headphones (for text-to-speech output).

---

## 2. Step 1: Install Python 3.11

If you do not already have Python installed:

1. Download the official Python 3.11 installer for Windows from [python.org](https://www.python.org/downloads/release/python-3119/) (e.g. `Windows installer (64-bit)` or `Windows installer (ARM64)`).
2. Run the installer.
3. **CRITICAL STEP**: On the very first screen of the installer, check the box that says:
   $$\mathbf{\checkmark\ \text{Add python.exe to PATH}}$$
4. Click **Install Now** and wait for installation to finish.
5. Close the installer.

---

## 3. Step 2: Download & Extract the Project

If you received this project as a ZIP archive:
1. Right-click the ZIP file and select **Extract All...**.
2. Extract to a convenient folder (e.g., `C:\SnapdragonDocAssistant` or your Documents folder).
3. Open the extracted folder in Windows File Explorer.

If using Git:
```powershell
git clone https://github.com/openslickofficial/OpenDoc.git
cd OpenDoc
```

---

## 4. Step 3: One-Command Setup

Open **Windows PowerShell** or **Command Prompt** in the project folder:

```powershell
# 1. Create an isolated virtual environment
python -m venv .venv

# 2. Activate the virtual environment
# In PowerShell:
.venv\Scripts\Activate.ps1

# (If PowerShell blocks script execution, run: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
# Or in standard Command Prompt (cmd.exe):
# .venv\Scripts\activate.bat

# 3. Upgrade pip and install all required libraries
pip install --upgrade pip
pip install -r requirements.txt
```

*(Note: The installation takes 2–5 minutes depending on your internet connection. Dependencies like PySide6, ONNX Runtime, PyTorch, and OpenCV will be installed automatically).*

---

## 5. Step 4: Launch the Desktop Application

Once the setup is complete, run:

```powershell
python scripts/run_app.py
```

Alternatively, you can double-click **`run_app.bat`** in the project root directory.

The **Snapdragon Document Assistant** window will open:
1. Click **"📁 Browse Files..."** or drag-and-drop a sample scan from the `test_images\` folder (e.g., `form_document.png` or `medical_bill_receipt.png`).
2. Verify the document thumbnail preview appears.
3. Choose your target language in the dropdown (Default: `Hindi (hi)`).
4. Click the high-contrast crimson button: **"⚡ Process Document"**.
5. Observe the live 4-stage pipeline panel on the left (OCR $\rightarrow$ Simplification $\rightarrow$ Translation $\rightarrow$ Speech Synthesis).
6. When complete, inspect the translated Hindi text in the right tab, review the **Fidelity Audit Table**, and click **▶ Play** on the audio player at the bottom to hear the document read aloud!

---

## 6. Running via the Command-Line Interface (CLI)

For developers or automated workflows, you can process documents directly without the graphical interface:

```powershell
# Basic run with text report and audio generation:
python scripts/run_pipeline.py --image test_images/form_document.png

# Output machine-readable JSON:
python scripts/run_pipeline.py --image test_images/form_document.png --json

# Strict safety mode (blocks audio synthesis if any inconsistencies are found):
python scripts/run_pipeline.py --image test_images/telecom_disconnect_unseen.png --strict
```

---

## 7. Running the Packaged Executable (`--onedir`)

If you build or receive the packaged distributable folder:
1. Navigate into `dist\SnapdragonDocAssistant\`.
2. Ensure the `models\` folder is present in the application directory.
3. Double-click **`SnapdragonDocAssistant.exe`**.
4. The application will start immediately without requiring a Python terminal, virtual environment, or internet connection. It operates 100% offline.

---

## 8. Troubleshooting & Common Questions

- **PowerShell Script Execution Error (`running scripts is disabled on this system`)**:
  - Run this command in your PowerShell window before activating:
    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    ```
- **"python is not recognized as an internal or external command"**:
  - Python was installed without checking "Add python.exe to PATH". Re-run the Python installer, select **Modify**, and ensure the PATH option is checked.
- **Audio does not play**:
  - The application uses your default Windows audio output device. Ensure your speakers or headphones are unmuted. The audio player includes an automatic fallback that plays `.wav` files through standard Windows system media services.
- **Where are the generated audio files stored?**:
  - All synthesized spoken files are saved as timestamped `.wav` audio files in the `audio_output\` folder inside the project directory.
