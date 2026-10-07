$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$pluginSource = Join-Path $PSScriptRoot "bundled_plugins\voiceStreaks"
$pluginArchive = Join-Path $PSScriptRoot "bundled_plugins\voiceStreaks.zip"
if (Test-Path $pluginSource) {
    Remove-Item -LiteralPath $pluginArchive -Force -ErrorAction SilentlyContinue
    Compress-Archive -Path (Join-Path $pluginSource "*") -DestinationPath $pluginArchive -Force
} elseif (-not (Test-Path $pluginArchive)) {
    throw "Missing bundled VoiceStreaks source and archive."
}
python -m pip install --upgrade -r requirements-build.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name VencordModManager-1.5 --add-data "bundled_plugins\voiceStreaks.zip;bundled_plugins" mod_manager.py
Write-Host "Built: $PSScriptRoot\dist\VencordModManager-1.5.exe"
