# setup_fcc.ps1
# This script configures a virtual environment using system Python in C:\Program Files
# to bypass the Windows Application Control policy blocking AppData python DLLs.

# Target the verified Anaconda Python path which is whitelisted
$pythonPath = "C:\Users\soura\anaconda3\python.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Host "Anaconda Python not found. Searching for system-wide Python in C:\Program Files..." -ForegroundColor Cyan
    
    # Search in C:\Program Files\Python3* folders
    $folders = Get-ChildItem -Path "C:\Program Files" -Filter "Python3*" -Directory -ErrorAction SilentlyContinue
    foreach ($folder in $folders) {
        $exe = Join-Path $folder.FullName "python.exe"
        if (Test-Path $exe) {
            $pythonPath = $exe
            break
        }
    }
    
    if (-not $pythonPath) {
        # Check C:\Program Files (x86)
        $folders = Get-ChildItem -Path "C:\Program Files (x86)" -Filter "Python3*" -Directory -ErrorAction SilentlyContinue
        foreach ($folder in $folders) {
            $exe = Join-Path $folder.FullName "python.exe"
            if (Test-Path $exe) {
                $pythonPath = $exe
                break
            }
        }
    }
}

if ($pythonPath) {
    Write-Host "Found system Python at: $pythonPath" -ForegroundColor Green
    
    # Create the virtual environment
    Write-Host "Creating virtual environment .fcc_venv..." -ForegroundColor Cyan
    & $pythonPath -m venv .fcc_venv
    
    if (Test-Path ".fcc_venv\Scripts\Activate.ps1") {
        Write-Host "Installing free-claude-code inside .fcc_venv..." -ForegroundColor Cyan
        
        # Upgrade pip first, then install free-claude-code
        & .fcc_venv\Scripts\python.exe -m pip install --upgrade pip
        & .fcc_venv\Scripts\python.exe -m pip install free-claude-code
        
        Write-Host "`nSetup Complete!" -ForegroundColor Green
        Write-Host "To run fcc-server, execute these two commands in your terminal:" -ForegroundColor Green
        Write-Host "  .fcc_venv\Scripts\Activate.ps1" -ForegroundColor Yellow
        Write-Host "  fcc-server" -ForegroundColor Yellow
    } else {
        Write-Error "Failed to create virtual environment."
    }
} else {
    Write-Host "Could not find a Python installation in C:\Program Files or C:\Program Files (x86)." -ForegroundColor Red
    Write-Host "Please download the official Python installer (from python.org)," -ForegroundColor Yellow
    Write-Host "run it, and make sure to select 'Install for all users' (which puts it in C:\Program Files)." -ForegroundColor Yellow
}
