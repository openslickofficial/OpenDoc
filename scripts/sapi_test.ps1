
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$wavPath = [System.IO.Path]::GetFullPath("audio_output/test_sapi5.wav")
$synth.SetOutputToWaveFile($wavPath)
$synth.Speak("Verification form. Application ID: SN-2026-X89. Status: Verified and Approved.")
$synth.Dispose()
Write-Host "SAPI5 Audio written to: $wavPath"
