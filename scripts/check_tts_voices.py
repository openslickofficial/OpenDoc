import os
import sys
import subprocess

sys.stdout.reconfigure(encoding="utf-8")

print("=" * 70)
print("1. CHECKING SYSTEM.SPEECH (SAPI5) VOICES")
print("=" * 70)
ps_code = """
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$installed = $synth.GetInstalledVoices()
Write-Host "Total SAPI5 voices found: $($installed.Count)"
foreach ($v in $installed) {
    Write-Host "Name: $($v.VoiceInfo.Name) | Culture: $($v.VoiceInfo.Culture) | Gender: $($v.VoiceInfo.Gender) | Enabled: $($v.Enabled)"
}
"""
try:
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True, encoding="utf-8")
    print(res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)
except Exception as e:
    print("Error querying System.Speech:", e)

print("\n" + "=" * 70)
print("2. CHECKING WINDOWS.MEDIA.SPEECHSYNTHESIS (ONECORE / WINRT) VOICES")
print("=" * 70)
ps_winrt = """
$allVoices = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType=WindowsRuntime]::AllVoices
Write-Host "Total WinRT OneCore voices found: $($allVoices.Count)"
foreach ($v in $allVoices) {
    Write-Host "ID: $($v.Id) | Display: $($v.DisplayName) | Lang: $($v.Language) | Gender: $($v.Gender)"
}
"""
try:
    res2 = subprocess.run(["powershell", "-NoProfile", "-Command", ps_winrt], capture_output=True, text=True, encoding="utf-8")
    print(res2.stdout)
    if res2.stderr:
        print("STDERR:", res2.stderr)
except Exception as e:
    print("Error querying Windows.Media.SpeechSynthesis:", e)

print("\n" + "=" * 70)
print("3. CHECKING QUALCOMM AI HUB CATALOG FOR TTS / SPEECH MODELS")
print("=" * 70)
try:
    import pkgutil
    import qai_hub_models.models
    models = [name for _, name, is_pkg in pkgutil.iter_modules(qai_hub_models.models.__path__) if is_pkg]
    tts_candidates = [m for m in models if any(k in m.lower() for k in ["tts", "speech", "voice", "audio", "indic", "vits", "fastspeech", "tacotron", "whisper", "melo", "piper"])]
    print(f"Total AI Hub models in catalog: {len(models)}")
    print(f"Audio/Speech/TTS models ({len(tts_candidates)}):")
    for c in tts_candidates:
        print(f"  - {c}")
    indic_models = [m for m in models if any(k in m.lower() for k in ["hindi", "indic", "devanagari", "tamil", "telugu", "bengali"])]
    print(f"Indic/Hindi models in catalog ({len(indic_models)}):")
    if not indic_models:
        print("  - NONE FOUND. Zero Indic/Hindi TTS models in Qualcomm AI Hub catalog.")
    else:
        for im in indic_models:
            print(f"  - {im}")
except Exception as e:
    print("Error inspecting qai_hub_models:", e)
