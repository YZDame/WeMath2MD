#!/usr/bin/env python3
"""
WeMath2MD Desktop Backend
桌面应用专用的后端服务
"""

import os
import sys
import uuid
import threading
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logger import setup_logger, get_logger
from config import web as cfg
from downloader import WechatImageDownloader
from mineru_converter import MinerUConverter

# 加载环境变量
load_dotenv()

# 初始化日志
logger = get_logger("wemath2md.desktop")

app = Flask(__name__)

# 配置
app.config['SECRET_KEY'] = 'desktop-secret-key'
app.config['OUTPUT_DIR'] = 'output'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 启用 CORS
CORS(app, origins=['http://localhost:*', 'http://127.0.0.1:*'])

# 存储任务状态
tasks = {}
# 存储转换历史
conversion_history = []

# 基础目录
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / app.config['OUTPUT_DIR']


class TaskState:
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


def validate_path(filepath):
    """验证路径是否安全"""
    try:
        resolved_path = (BASE_DIR / filepath).resolve()
        if resolved_path.is_relative_to(OUTPUT_DIR):
            return resolved_path
        return None
    except Exception:
        return None


def run_conversion_task(task_id, url, api_token, output_dir=None):
    """后台执行转换任务"""
    try:
        tasks[task_id]['state'] = TaskState.PROCESSING
        tasks[task_id]['progress'] = '下载图片中...'
        tasks[task_id]['progress_percent'] = 10

        # 设置输出目录
        work_dir = output_dir or str(OUTPUT_DIR)

        # 第一阶段：下载图片
        downloader = WechatImageDownloader(output_dir=work_dir)
        download_result = downloader.download_from_url(url)

        if not download_result:
            tasks[task_id]['state'] = TaskState.FAILED
            tasks[task_id]['error'] = '下载文章图片失败'
            tasks[task_id]['progress_percent'] = 0
            return

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
        if len(conversion_history) > 20:
            conversion_history.pop()

        tasks[task_id]['state'] = TaskState.DONE
        tasks[task_id]['progress'] = '完成'
        tasks[task_id]['progress_percent'] = 100
        tasks[task_id]['result'] = result
        logger.info(f"任务 {task_id} 转换成功: {result['title']}")

    except Exception as e:
        logger.error(f"任务 {task_id} 转换失败: {e}")
        tasks[task_id]['state'] = TaskState.FAILED
        tasks[task_id]['error'] = str(e)


@app.route('/convert', methods=['POST'])
def convert():
    """处理转换请求"""
    data = request.get_json()
    url = data.get('url', '').strip()
    user_api_token = data.get('api_token', '').strip()
    output_dir = data.get('output_dir', '').strip()

    logger.info(f"收到转换请求: {url}")

    if not url:
        return jsonify({'success': False, 'error': '请输入文章链接'})

    if not url.startswith('http'):
        return jsonify({'success': False, 'error': '无效的链接格式'})

    api_token = user_api_token or os.getenv('MINERU_API_TOKEN', '')
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
        args=(task_id, url, api_token, output_dir if output_dir else None),
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
def task_status(task_id):
    """查询任务状态"""
    if task_id not in tasks:
        return jsonify({'success': False, 'error': '任务不存在'})

    task = tasks[task_id]
    response = {
        'success': True,
        'state': task['state'],
        'progress': task['progress'],
        'progress_percent': task.get('progress_percent', 0)
    }

    if task['state'] == TaskState.DONE:
        response['result'] = task['result']
    elif task['state'] == TaskState.FAILED:
        response['error'] = task['error']

    return jsonify(response)


@app.route('/download/md/<path:filepath>')
def download_md(filepath):
    """下载 Markdown 文件"""
    safe_path = validate_path(filepath)
    if safe_path and safe_path.exists():
        return send_file(safe_path, mimetype='text/markdown')
    return "文件不存在", 404


@app.route('/download/zip/<path:filepath>')
def download_zip(filepath):
    """下载 ZIP 文件"""
    safe_path = validate_path(filepath)
    if safe_path and safe_path.exists():
        return send_file(safe_path, as_attachment=True)
    return "文件不存在", 404


@app.route('/preview/<path:filepath>')
def preview_md(filepath):
    """预览 Markdown 内容"""
    safe_path = validate_path(filepath)
    if safe_path and safe_path.exists():
        content = safe_path.read_text(encoding='utf-8')
        return jsonify({'success': True, 'content': content})
    return jsonify({'success': False, 'error': '文件不存在'})


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'service': 'wemath2md-desktop'})


def main():
    """启动服务器"""
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 初始化日志
    from config import logging as log_cfg
    setup_logger(level=log_cfg.level, log_file="desktop_backend.log")

    logger.info("WeMath2MD Desktop 后端服务启动中...")
    logger.info(f"监听地址: http://127.0.0.1:54321")

    # 启动 Flask 服务
    app.run(debug=False, host='127.0.0.1', port=54321, use_reloader=False)


if __name__ == '__main__':
    main()
