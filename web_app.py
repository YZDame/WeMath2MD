# web_app.py
"""
WeMath2MD Web 界面
简洁现代的前端，提供链接输入和结果下载
"""

import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv

from downloader import WechatImageDownloader
from mineru_converter import MinerUConverter

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.config['OUTPUT_DIR'] = 'output'

# 存储转换历史
conversion_history = []


@app.route('/')
def index():
    """首页"""
    return render_template('index.html', history=conversion_history)


@app.route('/convert', methods=['POST'])
def convert():
    """处理转换请求"""
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'success': False, 'error': '请输入文章链接'})
    
    if not url.startswith('http'):
        return jsonify({'success': False, 'error': '无效的链接格式'})
    
    # 获取 API Token
    api_token = os.getenv('MINERU_API_TOKEN')
    if not api_token:
        return jsonify({'success': False, 'error': '服务器未配置 API Token'})
    
    try:
        # 第一阶段：下载图片
        downloader = WechatImageDownloader(output_dir=app.config['OUTPUT_DIR'])
        download_result = downloader.download_from_url(url)
        
        if not download_result:
            return jsonify({'success': False, 'error': '下载文章图片失败'})
        
        # 第二阶段：OCR 转换
        converter = MinerUConverter(api_token=api_token)
        convert_result = converter.convert_images(
            image_dir=download_result['images_dir'],
            output_dir=download_result['result_dir'],
            output_name="converted"
        )
        
        if not convert_result:
            return jsonify({'success': False, 'error': 'OCR 转换失败'})
        
        # 保存到历史记录
        result = {
            'title': download_result['title'],
            'md_file': convert_result['md_file'],
            'zip_file': convert_result['zip_file'],
            'image_count': convert_result['image_count'],
            'result_dir': download_result['result_dir']
        }
        
        # 添加到历史（最新的在前面）
        conversion_history.insert(0, result)
        
        # 只保留最近 10 条
        if len(conversion_history) > 10:
            conversion_history.pop()
        
        return jsonify({
            'success': True,
            'title': result['title'],
            'md_file': result['md_file'],
            'zip_file': result['zip_file'],
            'image_count': result['image_count']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/download/md/<path:filepath>')
def download_md(filepath):
    """下载/预览 Markdown 文件"""
    file_path = Path(filepath)
    if file_path.exists():
        return send_file(file_path, mimetype='text/markdown')
    return "文件不存在", 404


@app.route('/download/zip/<path:filepath>')
def download_zip(filepath):
    """下载 ZIP 文件"""
    file_path = Path(filepath)
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    return "文件不存在", 404


@app.route('/preview/<path:filepath>')
def preview_md(filepath):
    """预览 Markdown 内容"""
    file_path = Path(filepath)
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        return jsonify({'success': True, 'content': content})
    return jsonify({'success': False, 'error': '文件不存在'})


if __name__ == '__main__':
    # 确保模板目录存在
    os.makedirs('templates', exist_ok=True)
    
    print("🚀 WeMath2MD Web 服务启动中...")
    print("📎 访问 http://localhost:8080")
    
    app.run(debug=True, host='0.0.0.0', port=8080)
