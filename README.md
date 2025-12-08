# WeMath2MD

微信公众号数学文章转 Markdown 工具 📐→📝

将微信公众号中的数学讲义/文章图片批量下载，通过 [MinerU](https://mineru.net) OCR API 识别，自动合并为一个完整的 Markdown 文件。

## ✨ 功能特点

- 🔗 自动提取公众号文章标题
- 🖼️ 批量下载文章中的所有图片
- 🔍 调用 MinerU API 进行 OCR 识别（支持数学公式）
- 📄 自动合并多张图片的识别结果为一个 Markdown 文件
- 📦 自动打包输出结果为 ZIP 文件

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

### 4. 配置 API Token

1. 前往 [MinerU](https://mineru.net) 注册并获取 API Token
2. 复制 `.env.example` 为 `.env`
3. 填入你的 API Token

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 Token
```

### 5. 运行

```bash
python main.py
```

## 📖 使用方法

### 方式一：一站式处理（推荐）

编辑 `main.py` 中的 URL 和 Token，然后运行：

```python
result = process_wechat_article(
    url="https://mp.weixin.qq.com/s/xxxxx",
    api_token="your_api_token",
    output_dir="output"
)
```

### 方式二：分步执行

```bash
# 第一步：下载图片
python downloader.py

# 第二步：OCR 识别转换
python mineru_converter.py
```

## 🛠️ 项目结构

| 文件 | 说明 |
|------|------|
| `main.py` | 主程序，整合下载+转换流程 |
| `downloader.py` | 下载公众号图片，提取文章标题 |
| `mineru_converter.py` | 调用 MinerU API 识别并合并结果 |

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 |
|--------|------|
| `MINERU_API_TOKEN` | MinerU API Token |

### MinerU API 参数

在 `mineru_converter.py` 中可调整：

```python
data = {
    "enable_formula": True,    # 启用公式识别
    "enable_table": True,      # 启用表格识别
    "layout_model": "doclayout_yolo",  # 布局模型
    "language": "ch"           # 语言：中文
}
```

## 📝 注意事项

- MinerU API 有调用频率限制，请合理使用
- 公众号文章需要能够公开访问
- 部分反爬严格的文章可能无法下载

## 📄 License

[MIT License](LICENSE)

## 🙏 致谢

- [MinerU](https://mineru.net) - 提供强大的文档 OCR 能力
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML 解析
