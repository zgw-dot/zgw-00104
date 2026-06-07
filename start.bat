@echo off
chcp 65001 >nul
echo ========================================
echo 实验室样本流转工作台 - 启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未检测到 Python，请先安装 Python 3.7+
    pause
    exit /b 1
)
echo [OK] Python 环境正常
echo.

echo [2/3] 安装依赖...
cd backend
pip install -r requirements.txt
echo [OK] 依赖安装完成
echo.

echo [3/3] 初始化数据库（首次运行）...
if not exist "..\data\samples.db" (
    python init_db.py
) else (
    echo [SKIP] 数据库已存在，跳过初始化
    echo        如需重新初始化，请删除 data\samples.db 后重启
)
echo.

echo ========================================
echo 启动后端服务...
echo 服务地址: http://localhost:5000
echo 前端页面: 请用浏览器打开 frontend\index.html
echo ========================================
echo.

python app.py

pause
