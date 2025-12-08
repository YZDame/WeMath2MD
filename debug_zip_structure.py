# debug_zip_structure.py
"""
调试脚本：检查 MinerU 返回的 ZIP 文件结构
"""

import os
import io
import zipfile
import requests
from dotenv import load_dotenv

load_dotenv()

def check_zip_structure(zip_url):
    """下载并检查 ZIP 文件结构"""
    print(f"📥 正在下载: {zip_url[:80]}...")
    
    response = requests.get(zip_url, timeout=120)
    
    if response.status_code != 200:
        print(f"❌ 下载失败: {response.status_code}")
        return
    
    print(f"✅ 下载成功, 大小: {len(response.content) / 1024:.1f} KB")
    
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        print("\n📦 ZIP 文件内容:")
        print("-" * 60)
        
        for name in sorted(zf.namelist()):
            info = zf.getinfo(name)
            size = info.file_size
            
            # 标记文件类型
            if name.endswith('/'):
                type_mark = "📁"
            elif name.endswith('.md'):
                type_mark = "📄"
            elif any(name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']):
                type_mark = "🖼️ "
            elif name.endswith('.json'):
                type_mark = "📋"
            else:
                type_mark = "  "
            
            print(f"{type_mark} {name} ({size:,} bytes)")
        
        print("-" * 60)
        print(f"总计: {len(zf.namelist())} 个文件/目录")
        
        # 检查是否有图片
        images = [f for f in zf.namelist() if any(f.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])]
        print(f"\n🖼️  找到 {len(images)} 个图片文件:")
        for img in images:
            print(f"   - {img}")


if __name__ == "__main__":
    # 这里需要手动填入一个 MinerU 返回的 zip_url 进行测试
    # 可以从转换日志中获取
    
    test_url = input("请输入 MinerU 返回的 full_zip_url: ").strip()
    
    if test_url:
        check_zip_structure(test_url)
    else:
        print("未输入 URL")
