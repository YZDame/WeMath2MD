# web_app.py
"""
WeMath2MD Web 界面
简洁现代的前端，提供链接输入和结果下载
"""

import os
import sys
import uuid
import threading
from enum import Enum
from typing import Any
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
from dotenv import load_dotenv
from logger import setup_logger, get_logger
from config import web as cfg, get_mineru_token

from downloader import WechatImageDownloader
from mineru_converter import MinerUConverter


class TaskState(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"

# 加载环境变量
load_dotenv()

# 初始化日志
logger = get_logger("wemath2md.web")

app = Flask(__name__)

# 安全配置：设置 SECRET_KEY
app.config['SECRET_KEY'] = cfg.secret_key
app.config['OUTPUT_DIR'] = cfg.output_dir
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 生产环境额外配置
if not cfg.debug:
    # 生产环境安全设置
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 年缓存
    logger.info("生产环境模式：启用安全配置")

# 配置 CORS
if cfg.cors_enabled:
    CORS(app, origins=cfg.cors_origins)
    logger.info(f"CORS 已启用，允许来源: {cfg.cors_origins}")
else:
    logger.info("CORS 已禁用")

# 存储转换历史
conversion_history: list[dict[str, Any]] = []

# 存储任务状态 {task_id: {state, progress, result, error}}
tasks: dict[str, dict[str, Any]] = {}

# 安全的文件访问基础目录
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / app.config['OUTPUT_DIR']


def validate_path(filepath: str | Path) -> Path | None:
    """
    验证路径是否在允许的目录内，防止路径遍历攻击

    Args:
        filepath: 用户提供的文件路径

    Returns:
        解析后的安全路径，如果不安全则返回 None
    """
    try:
        # 解析为绝对路径，消除 .. 和符号链接
        resolved_path = (BASE_DIR / filepath).resolve()

        # 验证路径是否在 output 目录内
        if resolved_path.is_relative_to(OUTPUT_DIR):
            return resolved_path

        logger.warning(f"路径遍历尝试: {filepath} -> {resolved_path}")
        return None
    except Exception as e:
        logger.error(f"路径验证失败: {e}")
        return None


def run_conversion_task(task_id: str, url: str, api_token: str) -> None:
    """
    后台执行转换任务

    Args:
        task_id: 任务 ID
        url: 文章链接
        api_token: MinerU API Token
    """
    try:
        # 更新状态：开始处理
        tasks[task_id]['state'] = TaskState.PROCESSING
        tasks[task_id]['progress'] = '下载图片中...'
        tasks[task_id]['progress_percent'] = 10

        # 第一阶段：下载图片
        downloader = WechatImageDownloader(output_dir=app.config['OUTPUT_DIR'])
        download_result = downloader.download_from_url(url)

        if not download_result:
            tasks[task_id]['state'] = TaskState.FAILED
            tasks[task_id]['error'] = '下载文章图片失败'
            tasks[task_id]['progress_percent'] = 0
            return

        # 更新进度
        tasks[task_id]['progress'] = 'OCR 转换中...'
        tasks[task_id]['progress_percent'] = 50

        # 第二阶段：OCR 转换
        converter = MinerUConverter(api_token=api_token)
        convert_result = converter.convert_images(
            image_dir=download_result['images_dir'],
            output_dir=download_result['result_dir'],
            output_name="converted"
        )

        if not convert_result:
            tasks[task_id]['state'] = TaskState.FAILED
            tasks[task_id]['error'] = 'OCR 转换失败'
            tasks[task_id]['progress_percent'] = 0
            return

        # 保存结果
        result = {
            'title': download_result['title'],
            'md_file': convert_result['md_file'],
            'zip_file': convert_result['zip_file'],
            'image_count': convert_result['image_count'],
            'result_dir': download_result['result_dir']
        }

        # 添加到历史记录
        conversion_history.insert(0, result)
        if len(conversion_history) > cfg.max_history_items:
            conversion_history.pop()

        # 更新状态：完成
        tasks[task_id]['state'] = TaskState.DONE
        tasks[task_id]['progress'] = '完成'
        tasks[task_id]['progress_percent'] = 100
        tasks[task_id]['result'] = result
        logger.info(f"任务 {task_id} 转换成功: {result['title']}")

    except Exception as e:
        logger.error(f"任务 {task_id} 转换失败: {e}")
        tasks[task_id]['state'] = TaskState.FAILED
        tasks[task_id]['error'] = str(e)


@app.route('/')
def index() -> str:
    """首页"""
    return render_template('index.html', history=conversion_history)


@app.route('/convert', methods=['POST'])
def convert() -> Response:
    """处理转换请求 - 异步模式，支持用户传入 API Token"""
    data = request.get_json()
    url = data.get('url', '').strip()
    user_api_token = data.get('api_token', '').strip()  # 用户传入的 Token

    logger.info(f"收到转换请求: {url}")

    if not url:
        return jsonify({'success': False, 'error': '请输入文章链接'})

    if not url.startswith('http'):
        return jsonify({'success': False, 'error': '无效的链接格式'})

    # 优先使用用户传入的 Token，如果没有则使用服务器配置的 Token
    api_token = user_api_token or get_mineru_token()
    if not api_token:
        return jsonify({'success': False, 'error': '请提供 MinerU API Token'})

    # 生成任务 ID
    task_id = str(uuid.uuid4())

    # 初始化任务状态
    tasks[task_id] = {
        'state': TaskState.PENDING,
        'progress': '等待开始...',
        'result': None,
        'error': None
    }

    # 启动后台线程执行转换
    thread = threading.Thread(
        target=run_conversion_task,
        args=(task_id, url, api_token),
        daemon=True
    )
    thread.start()

    logger.info(f"任务 {task_id} 已提交，后台处理中...")
    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': '任务已提交，正在后台处理'
    })


@app.route('/status/<task_id>')
def task_status(task_id: str) -> Response:
    """查询任务状态"""
    if task_id not in tasks:
        return jsonify({'success': False, 'error': '任务不存在'})

    task = tasks[task_id]
    response = {
        'success': True,
        'state': task['state'].value,
        'progress': task['progress'],
        'progress_percent': task.get('progress_percent', 0)
    }

    if task['state'] == TaskState.DONE:
        response['result'] = task['result']
    elif task['state'] == TaskState.FAILED:
        response['error'] = task['error']

    return jsonify(response)


@app.route('/download/md/<path:filepath>')
def download_md(filepath: str) -> Response | tuple[str, int]:
    """下载/预览 Markdown 文件"""
    safe_path = validate_path(filepath)
    if safe_path and safe_path.exists():
        logger.info(f"下载 Markdown: {filepath}")
        return send_file(safe_path, mimetype='text/markdown')
    logger.warning(f"文件不存在或路径无效: {filepath}")
    return "文件不存在", 404


@app.route('/download/zip/<path:filepath>')
def download_zip(filepath: str) -> Response | tuple[str, int]:
    """下载 ZIP 文件"""
    safe_path = validate_path(filepath)
    if safe_path and safe_path.exists():
        logger.info(f"下载 ZIP: {filepath}")
        return send_file(safe_path, as_attachment=True)
    logger.warning(f"文件不存在或路径无效: {filepath}")
    return "文件不存在", 404


@app.route('/preview/<path:filepath>')
def preview_md(filepath: str) -> Response:
    """预览 Markdown 内容"""
    safe_path = validate_path(filepath)
    if safe_path and safe_path.exists():
        content = safe_path.read_text(encoding='utf-8')
        logger.debug(f"预览 Markdown: {filepath}")
        return jsonify({'success': True, 'content': content})
    logger.warning(f"文件不存在或路径无效: {filepath}")
    return jsonify({'success': False, 'error': '文件不存在'})


if __name__ == '__main__':
    # 确保模板目录存在
    os.makedirs('templates', exist_ok=True)

    # 初始化日志系统
    from config import logging as log_cfg
    setup_logger(level=log_cfg.level, log_file="web_app.log")

    logger.info("WeMath2MD Web 服务启动中...")

    # Heroku 会设置 PORT 环境变量
    port = int(os.environ.get('PORT', cfg.port))
    logger.info(f"访问 http://{cfg.host}:{port}")

    app.run(debug=cfg.debug, host=cfg.host, port=port)
