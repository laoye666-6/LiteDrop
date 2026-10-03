@echo off
chcp 65001 >nul
cd /d %~dp0
echo ====== 打包 LiteDrop.exe ======
python -m PyInstaller --onefile --windowed --name LiteDrop --icon icon.ico --clean -y main.py
if errorlevel 1 (
  echo 打包失败,请检查上方错误信息
  pause
  exit /b 1
)
echo.
echo 完成: %~dp0dist\LiteDrop.exe
pause
