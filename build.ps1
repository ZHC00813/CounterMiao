param([switch]$Installer, [string]$IsccPath="ISCC.exe")
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {throw 'Dependency install failed'}
python -m PyInstaller --noconfirm --windowed --onedir --name CounterMiao --version-file "$PSScriptRoot\windows_version_info.txt" --icon "$PSScriptRoot\CounterMiao.ico" --collect-all tkinterdnd2 --exclude-module pymupdf.layout --exclude-module onnxruntime --exclude-module numpy --exclude-module networkx --add-data "$PSScriptRoot\template.docx;." --add-data "$PSScriptRoot\ocr.ps1;." --add-data "$PSScriptRoot\CounterMiao.ico;." --add-data "$PSScriptRoot\CounterMiao.png;." "$PSScriptRoot\app.py"
if ($LASTEXITCODE -ne 0) {throw 'Build failed'}
python -m PyInstaller --noconfirm --onefile --console --name CounterMiaoMCP --version-file "$PSScriptRoot\windows_version_info.txt" --icon "$PSScriptRoot\CounterMiao.ico" --distpath "$PSScriptRoot\dist\CounterMiao" "$PSScriptRoot\mcp_adapter.py"
if ($LASTEXITCODE -ne 0) {throw 'MCP build failed'}

$runtimeDir=Join-Path $PSScriptRoot 'dist\CounterMiao'
foreach($doc in @('README.md','VERSION_GUIDE.md','CHANGELOG.md','TESTING.md','VISUAL_QA.md','AI_INTERFACE.md','THIRD_PARTY_NOTICES.md','自动化测试报告.json')) {
  if(Test-Path -LiteralPath (Join-Path $PSScriptRoot $doc)) {Copy-Item -LiteralPath (Join-Path $PSScriptRoot $doc) -Destination $runtimeDir -Force}
}
if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'THIRD_PARTY_LICENSES')) {
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'THIRD_PARTY_LICENSES') -Destination $runtimeDir -Recurse -Force
} elseif(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'THIRD_PARTY_LICENSES.md')) {
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'THIRD_PARTY_LICENSES.md') -Destination $runtimeDir -Force
}

if ($Installer) {
  & $IsccPath "/DAppSourceDir=$PSScriptRoot\dist\CounterMiao" "/DInstallerOutputDir=$PSScriptRoot\installer-output" "$PSScriptRoot\installer.iss"
  if ($LASTEXITCODE -ne 0) {throw "Installer build failed"}
}
