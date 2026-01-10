# WeMath2MD Desktop

微信公众号数学文章转 Markdown 工具

![Screenshot](assets/screenshot.png)

## 简介

跨平台桌面应用，将微信公众号文章（特别是数学公式）转换为 Markdown 格式。支持 Windows、macOS、Linux。

## 功能

- 跨平台支持（Windows/macOS/Linux）
- 本地运行，数据安全
- 实时进度显示
- 转换历史记录
- 自定义输出目录

## 系统要求

- Windows 10+ / macOS 10.15+ / Linux (Ubuntu 20.04+)
- Node.js 18+
- Python 3.8+

## 快速开始

### 下载安装

从 [Releases](https://github.com/yzdame/WeMath2MD/releases) 下载安装包。

**macOS 用户注意**：

应用未签名，安装时请：

1. 右键点击应用选择"打开"
2. 或在"系统设置 → 隐私与安全性"中点击"仍要打开"

详见 [macOS安装说明.md](macOS安装说明.md)

### 从源码构建

```bash
# 克隆仓库
git clone https://github.com/yzdame/WeMath2MD.git
cd WeMath2MD/desktop-app

# 安装依赖
npm install

# 构建应用（选择对应平台的脚本）
./build-mac.sh      # macOS
./build-win.sh      # Windows (Git Bash)
./build-linux.sh    # Linux
```

构建产物位于 `dist/` 目录。

### 开发模式

```bash
# 终端 1：启动 Python 后端
cd /path/to/WeMath2MD
python desktop_backend.py

# 终端 2：启动 Electron
cd desktop-app
npm start
```

## 使用说明

1. 获取 MinerU API Token：访问 [MinerU 官网](https://mineru.net) 注册并获取
2. 粘贴微信公众号文章链接
3. 输入 API Token
4. 点击"开始转换"
5. 完成后点击"打开文件夹"查看结果

## 输出结构

```
output/{文章标题}/
├── downloaded_images/     # 原始图片
├── converted/
│   ├── converted.md       # Markdown 文件
│   └── images/            # 提取的图片
└── {文章标题}.zip         # 打包文件
```

## 项目结构

```
desktop-app/
├── src/
│   ├── main/              # Electron 主进程
│   └── renderer/          # 渲染进程（前端）
├── package.json
└── build-*.sh             # 构建脚本
```

## 常见问题

**Q: 转换失败？**

- 检查网络连接
- 确认 API Token 有效
- 确认文章可公开访问

**Q: 支持哪些格式？**

- JPG、PNG、WEBP

**Q: 能转换付费文章吗？**

- 不能，仅支持公开文章

## 许可证

MIT License
