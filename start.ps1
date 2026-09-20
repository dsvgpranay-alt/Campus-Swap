$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    throw "Python was not found on PATH. Install Python or activate the project environment first."
}

$ClassifierPath = Join-Path $ProjectRoot "runs\classify\campus_swap\weights\best.pt"
if (-not (Test-Path -LiteralPath $ClassifierPath -PathType Leaf)) {
    throw "Classifier checkpoint not found at '$ClassifierPath'. Finish train_classifier.py first."
}

$env:CLASSIFIER_MODEL_PATH = $ClassifierPath

Write-Host "Starting Campus Swap..." -ForegroundColor Cyan
Write-Host "Classifier: $ClassifierPath"
Write-Host "Device: Ultralytics will select the available device automatically."
Write-Host "Open http://127.0.0.1:5000 after Flask starts. Press Ctrl+C to stop."

& $PythonCommand.Source app.py
