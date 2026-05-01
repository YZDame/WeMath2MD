# WeMath2MD

微信公众号文章转 Markdown 工具，主用法是 CLI。

它会先抓取文章里的图片，再调用 [MinerU](https://mineru.net) OCR API，把内容、公式和图片整理成一个可继续编辑的 Markdown 结果。

[![CI](https://github.com/yzdame/WeMath2MD/actions/workflows/ci.yml/badge.svg)](https://github.com/yzdame/WeMath2MD/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yzdame/WeMath2MD/branch/main/graph/badge.svg)](https://codecov.io/gh/yzdame/WeMath2MD)

## 运行要求

- Python 3.10+
- 一个可用的 `MINERU_API_TOKEN`

当前项目是 Python 实现，没有独立二进制发行版，所以运行时必须有 Python 环境。  
你不一定非要手动建虚拟环境，但机器上必须能运行 Python，并安装项目依赖。虚拟环境只是推荐做法，用来隔离依赖。

## 快速开始

```bash
git clone https://github.com/YOUR_USERNAME/WeMath2MD.git
cd WeMath2MD

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install . --no-build-isolation

cp .env.example .env
# 编辑 .env，填入 MINERU_API_TOKEN
```

安装完成后可以直接使用 `wemath2md`。

如果你是在开发这个项目，而不是单纯使用它，再考虑 editable 安装：

```bash
pip install -e . --no-build-isolation --config-settings editable_mode=compat
```

## CLI 用法

最常用的命令：

```bash
# 单篇文章
wemath2md "https://mp.weixin.qq.com/s/xxxxx"

# 指定输出目录
wemath2md "https://mp.weixin.qq.com/s/xxxxx" -o output

# 批量处理
wemath2md -f urls.txt

# 预检查 URL，不实际执行
wemath2md -f urls.txt --dry-run

# 详细日志
wemath2md "https://mp.weixin.qq.com/s/xxxxx" -v

# 静默模式
wemath2md "https://mp.weixin.qq.com/s/xxxxx" -q

# 不显示进度条
wemath2md "https://mp.weixin.qq.com/s/xxxxx" --no-progress

# 交互模式
wemath2md
```

也可以不安装 CLI，直接运行：

```bash
python main.py "https://mp.weixin.qq.com/s/xxxxx"
```

## CLI 参数

| 参数 | 说明 |
|------|------|
| `url` | 文章链接，可选 |
| `-o, --output` | 输出目录，默认 `output` |
| `-f, --file` | 从文件读取 URL，一行一个 |
| `-v, --verbose` | 输出 DEBUG 日志 |
| `-q, --quiet` | 仅输出错误 |
| `--no-progress` | 不显示进度条 |
| `--dry-run` | 只检查输入，不执行下载和 OCR |

## 输出结构

每次运行都会生成独立目录，避免同标题文章互相覆盖：

```text
output/
├── {article_title}__{run_id}/
│   ├── downloaded_images/
│   ├── converted/
│   │   ├── converted.md
│   │   └── images/
└── {article_title}__{run_id}.zip
```

## Web 备用入口

Web 现在是备用方式，不是主入口。

启动方式：

```bash
python web_app.py
```

默认访问 [http://localhost:8080](http://localhost:8080)。

Web 端保留这些能力：

- 提交转换任务
- 查询进度
- 下载 Markdown / ZIP
- 预览 Markdown

出于安全考虑，Web 默认只允许抓取 `mp.weixin.qq.com`。

## 环境变量

创建 `.env` 文件后可配置以下变量：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MINERU_API_TOKEN` | MinerU API Token，必填 | - |
| `WEB_SECRET_KEY` | Flask Secret Key | `dev-secret-key-change-in-production` |
| `WEB_CORS_ENABLED` | 是否启用 CORS | `true` |
| `WEB_CORS_ORIGINS` | 允许的 CORS 来源 | `*` |
| `WEB_DEBUG` | Web 调试模式 | `true` |
| `WEB_PORT` | Web 端口 | `8080` |
| `WEB_ALLOWED_ARTICLE_HOSTS` | Web 允许抓取的域名，逗号分隔 | `mp.weixin.qq.com` |
| `WEB_MAX_CONCURRENT_TASKS` | Web 后台最大并发任务数 | `2` |

更细的默认值可以看 [config.py](./config.py)。


## 项目结构（简版）

- `main.py`：CLI 主入口（批量处理、日志级别、进度显示）。
- `web_app.py`：Flask Web 备用入口（提交任务、查状态、下载结果）。
- `conversion_service.py`：下载 + OCR 的统一编排层（CLI/Web 复用）。
- `downloader.py`：微信公众号页面解析与图片下载。
- `mineru_converter.py`：调用 MinerU API 做 OCR 与 Markdown 产出。
- `config.py`：集中配置（默认值 + 环境变量覆盖 + 启动校验）。
- `wemath2md/cli.py`：安装后命令 `wemath2md` 的入口封装。
- `tests/`：pytest 测试。

## 结构改进建议（Roadmap）

1. **包结构统一（优先级高）**
   - 将根目录核心模块逐步迁入 `wemath2md/` 包，统一为包内绝对导入。
   - 目标是减少运行路径依赖，降低 `sys.path` 处理复杂度。

2. **结果类型显式化（优先级高）**
   - 为 `conversion_service` 返回值引入 `TypedDict` 或 `dataclass`（如 `ConversionResult`）。
   - 避免 CLI/Web 通过字符串 key 访问“松散 dict”导致的运行时错误。

3. **Web 任务状态持久化（优先级中）**
   - 当前任务状态在进程内内存中，服务重启后会丢失。
   - 可先用 SQLite，后续演进到 Redis + 队列（RQ/Celery）。

4. **配置职责拆分（优先级中）**
   - 将“配置定义 / 环境解析 / 校验逻辑”拆成独立模块，提升可维护性。

5. **测试分层（优先级中）**
   - 在现有模块测试基础上，逐步拆分 `unit / integration`，增强 Web 并发与失败场景覆盖。


## 桌面客户端安装包（Windows/macOS）

如果你希望像常规客户端一样安装使用（而不是手动运行 Python 命令），项目支持通过 `cx_Freeze` 打包：

- Windows：`python setup_desktop.py bdist_msi` 生成 `.msi`
- macOS：`python setup_desktop.py bdist_dmg` 生成 `.dmg`

详细步骤见 [desktop_packaging.txt](./desktop_packaging.txt)。

## 调试与开发

```bash
# 只执行第一阶段：下载图片
python downloader.py

# 只执行第二阶段：调用 MinerU OCR
python mineru_converter.py

# 运行测试
pytest

# 覆盖率
pytest --cov=. --cov-report=term-missing
```

## 注意事项

- 文章必须是公开可访问的。
- MinerU API 有速率和额度限制。
- 某些文章如果反爬严格，下载阶段可能失败。

## License

[MIT License](LICENSE)
