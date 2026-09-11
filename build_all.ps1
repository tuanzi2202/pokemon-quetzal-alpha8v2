# Build Quetzal 0.8.4 CN ROM end-to-end
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
Write-Host "[CN] dump (optional if already done)"
# python tools\dump_text.py
Write-Host "[CN] font patch"
& cmd /c "fontpatch\build.bat"
if ($LASTEXITCODE -ne 0) { throw "font patch failed" }
if (Test-Path work\free_cursor.txt) { Remove-Item work\free_cursor.txt }
Write-Host "[CN] apply locale"
python tools\apply_text.py locale\zh_CN\all_en_zh.jsonl
if ($LASTEXITCODE -ne 0) { throw "apply_text failed" }
Write-Host "[CN] force UI (all ptr-backed copies)"
python tools\force_ui_zh.py
if ($LASTEXITCODE -ne 0) { throw "force_ui failed" }
Write-Host "[CN] force mode wizard"
python tools\force_mode_zh.py
if ($LASTEXITCODE -ne 0) { throw "force_mode failed" }
Write-Host "[CN] force randomizer UI"
python tools\force_randomizer_zh.py
if ($LASTEXITCODE -ne 0) { throw "force_randomizer failed" }
Write-Host "[CN] force official names"
python tools\force_names_zh.py
if ($LASTEXITCODE -ne 0) { throw "force_names failed" }
Write-Host "[CN] force trainer class names (nameplate)"
python tools\force_trainer_class_zh.py
if ($LASTEXITCODE -ne 0) { throw "force_trainer_class failed" }
python tools\diff_guard.py
if ($LASTEXITCODE -ne 0) { throw "diff_guard failed" }
Copy-Item -Force work\cn_build.gba out\quetzal_084_cn.gba
Write-Host "[CN] OK out\quetzal_084_cn.gba"
