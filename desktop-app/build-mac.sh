#!/bin/bash
# macOS 构建脚本

set -e

echo "========================================"
echo "WeMath2MD Desktop - macOS 构建脚本"
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

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python 3"
    exit 1
fi

echo "Python 版本: $(python3 --version)"

# 安装依赖
echo ""
echo "正在安装依赖..."
npm install

# 创建 Python 打包目录
echo ""
echo "正在准备 Python 环境..."
rm -rf python
mkdir -p python

# 复制 Python 文件
echo "复制 Python 文件..."
cp ../desktop_backend.py python/
cp ../config.py python/
cp ../downloader.py python/
cp ../mineru_converter.py python/
cp ../logger.py python/
cp ../temp_manager.py python/
cp ../main.py python/

# 复制 .env.example 作为 .env 默认配置（如果不存在）
if [ ! -f ../.env ]; then
    if [ -f ../.env.example ]; then
        cp ../.env.example python/.env
        echo "注意: 已复制 .env.example 作为默认配置"
    fi
else
    cp ../.env python/
fi

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

# 创建 README 说明用户需要安装依赖
cat > python/README.txt << 'EOF'
WeMath2MD Desktop - Python 依赖说明
=====================================

此应用需要系统安装 Python 3 和以下依赖包。

请在终端运行以下命令安装依赖：

pip3 install -r requirements.txt

或者使用 pip:

pip install flask flask-cors requests beautifulsoup4 python-dotenv tenacity tqdm openai

安装完成后，重新启动应用程序即可。
EOF

echo "Python 文件准备完成"

# 构建 macOS 应用（使用 --dir 跳过 DMG 创建和签名）
echo ""
echo "正在构建 macOS 应用..."
npx electron-builder --mac --dir || {
  echo "注意: electron-builder 构建可能因签名失败，但应用已创建"
}

# 使用 ditto 复制应用以移除所有元数据（macOS 26 兼容性）
echo ""
echo "使用 ditto 移除元数据..."
APP_PATH="dist/mac-arm64/WeMath2MD.app"
CLEAN_PATH="dist/clean/WeMath2MD.app"

if [ -d "$APP_PATH" ]; then
  rm -rf dist/clean
  mkdir -p dist/clean

  # 使用 ditto 复制时不包含资源分支和扩展属性
  ditto --norsrc --noextattr --noqtn "$APP_PATH" "$CLEAN_PATH"

  # 手动签名清理后的应用
  echo "手动签名应用..."
  codesign --force --deep --sign - "$CLEAN_PATH"

  # 验证签名
  echo ""
  echo "验证签名..."
  codesign -vvv "$CLEAN_PATH" | head -5

  # 替换原应用
  rm -rf "$APP_PATH"
  mv "$CLEAN_PATH" "$APP_PATH"

  echo "签名完成: $APP_PATH"
else
  echo "错误: 应用未找到: $APP_PATH"
  exit 1
fi

echo ""
echo "========================================"
echo "构建完成！"
echo "应用位置: $APP_PATH"
echo "========================================"
