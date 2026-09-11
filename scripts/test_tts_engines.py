import os
import sys
import subprocess

sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("audio_output", exist_ok=True)

test_hindi_text = "आवेदन संख्या SN-2026-X89। स्थिति: सत्यापित और स्वीकृत।"

print("=" * 70)
print("TEST 1: Testing SAPI5 (System.Speech) with installed voices")
print("=" * 70)

ps_sapi = r"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$wavPath = [System.IO.Path]::GetFullPath("audio_output/test_sapi5.wav")
$synth.SetOutputToWaveFile($wavPath)
$synth.Speak("Verification form. Application ID: SN-2026-X89. Status: Verified and Approved.")
$synth.Dispose()
Write-Host "SAPI5 Audio written to: $wavPath"
"""

with open("scripts/sapi_test.ps1", "w", encoding="utf-8") as f:
    f.write(ps_sapi)

res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/sapi_test.ps1"], capture_output=True, text=True, encoding="utf-8")
print("STDOUT:", res.stdout.strip())
if res.stderr:
    print("STDERR:", res.stderr.strip())

if os.path.exists("audio_output/test_sapi5.wav"):
    print(f"File created: audio_output/test_sapi5.wav ({os.path.getsize('audio_output/test_sapi5.wav')} bytes)")

print("\n" + "=" * 70)
print("TEST 2: Testing WinRT (Windows.Media.SpeechSynthesis) OneCore voices")
print("=" * 70)

ps_winrt = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

$synthesizer = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
# Find an Indian voice if available (e.g. Heera or Ravi)
$voice = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.Language -like "*IN*" -or $_.DisplayName -like "*Ravi*" -or $_.DisplayName -like "*Heera*" } | Select-Object -First 1
if ($voice) {
    Write-Host "Selected WinRT Voice: $($voice.DisplayName) ($($voice.Language))"
    $synthesizer.Voice = $voice
} else {
    Write-Host "Default WinRT Voice: $($synthesizer.Voice.DisplayName)"
}

$textToSpeak = "Application ID: SN-2026-X89. Status: Verified and approved."
$op = $synthesizer.SynthesizeTextToStreamAsync($textToSpeak)
$stream = Await $op ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])

$bytes = New-Object byte[] ($stream.Size)
$reader = New-Object Windows.Storage.Streams.DataReader($stream)
$loadOp = $reader.LoadAsync($stream.Size)
$null = Await $loadOp ([uint32])
$reader.ReadBytes($bytes)

[System.IO.File]::WriteAllBytes("audio_output/test_winrt.wav", $bytes)
Write-Host "WinRT Audio written to audio_output/test_winrt.wav ($($bytes.Length) bytes)"
"""

with open("scripts/winrt_test.ps1", "w", encoding="utf-8") as f:
    f.write(ps_winrt)

res2 = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/winrt_test.ps1"], capture_output=True, text=True, encoding="utf-8")
print("STDOUT:", res2.stdout.strip())
if res2.stderr:
    print("STDERR:", res2.stderr.strip())

if os.path.exists("audio_output/test_winrt.wav"):
    print(f"File created: audio_output/test_winrt.wav ({os.path.getsize('audio_output/test_winrt.wav')} bytes)")
