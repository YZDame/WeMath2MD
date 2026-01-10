#!/bin/bash
# WeMath2MD Heroku 部署脚本

set -e  # 遇到错误立即退出

echo "========================================="
echo "WeMath2MD Heroku 部署脚本"
echo "========================================="

# 检查 Heroku CLI 是否安装
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI 未安装"
    echo "请先安装 Heroku CLI: npm install -g heroku"
    exit 1
fi

# 检查是否已登录
if ! heroku auth:whoami &> /dev/null; then
    echo "❌ 未登录 Heroku"
    echo "请先登录: heroku login"
    exit 1
fi

# 读取应用名称
read -p "请输入 Heroku 应用名称 (留空则自动生成): " APP_NAME

if [ -z "$APP_NAME" ]; then
    APP_NAME="wemath2md-$(date +%s)"
    echo "将使用自动生成的名称: $APP_NAME"
fi

# 读取 MinerU API Token
read -p "请输入您的 MinerU API Token (从 mineru.net 获取): " MINERU_TOKEN

if [ -z "$MINERU_TOKEN" ]; then
    echo "❌ MinerU API Token 是必需的"
    exit 1
fi

# 生成随机的 Flask SECRET_KEY
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

echo ""
echo "========================================="
echo "部署配置信息"
echo "========================================="
echo "应用名称: $APP_NAME"
echo "MinerU Token: ${MINERU_TOKEN:0:20}..."
echo "Secret Key: ${SECRET_KEY:0:20}..."
echo ""

# 步骤 1: 创建 Heroku 应用
echo "步骤 1/5: 创建 Heroku 应用..."
if heroku create $APP_NAME 2>/dev/null; then
    echo "✅ 应用创建成功: $APP_NAME"
else
    echo "⚠️  应用可能已存在，尝试使用现有应用..."
    heroku apps:info $APP_NAME || exit 1
fi

# 步骤 2: 设置环境变量
echo "步骤 2/5: 配置环境变量..."
heroku config:set MINERU_API_TOKEN="$MINERU_TOKEN" --app $APP_NAME
heroku config:set WEB_SECRET_KEY="$SECRET_KEY" --app $APP_NAME
heroku config:set WEB_DEBUG="false" --app $APP_NAME
heroku config:set WEB_PORT="8080" --app $APP_NAME
echo "✅ 环境变量配置完成"

# 步骤 3: 验证 requirements.txt
echo "步骤 3/5: 验证依赖文件..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt 不存在"
    exit 1
fi
echo "✅ requirements.txt 存在"

# 步骤 4: 验证 Procfile
echo "步骤 4/5: 验证 Procfile..."
if [ ! -f "Procfile" ]; then
    echo "❌ Procfile 不存在"
    exit 1
fi
echo "✅ Procfile 存在"

# 步骤 5: 部署代码
echo "步骤 5/5: 部署代码到 Heroku..."
git add .
git commit -m "Deploy to Heroku: $APP_NAME" --allow-empty || echo "使用现有提交"
git push heroku main 2>&1 || {
    echo "⚠️  推送到 Heroku 失败，尝试设置远程仓库..."
    heroku git:remote -a $APP_NAME
    git push heroku main
}

echo ""
echo "========================================="
echo "✅ 部署完成！"
echo "========================================="
echo ""
echo "应用 URL: https://$APP_NAME.herokuapp.com"
echo ""
echo "查看日志:"
echo "  heroku logs --tail --app $APP_NAME"
echo ""
echo "重启应用:"
echo "  heroku restart --app $APP_NAME"
echo ""
echo "========================================="
