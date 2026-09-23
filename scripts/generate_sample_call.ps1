# Regenerates assets/audio/customer_support.wav from assets/audio/customer_support_call.txt
# with the Windows speech synthesizer, so the sample call is original, synthetic audio
# (issue #14). Lines start with "AGENT:" or "CUSTOMER:", which pick the voice.
#
# Run from the project root on Windows:
#   powershell -ExecutionPolicy Bypass -File scripts/generate_sample_call.ps1
#
# Voices differ between machines, so the output is not byte-identical everywhere; the
# transcript file is the source of truth.

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root "assets/audio/customer_support_call.txt"
$out = Join-Path $root "assets/audio/customer_support.wav"

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$installed = $synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo }
$female = ($installed | Where-Object { $_.Gender -eq "Female" } | Select-Object -First 1).Name
$male = ($installed | Where-Object { $_.Gender -eq "Male" } | Select-Object -First 1).Name
if (-not $female -or -not $male) {
    throw "Needs one female and one male voice installed; found: $($installed.Name -join ', ')"
}

$prompt = New-Object System.Speech.Synthesis.PromptBuilder
foreach ($line in Get-Content -Encoding UTF8 $script) {
    if ($line -match '^(AGENT|CUSTOMER):\s*(.+)$') {
        $voice = if ($Matches[1] -eq "AGENT") { $female } else { $male }
        $prompt.StartVoice($voice)
        $prompt.AppendText($Matches[2])
        $prompt.EndVoice()
        $prompt.AppendBreak([TimeSpan]::FromMilliseconds(500))
    }
}

# 16 kHz mono 16-bit: what Whisper resamples to anyway, and a quarter the size of 44.1 kHz stereo.
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$synth.SetOutputToWaveFile($out, $format)
$synth.Speak($prompt)
$synth.Dispose()
Write-Output "Wrote $out"
