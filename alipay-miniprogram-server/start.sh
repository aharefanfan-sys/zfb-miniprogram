#!/bin/bash

# 支付宝小程序后端服务启动脚本

cd "$(dirname "$0")"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Using default configuration."
    echo "Please copy .env.example to .env and configure your settings."
fi

# 安装/更新依赖
echo "Installing dependencies..."
pip install -q -r requirements.txt

# 启动服务
echo "Starting server..."
export FLASK_ENV=${FLASK_ENV:-development}
export PORT=${PORT:-5001}

echo "Environment: $FLASK_ENV"
echo "Port: $PORT"

if [ "$FLASK_ENV" = "production" ]; then
    # 生产环境使用Gunicorn
    exec gunicorn -w 4 -b 0.0.0.0:$PORT "app:create_app()"
else
    # 开发环境直接运行
    exec python app.py
fi
