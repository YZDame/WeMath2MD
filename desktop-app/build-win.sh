#!/bin/bash
# Windows 构建脚本 (在 Git Bash 或 WSL 中运行)

set -e

echo "========================================"
echo "WeMath2MD Desktop - Windows 构建脚本"
echo "========================================"

# 进入桌面应用目录
cd "$(dirname "$0")"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "错误: 未找到 Node.js，请先安装 Node.js"
    exit 1
fi

echo "Node.js 版本: $(node --version)"
echo "npm 版本: $(npm --version)"

# 安装依赖
echo ""
echo "正在安装依赖..."
npm install

# 创建 Python 打包目录
echo ""
echo "正在准备 Python 环境..."
mkdir -p python

# 复制 Python 文件
cp ../desktop_backend.py python/
cp ../config.py python/
cp ../downloader.py python/
cp ../mineru_converter.py python/
cp ../logger.py python/
cp ../temp_manager.py python/

# 创建 requirements.txt
cat > python/requirements.txt << 'EOF'
flask>=2.0.0
flask-cors>=4.0.0
requests>=2.28.0
beautifulsoup4>=4.11.0
python-dotenv>=1.0.0
tenacity>=8.2.0
tqdm>=4.64.0
openai>=1.0.0
EOF

# 创建 Python 启动脚本
cat > python/start.py << 'EOF'
#!/usr/bin/env python3
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入并运行
import desktop_backend
desktop_backend.main()
EOF

# 构建 Windows 安装包
echo ""
echo "正在构建 Windows 安装包..."
npm run build:win

echo ""
echo "========================================"
echo "构建完成！"
echo "安装包位置: dist/"
echo "========================================"
