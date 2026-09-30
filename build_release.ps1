<#
.SYNOPSIS
Builds the epub2cbz executable, packages it into a release ZIP, and generates a SHA256 checksum.
#>

$ErrorActionPreference = "Stop"

# 1. バージョン情報の定義
$Version = "v2.3.0"
$ZipName = "epub2cbz-$Version-windows-x64.zip"
$ChecksumName = "$ZipName.sha256"

Write-Host "Starting build process for epub2cbz $Version..." -ForegroundColor Cyan

# 2. PyInstaller のインストール確認と実行
if (!(Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

Write-Host "Building executable with PyInstaller..." -ForegroundColor Yellow
pyinstaller --noconfirm --onefile --console epub2cbz.py

# 3. 配布用フォルダの準備
$DistDir = "dist\epub2cbz-release"
Write-Host "Preparing release folder at $DistDir..." -ForegroundColor Yellow

if (Test-Path $DistDir) {
    Remove-Item -Recurse -Force $DistDir
}
New-Item -ItemType Directory -Path $DistDir | Out-Null

# 必要なファイルをリリース用フォルダにコピー
Copy-Item "dist\epub2cbz.exe" -Destination $DistDir\
Copy-Item "epub2cbz.i18n" -Destination $DistDir\
Copy-Item "README.md" -Destination $DistDir\

# 4. ZIP アーカイブの作成
Write-Host "Creating release archive $ZipName..." -ForegroundColor Yellow
if (Test-Path "dist\$ZipName") {
    Remove-Item -Force "dist\$ZipName"
}
Compress-Archive -Path "$DistDir\*" -DestinationPath "dist\$ZipName"

# 5. SHA256 ハッシュの計算とファイル出力
Write-Host "Calculating SHA256 checksum..." -ForegroundColor Yellow
$HashString = (Get-FileHash -Algorithm SHA256 "dist\$ZipName").Hash.ToLower()
$HashContent = "$HashString *$ZipName"
Set-Content -Path "dist\$ChecksumName" -Value $HashContent -Encoding UTF8
Write-Host "SHA256: $HashString" -ForegroundColor Cyan

# 6. お掃除 (中間フォルダの削除)
Remove-Item -Recurse -Force $DistDir

Write-Host "Build and packaging completed successfully!" -ForegroundColor Green
Write-Host "Release assets are ready at:" -ForegroundColor Green
Write-Host "  - dist\$ZipName"
Write-Host "  - dist\$ChecksumName"
