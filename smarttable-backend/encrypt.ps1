# ============================================================
# PyArmor Encryption - SmartTable Backend
# Python 3.12 + PyArmor 9.3.0
# ============================================================
# Trial version limits:
#   - Can only encrypt ONE top-level resource (package = 1 resource)
#   - Cannot encrypt big script (code object > 32768 B) -- split done
#   - --restrict causes import failures, do NOT use it
#
# Strategy:
#   - Encrypt app/ package ONLY (1 top-level resource)
#   - Encrypted output mirrors source structure
#   - run.py stays plaintext (encrypting it requires full license)
#
# Verification:
#   cd dist\pyarmor
#   python -c "from app import create_app; app=create_app(); print(f'OK: {len(list(app.blueprints))} blueprints')"
# ============================================================

# NOTE: PyArmor writes INFO to stderr, PowerShell 5 treats stderr as errors.
# - Do NOT set $ErrorActionPreference = "Stop" here (it would abort on stderr)
# - Use 2>&1 to merge stderr into stdout, so INFO lines appear as normal output
# - Check $LASTEXITCODE (process exit code, always reliable) instead of error stream
$ErrorActionPreference = "Continue"
$PYARMOR = "C:\Users\Administrator\AppData\Local\Python\pythoncore-3.12-64\Scripts\pyarmor.exe"
$BACKEND = Split-Path -Parent $MyInvocation.MyCommand.Path
$OUTDIR  = Join-Path $BACKEND "dist\pyarmor"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SmartTable Backend - PyArmor Encryption" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  PyArmor : $PYARMOR"
Write-Host "  Backend : $BACKEND"
Write-Host "  Output  : $OUTDIR"
Write-Host ""

# Step 1: Clean old output
Write-Host "[1/3] Cleaning old output..." -ForegroundColor Yellow
if (Test-Path $OUTDIR) { Remove-Item $OUTDIR -Recurse -Force }

# Step 2: Run PyArmor gen
# 2>&1 merges stderr (INFO messages) into stdout so they display normally;
# $LASTEXITCODE still reflects the REAL process exit code (0 = success).
Write-Host "[2/3] Running PyArmor gen..." -ForegroundColor Yellow
& $PYARMOR gen `
    -O $OUTDIR `
    -r `
    --obf-code 1 `
    --exclude "*/tests/*" `
    --exclude "*/test_*.py" `
    --exclude "*/.env*" `
    --exclude "*/Dockerfile*" `
    --exclude "*.bak_before_split" `
    --exclude "*/__pycache__/*" `
    (Join-Path $BACKEND "app") `
    2>&1 | ForEach-Object { Write-Host $_ }
$pyarmor_rc = $LASTEXITCODE

# Step 3: Copy launcher files
Write-Host "[3/3] Copying launcher files..." -ForegroundColor Yellow
foreach ($f in @("run.py", "create_tables.py", ".env.example")) {
    $src = Join-Path $BACKEND $f
    if (Test-Path $src) { Copy-Item $src $OUTDIR -Force }
}

Write-Host ""
if ($pyarmor_rc -eq 0 -and (Test-Path (Join-Path $OUTDIR "app\__init__.py"))) {
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  DONE!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  Encrypted output : $OUTDIR"
    Write-Host ""
    Write-Host "  To run:" -ForegroundColor Cyan
    Write-Host "    cd $OUTDIR"
    Write-Host "    python run.py"
} else {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "  PyArmor exit code : $pyarmor_rc"
    Write-Host "  Output dir exists : $(Test-Path $OUTDIR)"
    exit 1
}
