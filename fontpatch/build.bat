@echo off
setlocal
cd /d "%~dp0"
rem The top-level 2020 armips cannot parse the .ifndef syntax used here.
rem Prefer the bundled 2023 build that matches the upstream font patch.
set ARMIPS=%~dp0..\vendor\Pokemon_GBA_Font_Patch-main\pokeE\tools\armips\armips.exe
if not exist "%ARMIPS%" set ARMIPS=%~dp0..\vendor\armips.exe
set GOLDEN=%~dp0..\golden\en_0.8.4.gba
set OUT=%~dp0..\work\cn_build.gba
set FLAT=%~dp0main_quetzal.generated.asm
copy /Y "%GOLDEN%" "%OUT%" >nul
python "%~dp0..\tools\prepare_armips_source.py" "%~dp0main_quetzal.asm" "%FLAT%"
if errorlevel 1 (
  echo FONT SOURCE PREP FAILED
  exit /b 1
)
"%ARMIPS%" "%FLAT%" -strequ Origin_Rom "%OUT%" -erroronwarning -sym quetzal_chs.sym
if errorlevel 1 (
  echo FONT PATCH FAILED
  exit /b 1
)
echo FONT PATCH OK
endlocal
