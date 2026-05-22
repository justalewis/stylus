# Installs every optional dependency for Graphion's advanced features.
# Uses Chocolatey (auto-installed if absent).
#
# Usage (run as Administrator):
#   cd C:\Users\Justin\Desktop\LiCS-Pipeline
#   powershell -ExecutionPolicy Bypass -File .\install-graphion-deps.ps1
#
# Idempotent: safe to re-run. Already-installed packages are skipped.

$ErrorActionPreference = "Continue"

function Section($title) {
  Write-Host ""
  Write-Host "==== $title ====" -ForegroundColor Cyan
}

function Have-Command($name) {
  $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

# ---------- Chocolatey bootstrap ----------

Section "Checking for Chocolatey"
if (-not (Have-Command choco)) {
  Write-Host "Chocolatey not found. Installing it now (one-time)..."
  Set-ExecutionPolicy Bypass -Scope Process -Force
  [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
  try {
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
  } catch {
    Write-Host "Chocolatey install failed: $_" -ForegroundColor Red
    Write-Host "Install manually from https://chocolatey.org/install then re-run this script." -ForegroundColor Yellow
    exit 1
  }
  # Refresh PATH for this session so 'choco' is callable below.
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
if (-not (Have-Command choco)) {
  Write-Host "Chocolatey still not callable after install. Open a NEW Admin PowerShell and re-run this script." -ForegroundColor Red
  exit 1
}
Write-Host "Chocolatey OK"

# ---------- Native tools via Chocolatey ----------

Section "Installing native tools via Chocolatey"
$packages = @(
  @{ Id = "libreoffice-fresh";  Name = "LibreOffice" },
  @{ Id = "tesseract";          Name = "Tesseract OCR" },
  @{ Id = "nodejs-lts";         Name = "Node.js LTS" },
  @{ Id = "temurin21jre";       Name = "Java (Temurin 21 JRE)" },
  @{ Id = "gtk-runtime";        Name = "GTK3 Runtime (for WeasyPrint)" }
)
foreach ($p in $packages) {
  Write-Host ""
  Write-Host (">> " + $p.Name + " [" + $p.Id + "]") -ForegroundColor Yellow
  choco install $p.Id -y --no-progress
  if ($LASTEXITCODE -ne 0) {
    Write-Host ("   (choco returned " + $LASTEXITCODE + " - may already be installed)") -ForegroundColor DarkYellow
  }
}

# ---------- verapdf (no Chocolatey package - direct download) ----------

Section "Installing verapdf CLI to C:\Tools\verapdf"
$verapdfDir = "C:\Tools\verapdf"
if (Test-Path "$verapdfDir\verapdf.bat") {
  Write-Host "verapdf already at $verapdfDir - skipping"
} else {
  New-Item -ItemType Directory -Force -Path "C:\Tools" | Out-Null
  $zipUrl = "https://software.verapdf.org/releases/verapdf-installer-1.27.50.zip"
  $zipOut = "$env:TEMP\verapdf.zip"
  Write-Host "Downloading $zipUrl ..."
  try {
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipOut -UseBasicParsing
    Expand-Archive -Path $zipOut -DestinationPath "C:\Tools" -Force
    $extracted = Get-ChildItem "C:\Tools" -Directory | Where-Object { $_.Name -like "verapdf*" } | Select-Object -First 1
    if ($extracted -and $extracted.FullName -ne $verapdfDir) {
      if (Test-Path $verapdfDir) { Remove-Item $verapdfDir -Recurse -Force }
      Rename-Item -Path $extracted.FullName -NewName "verapdf"
    }
    Write-Host "verapdf extracted to $verapdfDir"
  } catch {
    Write-Host "verapdf download failed: $_" -ForegroundColor Red
    Write-Host "Get it manually from https://verapdf.org/software/ and unzip to $verapdfDir"
  }
}

# ---------- PATH (verapdf only - Chocolatey handles the others) ----------

Section "Updating PATH (persistent, user-level)"
$pathsToAdd = @("$verapdfDir")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
foreach ($p in $pathsToAdd) {
  if ($userPath -notlike "*$p*") {
    Write-Host "Adding $p to user PATH"
    [Environment]::SetEnvironmentVariable("Path", ($userPath + ";" + $p), "User")
    $userPath = $userPath + ";" + $p
  } else {
    Write-Host "$p already in user PATH"
  }
}

# ---------- Python packages ----------

Section "Installing Python packages from requirements.txt"
$reqPath = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $reqPath) {
  pip install -r $reqPath
} else {
  Write-Host "requirements.txt not found at $reqPath - run from project root." -ForegroundColor Red
}

# ---------- pa11y via npm ----------

Section "Installing pa11y via npm"
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
if (Have-Command npm) {
  npm install -g pa11y
} else {
  Write-Host "npm not on PATH yet. Open a NEW PowerShell window and run: npm install -g pa11y" -ForegroundColor Yellow
}

# ---------- Done ----------

Section "Done"
Write-Host ""
Write-Host "Open a NEW PowerShell window (so PATH refreshes), then verify with:"
Write-Host ""
Write-Host '   cd C:\Users\Justin\Desktop\LiCS-Pipeline'
Write-Host '   python -c "import preprocessors, validators, llm_cleanup, ocr, conversion; print(preprocessors.mammoth_available(), preprocessors.libreoffice_available(), conversion.weasyprint_available(), validators.verapdf_available(), validators.pa11y_available(), llm_cleanup.available(), ocr.available())"'
Write-Host ""
Write-Host "Seven Trues expected (claude needs ANTHROPIC_API_KEY set first)."
Write-Host ""
