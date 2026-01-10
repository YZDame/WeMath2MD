# WeMath2MD

微信公众号数学文章转 Markdown 工具 📐→📝

[![CI](https://github.com/yzdame/WeMath2MD/actions/workflows/ci.yml/badge.svg)](https://github.com/yzdame/WeMath2MD/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yzdame/WeMath2MD/branch/main/graph/badge.svg)](https://codecov.io/gh/yzdame/WeMath2MD)

将微信公众号中的数学讲义/文章图片批量下载，通过 [MinerU](https://mineru.net) OCR API 识别，自动合并为一个完整的 Markdown 文件。

## ✨ 功能特点

- 🔗 自动提取公众号文章标题
- 🖼️ 批量下载文章中的所有图片
- 🔍 调用 MinerU API 进行 OCR 识别（支持数学公式）
- 📄 自动合并多张图片的识别结果为一个 Markdown 文件
- 📦 自动打包输出结果为 ZIP 文件
- 🌐 **提供简洁现代的 Web 界面**
- ⚡ **支持批量处理多个文章**
- 🎛️ **灵活的 CLI 选项（verbose/quiet/dry-run）**

## 📁 输出目录结构

```
output/
└── {文章标题}/
    ├── downloaded_images/     ← 原始下载的图片
    │   ├── 001.jpg
    │   ├── 002.png
    │   └── ...
    ├── converted/             ← MinerU 转换结果
    │   ├── converted.md       ← 合并后的 Markdown
    │   └── images/            ← 识别结果中的图片
    │       └── ...
    └── {文章标题}.zip          ← 打包的完整结果
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/WeMath2MD.git
cd WeMath2MD
```

### 2. 创建虚拟环境

**支持 Python 3.10+**

```bash
# 使用 conda
conda create -p .conda python=3.11
conda activate ./.conda

# 或使用 venv
python -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 安装命令行工具（可选）

```bash
pip install -e .
```

安装后可以直接使用 `wemath2md` 命令。

### 5. 配置 API Token

1. 前往 [MinerU](https://mineru.net) 注册并获取 API Token
2. 复制 `.env.example` 为 `.env`
3. 填入你的 API Token

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 Token
```

### 6. 运行

```bash
# 方式一：命令行参数
wemath2md https://mp.weixin.qq.com/s/xxxxx

# 方式二：交互式（直接运行后输入链接）
wemath2md

# 方式三：使用 Python 运行
python main.py https://mp.weixin.qq.com/s/xxxxx
```

## 📖 使用方法

### 方式一：Web 界面（最简单）

```bash
python web_app.py
```

然后打开浏览器访问 <http://localhost:8080>，粘贴链接即可。

**Web 界面特性**：
- 异步处理，长时间任务不会超时
- 实时进度显示（10% → 50% → 100%）
- 支持 Markdown 预览和下载

![Web界面](https://pauline.oss-cn-shenzhen.aliyuncs.com/img/screencapture-localhost-8080-2026-01-10-22_20_00.png)

### 方式二：命令行

```bash
# 基本用法
wemath2md https://mp.weixin.qq.com/s/xxxxx

# 指定输出目录
wemath2md https://mp.weixin.qq.com/s/xxxxx -o my_output

# 详细输出模式（显示 DEBUG 日志）
wemath2md https://mp.weixin.qq.com/s/xxxxx -v

# 静默模式（只输出错误）
wemath2md https://mp.weixin.qq.com/s/xxxxx -q

# 批量处理（从文件读取 URL，每行一个）
wemath2md -f urls.txt

# 预览模式（验证 URL，不实际处理）
wemath2md -f urls.txt --dry-run

# 不显示进度条
wemath2md https://mp.weixin.qq.com/s/xxxxx --no-progress

# 交互模式（不传链接，运行后提示输入）
wemath2md
```

**命令行参数说明**：

| 参数 | 说明 |
|------|------|
| `url` | 文章链接（可选） |
| `-o, --output` | 输出目录（默认: output） |
| `-v, --verbose` | 详细输出模式（DEBUG 级别） |
| `-q, --quiet` | 静默模式（只输出错误） |
| `-f, --file` | 从文件读取 URL 批量处理 |
| `--no-progress` | 不显示进度条 |
| `--dry-run` | 预览模式（只验证 URL） |

### 方式三：分步执行

```bash
# 第一步：下载图片
python downloader.py

# 第二步：OCR 识别转换
python mineru_converter.py
```

## 🛠️ 项目结构

| 文件/目录 | 说明 |
|-----------|------|
| `web_app.py` | Web 界面服务（异步处理 + 进度跟踪） |
| `main.py` | 命令行主程序（支持批量处理） |
| `downloader.py` | 下载公众号图片，提取文章标题（并发下载） |
| `mineru_converter.py` | 调用 MinerU API 识别并合并结果（并发上传） |
| `config.py` | 统一配置管理（支持环境变量） |
| `logger.py` | 日志系统配置 |
| `temp_manager.py` | 临时目录管理（自动清理） |
| `tests/` | 自动化测试目录 |
| `.github/workflows/` | CI/CD 配置 |

## ⚙️ 配置说明

### 环境变量

创建 `.env` 文件（可从 `.env.example` 复制）并配置以下变量：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MINERU_API_TOKEN` | MinerU API Token（必填） | - |
| `LOG_LEVEL` | 日志级别 | INFO |
| `WEB_SECRET_KEY` | Web Flask 密钥 | dev-secret-key |
| `WEB_CORS_ENABLED` | 是否启用 CORS | true |
| `WEB_CORS_ORIGINS` | 允许的 CORS 来源 | * |
| `WEB_DEBUG` | Web 调试模式 | false |
| `WEB_HOST` | Web 监听地址 | 127.0.0.1 |
| `WEB_PORT` | Web 监听端口 | 8080 |

### 配置文件

所有配置都支持通过环境变量覆盖，无需修改代码。详见 `config.py`。

## 📝 注意事项

- MinerU API 有调用频率限制，请合理使用
- 公众号文章需要能够公开访问
- 部分反爬严格的文章可能无法下载

## 🤝 贡献指南

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与开发。

### 开发者相关

```bash
# 运行测试
pytest

# 运行测试并查看覆盖率
pytest --cov=. --cov-report=term-missing

# 安装 pre-commit hooks（推荐）
pip install pre-commit
pre-commit install
```

## 📄 License

[MIT License](LICENSE)

## 🙏 致谢

- [MinerU](https://mineru.net) - 提供强大的文档 OCR 能力（本项目通过 API 调用其服务，不包含 MinerU 源代码）
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML 解析
