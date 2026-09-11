
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
