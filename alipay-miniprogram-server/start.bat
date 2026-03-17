@echo off
chcp 65001 >nul

:: 支付宝小程序后端服务启动脚本（Windows）

cd /d "%~dp0"

:: 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

:: 检查环境变量
if not exist ".env" (
    echo Warning: .env file not found. Using default configuration.
    echo Please copy .env.example to .env and configure your settings.
)

:: 安装/更新依赖
echo Installing dependencies...
pip install -q -r requirements.txt

:: 启动服务
echo Starting server...
if "%FLASK_ENV%"=="" set FLASK_ENV=development
if "%PORT%"=="" set PORT=5001

echo Environment: %FLASK_ENV%
echo Port: %PORT%

:: 开发环境直接运行
python app.py

pause
