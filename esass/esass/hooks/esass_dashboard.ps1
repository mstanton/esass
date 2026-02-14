# ESASS Unified Dashboard - PowerShell Launcher
# Launches the dashboard in a properly sized terminal window

$Host.UI.RawUI.WindowTitle = "ESASS Unified Dashboard"

# Set working directory
Set-Location $PSScriptRoot

# Set console size
try {
    $Host.UI.RawUI.WindowSize = New-Object System.Management.Automation.Host.Size(110, 55)
    $Host.UI.RawUI.BufferSize = New-Object System.Management.Automation.Host.Size(110, 1000)
} catch {
    Write-Host "Note: Could not resize console window" -ForegroundColor Yellow
}

# Check for Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
}

if (-not $pythonCmd) {
    Write-Host "ERROR: Python not found in PATH" -ForegroundColor Red
    Write-Host "Please install Python or add it to your PATH"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting ESASS Unified Dashboard..." -ForegroundColor Cyan
Write-Host "Python: $pythonCmd" -ForegroundColor Gray

# Run the dashboard
& $pythonCmd esass_dashboard.py

# Keep window open if dashboard exits unexpectedly
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nDashboard exited with code: $LASTEXITCODE" -ForegroundColor Yellow
}
Read-Host "`nPress Enter to close"
