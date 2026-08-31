param(
    [switch]$InstallDev
)

$ErrorActionPreference = "Stop"

Write-Host "Creating virtual environment if missing..."
if (-not (Test-Path ".venv")) {
    py -3.12 -m venv .venv
}

$python = ".venv\Scripts\python.exe"
Write-Host "Upgrading pip..."
& $python -m pip install --upgrade pip

$target = ".[dev]"
if (-not $InstallDev) {
    $target = "."
}

Write-Host "Installing package $target ..."
& $python -m pip install -e $target

Write-Host "Done. Activate with: .venv\Scripts\Activate.ps1"
