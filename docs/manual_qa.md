# Snapdragon Document Assistant — Desktop GUI Manual QA Checklist

This document provides a structured manual test checklist for hackathon judges, QA evaluators, and developers to verify the PySide6 desktop GUI application.

> [!NOTE]
> **Execution Status**: This document is a standardized manual evaluation protocol created for human testers. Automated headless testing (`scripts/test_gui_headless.py`) has validated widget states, background signals, and screen grabs programmatically; this interactive checklist has not yet been walked through end-to-end by an interactive human tester.

---

## Quickstart: Launching the Desktop UI

From the `doc-assistant` root directory, run:

```powershell
python scripts/run_app.py
```

---

## QA Test Checklist

### 1. Ingestion & Pre-Run State
| # | Test Scenario | Steps | Expected Behavior | Pass/Fail |
|---|---|---|---|:---:|
| **1.1** | **Initial State** | Launch application. | Window opens in dark slate theme (1180×820). "Process Document" button is disabled. Banner is hidden. Stages 1–4 are marked `⚪ Pending`. Audio player displays `No audio generated yet`. | [ ] |
| **1.2** | **File Browser Selection** | Click "📁 Browse Files..." in the drop area. Select `test_images/form_document.png`. | Preview thumbnail renders the verification form. File label displays name, dimensions, and size. "Process Document" button is enabled with text `⚡ Process 'form_document.png'`. | [ ] |
| **1.3** | **Drag & Drop Ingestion** | Drag `test_images/medical_bill_receipt.png` from Windows File Explorer and drop it onto the drop box. | Drop area border highlights cyan during hover. On drop, preview updates to the medical bill, and process button text updates to `⚡ Process 'medical_bill_receipt.png'`. | [ ] |

---

### 2. Multi-Threaded Non-Blocking Execution & Stage Progress
| # | Test Scenario | Steps | Expected Behavior | Pass/Fail |
|---|---|---|---|:---:|
| **2.1** | **UI Responsiveness** | Click "⚡ Process Document". While processing (12–25s on CPU): move the window, click tabs, or click the language dropdown. | **Zero window freezing**. The UI remains 100% fluid, responsive, and draggable. The process button shows `⏳ Processing Document on Device...`. | [ ] |
| **2.2** | **Live Stage Badges** | Observe the "PIPELINE EXECUTION STAGES" card as processing proceeds. | Each stage turns to `🔄 Running...` (cyan border) while active. Upon stage completion, it updates to `✅ Complete` (green) with exact latency and provider: <br>• OCR: `~1480 ms via CPUExecutionProvider`<br>• Simplify: `~10500 ms via LocalLLMExecutionEngine`<br>• Translate: `<10 ms via AnchorPreservedTranslationEngine`<br>• TTS: `~1100 ms via PiperTTS-ONNX`. | [ ] |

---

### 3. Clean Document Pass & Audio Playback
| # | Test Scenario | Steps | Expected Behavior | Pass/Fail |
|---|---|---|---|:---:|
| **3.1** | **Fidelity Verified Banner** | Wait for `form_document.png` or `medical_bill_receipt.png` to finish. | Prominent green banner appears: `🛡️ FIDELITY VERIFIED: 100% Entity Preservation Confirmed`. States that 100% of dates, amounts, IDs, and statuses survived without discrepancy. | [ ] |
| **3.2** | **Multi-Tab Inspection** | Click through the 4 tabs on the right: <br>• 🇮🇳 **Translated Text**<br>• 📝 **Simplified English**<br>• 🔍 **Raw OCR Text**<br>• 🛡️ **Fidelity Audit** | All 4 tabs are populated with high-contrast text: <br>• Tab 1 renders clean Devanagari Hindi text.<br>• Tab 2 renders 6th–8th grade plain English.<br>• Tab 3 renders verbatim TrOCR lines.<br>• Tab 4 renders the entity table with green `✅ Verified Intact` tags. | [ ] |
| **3.3** | **Clipboard Copying** | Click "📋 Copy Text" in any tab. Paste into Notepad. | Correct text is copied to clipboard without truncation. | [ ] |
| **3.4** | **Audio Playback** | In the Audio Player bar: <br>1. Click `▶ Play`.<br>2. Drag the scrub slider to 00:05.<br>3. Click `⏸ Pause`, then `▶ Play`.<br>4. Click `⏹ Stop`. | Audio plays cleanly through system speakers. Time label updates (`00:02 / 00:20`). Audio scrubber moves smoothly. Policy badge shows `🛡️ Clean Spoken Synthesis`. | [ ] |

---

### 4. Real Error States & Safety Policies (The 3 Core Scenarios)
| # | Test Scenario | Steps | Expected Behavior | Pass/Fail |
|---|---|---|---|:---:|
| **4.1** | **Blank / Corrupted Scan Short-Circuit** | In Python or Paint, create a pure white image `test_images/blank.png`. Load it into the UI and click "Process Document". | **Immediate short-circuit in <10 ms**: <br>• Prominent red error banner appears: `❌ PROCESSING HALTED: OCR detected unreadable or empty document text (low information density: std=0.00)...`.<br>• Stage 1 is marked `❌ Failed`.<br>• Stages 2, 3, and 4 are marked `⏸️ Skipped`.<br>• Zero compute wasted downstream. | [ ] |
| **4.2** | **TTS Synthesis Partial-Success** | Run the application with missing TTS assets or corrupted audio configuration. | **Graceful degradation to text-only mode**: <br>• Amber banner appears: `ℹ️ PARTIAL SUCCESS: Text Available (Audio Synthesis Degraded)`.<br>• Text tabs 1, 2, and 3 are **100% intact and readable**.<br>• Audio player is visibly disabled with message: `No audio file available for this document`. | [ ] |
| **4.3** | **Strict Safety Gate Audio Suppression** | 1. Check the box: `[x] Strict Safety Gate (Block audio on mismatch)`.<br>2. Load `test_images/telecom_disconnect_unseen.png` (conflicting $89.50 vs $889.50).<br>3. Click "Process Document". | **Audio suppression enforced**: <br>• Prominent red banner appears: `🚫 AUDIO GENERATION BLOCKED: Strict Safety Gate Active`.<br>• Text tabs are available for human inspection.<br>• Audio player is disabled with badge: `🚫 Audio Suppressed (Strict Mode)`. | [ ] |
| **4.4** | **Permissive Auditory Warning Prepending** | 1. Uncheck the box: `[ ] Strict Safety Gate`.<br>2. Load `test_images/telecom_disconnect_unseen.png`.<br>3. Click "Process Document".<br>4. Click `▶ Play` on audio player. | **Auditory warning policy applied**: <br>• Orange banner appears: `⚠️ FIDELITY SAFEGUARD TRIGGERED: Discrepancies Intercepted!`.<br>• Audio player badge shows `⚠️ Warning Prepended to Speech`.<br>• Audio speaks the authoritative Hindi warning first: *"चेतावनी: इस दस्तावेज़ में जानकारी की पुष्टि नहीं हो सकी है..."* before reading document terms. | [ ] |
