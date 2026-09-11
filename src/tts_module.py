"""
On-Device Text-to-Speech (TTS) Module for Snapdragon X Document Assistant.

Architecture:
1. Primary On-Device Engine (Default):
   - Piper TTS ONNX model (hi_IN-pratham-medium) executing locally via ONNX Runtime.
   - 100% offline, native ONNX inference targeting Hexagon NPU (QNNExecutionProvider)
     with automatic fallback to CPUExecutionProvider.
   - MIT licensed, embedded phoneme frontend (espeak-ng Hindi tables).
2. Offline System Fallback:
   - Windows SAPI5 / WinRT system voice fallback when Piper assets are unavailable.
3. Optional Enhanced Quality Cloud Mode:
   - Microsoft EdgeTTS neural speech (hi-IN-SwaraNeural), explicitly flagged as
     "Optional Online Mode (Requires Internet)" and never active by default.
4. Spoken-Friendly Indic Normalization & Anchor-Survival Safeguard:
   - Normalizes currency ($250.00 -> दो सौ पचास डॉलर), dates (October 18, 2026 -> अठारह अक्टूबर दो हज़ार छब्बीस),
     and alphanumeric reference IDs (TEL-542-1-CA -> टी ई एल डैश पांच चार दो...).
   - Validates that factual anchors survive text normalization into spoken words.
5. Fidelity-Gated Speech Policy:
   - When document fidelity verification fails (fidelity_passed == False), an audible Hindi
     warning is prepended to the speech output:
     "चेतावनी: इस दस्तावेज़ में जानकारी की पुष्टि नहीं हो सकी है। कृपया मूल दस्तावेज़ की जाँच करें।"
   - In strict mode (strict_fidelity_gate=True), audio generation on unverified text is completely
     blocked to protect vulnerable users from hearing corrupted amounts or dates.
"""

import os
import sys
import re
import time
import wave
import logging
from typing import Dict, Any, Optional, List, Tuple

# Structured logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TTSModule] %(message)s",
)
logger = logging.getLogger("TTSModule")

from src.config import PROJECT_ROOT
DEFAULT_AUDIO_DIR = os.path.join(PROJECT_ROOT, "audio_output")
PIPER_MODEL_DIR = os.path.join(PROJECT_ROOT, "models", "piper_hi")
PIPER_ONNX_PATH = os.path.join(PIPER_MODEL_DIR, "hi_IN-pratham-medium.onnx")
PIPER_CONFIG_PATH = os.path.join(PIPER_MODEL_DIR, "hi_IN-pratham-medium.onnx.json")


# ==============================================================================
# 1. HINDI SPOKEN TEXT NORMALIZER & ANCHOR SURVIVAL
# ==============================================================================

HINDI_UNITS_0_TO_99 = {
    0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पांच", 6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
    11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह", 16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस",
    21: "इक्कीस", 22: "बाईस", 23: "तेईस", 24: "चौबीस", 25: "पच्चीस", 26: "छब्बीस", 27: "सत्ताईस", 28: "अट्ठाईस", 29: "उनतीस", 30: "तीस",
    31: "इकतीस", 32: "बत्तीस", 33: "तैंतीस", 34: "चौंतीस", 35: "पैंतीस", 36: "छत्तीस", 37: "सैंतीस", 38: "अड़तीस", 39: "उनतालीस", 40: "चालीस",
    41: "इकतालीस", 42: "बयालीस", 43: "तैंतालीस", 44: "चवालीस", 45: "पैंतालीस", 46: "छियालीस", 47: "सैंतालीस", 48: "अड़तालीस", 49: "उनचास", 50: "पचास",
    51: "इक्यावन", 52: "बावन", 53: "तिरेपन", 54: "चौवन", 55: "पचपन", 56: "छप्पन", 57: "सत्तावन", 58: "अट्ठावन", 59: "उनसठ", 60: "साठ",
    61: "इकसठ", 62: "बासठ", 63: "तिरेसठ", 64: "चौंसठ", 65: "पैंसठ", 66: "छियासठ", 67: "सरसठ", 68: "अड़सठ", 69: "उनहत्तर", 70: "सत्तर",
    71: "इकहत्तर", 72: "बहत्तर", 73: "तिहत्तर", 74: "चौहत्तर", 75: "पचहत्तर", 76: "छिहत्तर", 77: "सतहत्तर", 78: "अठहत्तर", 79: "उन्नासी", 80: "अस्सी",
    81: "इक्यासी", 82: "बयासी", 83: "तिरासी", 84: "चौरासी", 85: "पचासी", 86: "छियासी", 87: "सत्तासी", 88: "अट्ठासी", 89: "नवासी", 90: "नब्बे",
    91: "इक्यानवे", 92: "बानवे", 93: "तिरानवे", 94: "चौरानवे", 95: "पंचानवे", 96: "छियानवे", 97: "सत्तानवे", 98: "अट्ठानवे", 99: "निन्यानवे"
}

HINDI_MONTHS = {
    1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल", 5: "मई", 6: "जून",
    7: "जुलाई", 8: "अगस्त", 9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर",
    "january": "जनवरी", "february": "फ़रवरी", "march": "मार्च", "april": "अप्रैल",
    "may": "मई", "june": "जून", "july": "जुलाई", "august": "अगस्त",
    "september": "सितंबर", "october": "अक्टूबर", "november": "नवंबर", "december": "दिसंबर",
    "jan": "जनवरी", "feb": "फ़रवरी", "mar": "मार्च", "apr": "अप्रैल",
    "jun": "जून", "jul": "जुलाई", "aug": "अगस्त", "sep": "सितंबर", "sept": "सितंबर",
    "oct": "अक्टूबर", "nov": "नवंबर", "dec": "दिसंबर"
}

ENGLISH_LETTERS_TO_HINDI = {
    'A': 'ए', 'B': 'बी', 'C': 'सी', 'D': 'डी', 'E': 'ई', 'F': 'एफ', 'G': 'जी',
    'H': 'एच', 'I': 'आई', 'J': 'जे', 'K': 'के', 'L': 'एल', 'M': 'एम', 'N': 'एन',
    'O': 'ओ', 'P': 'पी', 'Q': 'क्यू', 'R': 'आर', 'S': 'एस', 'T': 'टी', 'U': 'यू',
    'V': 'वी', 'W': 'डब्लू', 'X': 'एक्स', 'Y': 'वाई', 'Z': 'ज़ेड'
}

DIGIT_TO_HINDI = {
    '0': 'शून्य', '1': 'एक', '2': 'दो', '3': 'तीन', '4': 'चार',
    '5': 'पांच', '6': 'छह', '7': 'सात', '8': 'आठ', '9': 'नौ'
}


def number_to_hindi_words(n: int) -> str:
    """Recursively converts an integer to clean Hindi spoken words."""
    if n < 0:
        return "ऋण " + number_to_hindi_words(-n)
    if n < 100:
        return HINDI_UNITS_0_TO_99.get(n, str(n))
    if n < 1000:
        hundreds = n // 100
        rem = n % 100
        res = f"{HINDI_UNITS_0_TO_99.get(hundreds, str(hundreds))} सौ"
        if rem > 0:
            res += f" {number_to_hindi_words(rem)}"
        return res
    if n < 100000:
        thousands = n // 1000
        rem = n % 1000
        res = f"{number_to_hindi_words(thousands)} हज़ार"
        if rem > 0:
            res += f" {number_to_hindi_words(rem)}"
        return res
    if n < 10000000:
        lakhs = n // 100000
        rem = n % 100000
        res = f"{number_to_hindi_words(lakhs)} लाख"
        if rem > 0:
            res += f" {number_to_hindi_words(rem)}"
        return res
    crores = n // 10000000
    rem = n % 10000000
    res = f"{number_to_hindi_words(crores)} करोड़"
    if rem > 0:
        res += f" {number_to_hindi_words(rem)}"
    return res


def normalize_currency_match(m) -> str:
    symbol = m.group(1).strip()
    whole_str = m.group(2).replace(',', '')
    frac_str = m.group(3)
    whole = int(whole_str)

    currency_main = "डॉलर" if symbol == "$" else "रुपये"
    currency_sub = "सेंट" if symbol == "$" else "पैसे"

    whole_words = number_to_hindi_words(whole)
    if frac_str and int(frac_str) > 0:
        frac = int(frac_str)
        frac_words = number_to_hindi_words(frac)
        return f"{whole_words} {currency_main} {frac_words} {currency_sub}"
    else:
        return f"{whole_words} {currency_main}"


def normalize_date_text_match(m) -> str:
    g1, g2, g3 = m.group(1), m.group(2), m.group(3)
    if g1.lower() in HINDI_MONTHS:
        month = HINDI_MONTHS[g1.lower()]
        day = int(g2)
        year = int(g3)
    else:
        day = int(g1)
        month = HINDI_MONTHS[g2.lower()]
        year = int(g3)
    day_words = number_to_hindi_words(day)
    year_words = number_to_hindi_words(year)
    return f"{day_words} {month} {year_words}"


def normalize_iso_date_match(m) -> str:
    p1, p2, p3 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if p1 > 1000:
        year, month_idx, day = p1, p2, p3
    else:
        day, month_idx, year = p1, p2, p3
    month = HINDI_MONTHS.get(month_idx, str(month_idx))
    day_words = number_to_hindi_words(day)
    year_words = number_to_hindi_words(year)
    return f"{day_words} {month} {year_words}"


def normalize_alphanumeric_code(m) -> str:
    code = m.group(0)
    parts = []
    for token in re.split(r'([-_/])', code):
        if token in ('-', '_', '/'):
            parts.append("डैश")
        elif token.isdigit():
            digits = [DIGIT_TO_HINDI.get(d, d) for d in token]
            parts.append(" ".join(digits))
        else:
            letters = [ENGLISH_LETTERS_TO_HINDI.get(c.upper(), c) for c in token]
            parts.append(" ".join(letters))
    return " ".join(parts)


def normalize_for_spoken_hindi(text: str) -> str:
    """
    Normalizes Hindi translation text for high-fidelity speech synthesis.
    Converts numbers, currencies, dates, and codes to Devanagari words to prevent
    the TTS engine from dropping digits or spelling punctuation literally.
    """
    if not text:
        return ""

    res = text

    # 1. Normalize currency: $250.00, $250, ₹1,250.00, Rs. 250
    curr_full_regex = r'([\$₹]|Rs\.?|INR)\s*(\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d{2}))?'
    res = re.sub(curr_full_regex, normalize_currency_match, res, flags=re.IGNORECASE)

    # 2. Text dates: October 18, 2026 or 18 October 2026
    month_names = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)'
    date_text_1 = rf'\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b'
    date_text_2 = rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names}),?\s+(\d{{4}})\b'
    res = re.sub(date_text_1, normalize_date_text_match, res, flags=re.IGNORECASE)
    res = re.sub(date_text_2, normalize_date_text_match, res, flags=re.IGNORECASE)

    # 3. Numeric dates: 2026-10-18 or 18/10/2026 or 18-10-2026
    iso_date_regex = r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b'
    dmy_date_regex = r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b'
    res = re.sub(iso_date_regex, normalize_iso_date_match, res)
    res = re.sub(dmy_date_regex, normalize_iso_date_match, res)

    # 4. Alphanumeric codes & reference IDs: TEL-55421-CA, GOV-2026-LAW-77, MED-9921-X
    code_regex = r'\b(?=[A-Z0-9_-]{4,25}\b)(?:[A-Z]+[-_][A-Z0-9_-]+|[0-9]+[-_][A-Z0-9_-]+)\b'
    res = re.sub(code_regex, normalize_alphanumeric_code, res)

    # 5. Standalone numbers with commas or decimals: e.g. 1,250 or 250
    def norm_num(m):
        raw = m.group(0).replace(',', '')
        if '.' in raw:
            parts = raw.split('.')
            w = number_to_hindi_words(int(parts[0]))
            f_digits = [DIGIT_TO_HINDI.get(d, d) for d in parts[1]]
            return f"{w} दशमलव {' '.join(f_digits)}"
        else:
            return number_to_hindi_words(int(raw))

    res = re.sub(r'\b\d{1,3}(?:,\d{3})+\b|\b\d{1,7}\b', norm_num, res)

    # 6. Smooth field separators: e.g. "राशि: " -> "राशि। "
    res = re.sub(r':\s*', '। ', res)

    # 7. Convert ASCII full stops to Devanagari purna viram for natural speech pauses
    res = re.sub(r'\.\s*', '। ', res)

    # Clean whitespace
    res = re.sub(r'[ \t]+', ' ', res).strip()
    return res


def verify_normalization_anchor_survival(original_text: str, normalized_text: str) -> Dict[str, Any]:
    """
    Safeguard checking that factual anchors in original text survived into normalized speech text.
    Verifies that amounts and dates were converted into valid Hindi words rather than dropped.
    """
    dropped = []
    
    # 1. Check amounts
    amounts = re.findall(r'[\$₹]\s*(\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d{2}))?', original_text)
    for whole_str, frac_str in amounts:
        whole = int(whole_str.replace(',', ''))
        whole_words = number_to_hindi_words(whole)
        if whole_words not in normalized_text:
            dropped.append(f"Amount '{whole_str}' (expected words '{whole_words}') missing from normalized speech text")

    # 2. Check dates
    years = re.findall(r'\b(20\d{2})\b', original_text)
    for y in set(years):
        y_words = number_to_hindi_words(int(y))
        if y_words not in normalized_text:
            dropped.append(f"Year '{y}' (expected words '{y_words}') missing from normalized speech text")

    return {
        "anchors_survived": len(dropped) == 0,
        "dropped_anchors": dropped,
        "checked_amounts_count": len(amounts),
        "checked_years_count": len(set(years))
    }


# ==============================================================================
# 2. PRONUNCIATION & NORMALIZATION QUALITY AUDIT
# ==============================================================================

def verify_speech_normalization(original_text: str, normalized_text: str) -> Dict[str, Any]:
    """
    Audits whether numbers, dates, and currency were transformed into spoken-friendly form.
    """
    warnings = []
    passed = True

    # 1. Currency audit: check if raw currency symbols remain
    unnormalized_currencies = re.findall(r'[\$₹]\s*\d+', normalized_text)
    if unnormalized_currencies:
        warnings.append(f"Unnormalized currency symbols detected: {unnormalized_currencies}")
        passed = False

    # 2. Raw numeric date audit
    unnormalized_dates = re.findall(r'\b\d{1,4}[-/]\d{1,2}[-/]\d{2,4}\b', normalized_text)
    if unnormalized_dates:
        warnings.append(f"Unnormalized numeric dates detected: {unnormalized_dates}")
        passed = False

    # 3. Raw standalone digits audit
    raw_digits = re.findall(r'\b\d+\b', normalized_text)
    if raw_digits:
        warnings.append(f"Unnormalized raw digits detected: {raw_digits[:5]}")
        passed = False

    return {
        "normalization_passed": passed,
        "warnings": warnings,
        "unnormalized_currencies": unnormalized_currencies,
        "unnormalized_dates": unnormalized_dates,
        "raw_digits_remaining": len(raw_digits),
    }


# ==============================================================================
# 3. ON-DEVICE PIPER TTS ENGINE (PRIMARY / DEFAULT)
# ==============================================================================

_PIPER_VOICE_INSTANCE = None

def _get_piper_voice():
    """Loads and caches the local Piper ONNX voice instance."""
    global _PIPER_VOICE_INSTANCE
    if _PIPER_VOICE_INSTANCE is None:
        if not os.path.exists(PIPER_ONNX_PATH):
            raise FileNotFoundError(f"Piper ONNX model not found at {PIPER_ONNX_PATH}")
        from piper.voice import PiperVoice
        import onnxruntime as ort

        logger.info("Initializing on-device Piper ONNX TTS engine from %s...", os.path.basename(PIPER_ONNX_PATH))
        voice = PiperVoice.load(PIPER_ONNX_PATH, config_path=PIPER_CONFIG_PATH)

        # Configure QNNExecutionProvider if available on Snapdragon X Elite ARM64
        available_providers = ort.get_available_providers()
        preferred_providers = (
            ["QNNExecutionProvider", "CPUExecutionProvider"]
            if "QNNExecutionProvider" in available_providers
            else ["CPUExecutionProvider"]
        )
        voice.session = ort.InferenceSession(PIPER_ONNX_PATH, providers=preferred_providers)
        logger.info("Piper ONNX session configured with execution providers: %s", voice.session.get_providers())
        _PIPER_VOICE_INSTANCE = voice

    return _PIPER_VOICE_INSTANCE


def _synthesize_piper_wav(text: str, output_path: str) -> Tuple[str, str, float]:
    """Synthesizes text to a WAV file completely on-device using Piper ONNX."""
    voice = _get_piper_voice()
    providers = voice.session.get_providers()
    provider_str = f"PiperTTS-ONNX (hi_IN-pratham on {providers[0]})"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with wave.open(output_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file, set_wav_format=True)

    # Compute duration from WAV header
    with wave.open(output_path, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        duration_ms = (frames / float(rate)) * 1000.0

    return output_path, provider_str, round(duration_ms, 2)


# ==============================================================================
# 4. OPTIONAL CLOUD & OFFLINE FALLBACK ENGINES
# ==============================================================================

def _synthesize_sapi_fallback(text: str, output_path: str) -> Tuple[str, str, float]:
    """Offline system fallback via Windows SAPI5 synthesizer."""
    import subprocess
    logger.info("Synthesizing via Windows SAPI5 offline fallback...")
    ps_cmd = f"""
    Add-Type -AssemblyName System.Speech
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.SetOutputToWaveFile('{output_path}')
    $s.Speak('{text.replace("'", " ")}')
    $s.Dispose()
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    
    duration_ms = 0.0
    if os.path.exists(output_path):
        try:
            with wave.open(output_path, "rb") as wf:
                duration_ms = (wf.getnframes() / float(wf.getframerate())) * 1000.0
        except Exception:
            pass
    return output_path, "Windows-SAPI-Offline-Fallback", round(duration_ms, 2)


async def _synthesize_edge_tts_cloud(text: str, output_path: str) -> Tuple[str, str, float]:
    """Optional enhanced-quality cloud synthesizer (requires internet connection)."""
    import edge_tts
    voice_name = "hi-IN-SwaraNeural"
    communicate = edge_tts.Communicate(text, voice_name)
    audio_data = bytearray()
    boundaries = []
    
    async for chunk in communicate.stream():
        chunk_type = chunk.get("type")
        if chunk_type == "audio":
            audio_data.extend(chunk["data"])
        elif chunk_type in ("WordBoundary", "SentenceBoundary"):
            boundaries.append(chunk)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(audio_data)

    duration_ms = 0.0
    if boundaries:
        last_b = boundaries[-1]
        duration_ms = (last_b.get("offset", 0) + last_b.get("duration", 0)) / 10000.0

    return output_path, f"EdgeTTS-Cloud (Optional Online Quality Mode - {voice_name})", round(duration_ms, 2)


# ==============================================================================
# 5. MAIN SYNTHESIZE SPEECH INTERFACE WITH FIDELITY GATING
# ==============================================================================

# Spoken auditory warning prepended when fidelity verification fails
FIDELITY_WARNING_PROMPT_HI = "चेतावनी: इस दस्तावेज़ में जानकारी की पुष्टि नहीं हो सकी है। कृपया मूल दस्तावेज़ की जाँच करें।"


def synthesize_speech(
    text: str,
    lang: str = "hi",
    fidelity_passed: bool = True,
    strict_fidelity_gate: bool = False,
    use_online_enhancement: bool = False,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Standard project interface for Speech Synthesis with Fidelity-Gated Security.

    Parameters:
        text: Final translated text to synthesize.
        lang: Target language code ('hi' for Hindi).
        fidelity_passed: Fidelity check status from Stage 2 / Stage 3.
        strict_fidelity_gate: If True, completely blocks speech when fidelity_passed is False.
        use_online_enhancement: If True, opts into cloud EdgeTTS. Default is FALSE (100% on-device).
        output_dir: Audio output folder.

    Returns:
        {
            "audio_path": str,
            "provider_used": str,
            "latency_ms": float,
            "duration_ms": float,
            "normalized_text": str,
            "fidelity_gate": {
                "fidelity_passed": bool,
                "warning_prepended": bool,
                "blocked": bool,
                "policy_applied": str
            },
            "anchor_survival": dict,
            "pronunciation_audit": dict
        }
    """
    if output_dir is None:
        output_dir = DEFAULT_AUDIO_DIR
    os.makedirs(output_dir, exist_ok=True)

    start_time = time.perf_counter()

    # Step 1: Fidelity-Gated Policy Decision
    warning_prepended = False
    if not fidelity_passed:
        if strict_fidelity_gate:
            logger.warning("[SPEECH FIDELITY GATE] STRICT BLOCK: Audio synthesis suppressed due to failed document fidelity.")
            return {
                "audio_path": None,
                "provider_used": "FidelityGate-Suppressed",
                "latency_ms": 0.0,
                "duration_ms": 0.0,
                "normalized_text": text,
                "fidelity_gate": {
                    "fidelity_passed": False,
                    "warning_prepended": False,
                    "blocked": True,
                    "policy_applied": "strict_suppress (audio generation halted on unverified document content)"
                },
                "anchor_survival": {"anchors_survived": False, "dropped_anchors": ["Blocked by fidelity safeguard"]},
                "pronunciation_audit": {"normalization_passed": False, "warnings": ["Blocked by fidelity safeguard"]}
            }
        else:
            logger.warning("[SPEECH FIDELITY GATE] PREPEND WARNING: Prepending auditory warning due to failed document fidelity.")
            text = f"{FIDELITY_WARNING_PROMPT_HI}। {text}"
            warning_prepended = True

    # Step 2: Spoken-friendly normalization
    normalized_text = normalize_for_spoken_hindi(text) if lang.lower().startswith("hi") else text

    # Step 3: Anchor-Survival Audit
    anchor_survival = verify_normalization_anchor_survival(text, normalized_text)
    if not anchor_survival["anchors_survived"]:
        for drop_warn in anchor_survival["dropped_anchors"]:
            logger.warning("[ANCHOR NORMALIZATION WARNING] %s", drop_warn)

    # Step 4: Engine Selection & Synthesis
    file_id = f"speech_{int(time.time() * 1000)}"

    if use_online_enhancement:
        # User explicitly opted into cloud enhancement
        logger.info("Using OPTIONAL Online Quality Mode (EdgeTTS Cloud)...")
        output_path = os.path.join(output_dir, f"{file_id}.mp3")
        import asyncio
        audio_path, provider_used, duration_ms = asyncio.run(_synthesize_edge_tts_cloud(normalized_text, output_path))
    else:
        # DEFAULT: 100% On-Device Offline Piper ONNX Engine
        output_path = os.path.join(output_dir, f"{file_id}.wav")
        try:
            audio_path, provider_used, duration_ms = _synthesize_piper_wav(normalized_text, output_path)
        except Exception as e:
            logger.error("On-device Piper synthesis failed (%s). Falling back to SAPI5...", e)
            audio_path, provider_used, duration_ms = _synthesize_sapi_fallback(normalized_text, output_path)

    end_time = time.perf_counter()
    latency_ms = round((end_time - start_time) * 1000.0, 2)

    # Step 5: Pronunciation audit
    pronunciation_audit = verify_speech_normalization(text, normalized_text)

    logger.info(
        "TTS Complete: %.2f ms | Provider: %s | Duration: %.2f s | Warning Prepended: %s",
        latency_ms,
        provider_used,
        duration_ms / 1000.0,
        warning_prepended
    )

    return {
        "audio_path": audio_path,
        "provider_used": provider_used,
        "latency_ms": latency_ms,
        "duration_ms": duration_ms,
        "normalized_text": normalized_text,
        "fidelity_gate": {
            "fidelity_passed": fidelity_passed,
            "warning_prepended": warning_prepended,
            "blocked": False,
            "policy_applied": "warning_prepended" if warning_prepended else "clean_pass"
        },
        "anchor_survival": anchor_survival,
        "pronunciation_audit": pronunciation_audit,
    }
