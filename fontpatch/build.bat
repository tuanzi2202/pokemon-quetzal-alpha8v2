@echo off
setlocal
cd /d "%~dp0"
set ARMIPS=%~dp0..\vendor\armips.exe
if not exist "%ARMIPS%" set ARMIPS=%~dp0..\vendor\Pokemon_GBA_Font_Patch-main\pokeE\tools\armips\armips.exe
set GOLDEN=%~dp0..\golden\en_0.8.4.gba
set OUT=%~dp0..\work\cn_build.gba
copy /Y "%GOLDEN%" "%OUT%" >nul
"%ARMIPS%" main_quetzal.asm -strequ Origin_Rom "%OUT%" -erroronwarning -sym quetzal_chs.sym
if errorlevel 1 (
  echo FONT PATCH FAILED
  exit /b 1
)
echo FONT PATCH OK
endlocal
