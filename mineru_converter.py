# mineru_converter.py
"""
MinerU API 批量图片转 Markdown
功能：批量上传图片，识别后合并 markdown 和图片，打包成 zip 返回
"""

import os
import io
import re
import time
import shutil
import zipfile
import requests
from pathlib import Path


class MinerUConverter:
    def __init__(self, api_token):
        self.token = api_token
        self.base_url = "https://mineru.net/api/v4"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }
    
    def apply_upload_urls(self, file_names):
        """步骤1: 批量申请上传链接"""
        url = f"{self.base_url}/file-urls/batch"
        
        # 使用带序号的 data_id 以便后续排序
        files = [
            {"name": name, "data_id": f"file_{i:04d}_{int(time.time())}"}
            for i, name in enumerate(file_names)
        ]
        
        data = {
            "files": files,
            "enable_formula": True,
            "enable_table": True,
            "layout_model": "doclayout_yolo",
            "language": "ch"
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result["code"] == 0:
                return result["data"]["batch_id"], result["data"]["file_urls"]
            else:
                raise Exception(f"申请上传链接失败: {result}")
        else:
            raise Exception(f"API 请求失败: {response.status_code}")
    
    def upload_files(self, file_paths, upload_urls):
        """步骤2: 上传文件"""
        success_count = 0
        
        for file_path, upload_url in zip(file_paths, upload_urls):
            try:
                with open(file_path, 'rb') as f:
                    response = requests.put(upload_url, data=f)
                    
                if response.status_code == 200:
                    print(f"   ✅ 上传成功: {os.path.basename(file_path)}")
                    success_count += 1
                else:
                    print(f"   ❌ 上传失败: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"   ❌ 上传异常: {e}")
        
        return success_count
    
    def wait_for_result(self, batch_id, max_wait=300, interval=3):
        """步骤3: 等待解析完成"""
        url = f"{self.base_url}/extract-results/batch/{batch_id}"
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                
                if result["code"] == 0:
                    extract_result = result["data"].get("extract_result", [])
                    
                    if not extract_result:
                        # 还没有结果
                        elapsed = int(time.time() - start_time)
                        print(f"   ⏳ 等待解析开始... ({elapsed}s)", end='\r')
                        time.sleep(interval)
                        continue
                    
                    # 检查所有文件的状态
                    states = [item.get("state") for item in extract_result]
                    
                    if all(s == "done" for s in states):
                        print(f"\n   ✅ 全部解析完成!")
                        return extract_result
                    elif any(s == "failed" for s in states):
                        failed = [item["file_name"] for item in extract_result if item.get("state") == "failed"]
                        print(f"\n   ⚠️ 部分文件失败: {failed}")
                        return extract_result
                    else:
                        # 还在处理中
                        done_count = sum(1 for s in states if s == "done")
                        elapsed = int(time.time() - start_time)
                        print(f"   ⏳ 解析中: {done_count}/{len(states)} 完成 ({elapsed}s)", end='\r')
                        time.sleep(interval)
                else:
                    raise Exception(f"查询失败: {result}")
            else:
                raise Exception(f"查询请求失败: {response.status_code}")
        
        raise Exception(f"等待超时 ({max_wait}s)")
    
    def download_and_extract_zip(self, zip_url, file_name, temp_dir, index):
        """
        下载 zip 并解压到临时目录
        返回: (md_content, images_extracted_count)
        
        zip 结构:
        <root>/
           ├── full.md                 ← 需要抽取的 Markdown 内容
           ├── images/                 ← 图片资源文件夹
           ├── *.json                  ← 可忽略
           ├── *_origin.pdf            ← 可忽略
        """
        try:
            response = requests.get(zip_url, timeout=120)
            
            if response.status_code != 200:
                return f"<!-- {file_name}: 下载失败 {response.status_code} -->", 0
            
            md_content = None
            images_count = 0
            
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                # 打印 zip 内容用于调试
                all_files = zf.namelist()
                print(f"      📦 ZIP 包含 {len(all_files)} 个文件")
                
                # 找 markdown 文件
                for name in all_files:
                    # full.md 可能在根目录或一级子目录下
                    if name.endswith('full.md') or name.endswith('.md'):
                        parts = name.split('/')
                        # 优先选择 full.md
                        if name.endswith('full.md') and len(parts) <= 2:
                            md_content = zf.read(name).decode('utf-8')
                            md_content = self._rewrite_image_paths(md_content, index)
                            break
                        # 备选任何 .md 文件
                        elif md_content is None and len(parts) <= 2:
                            md_content = zf.read(name).decode('utf-8')
                            md_content = self._rewrite_image_paths(md_content, index)
                
                # 提取 images 文件夹中的图片（支持多种路径格式）
                for name in all_files:
                    # 跳过目录
                    if name.endswith('/'):
                        continue
                    
                    # 检查是否是图片文件（在 images 目录下或者是图片扩展名）
                    lower_name = name.lower()
                    is_image = any(lower_name.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])
                    is_in_images = '/images/' in name or name.startswith('images/')
                    
                    if is_image and is_in_images:
                        # 获取原始图片文件名
                        img_name = os.path.basename(name)
                        # 添加索引前缀避免冲突
                        new_img_name = f"{index:04d}_{img_name}"
                        
                        # 保存到临时目录的 images 文件夹
                        target_path = temp_dir / "images" / new_img_name
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(target_path, 'wb') as f:
                            f.write(zf.read(name))
                        images_count += 1
            
            if md_content is None:
                md_content = f"<!-- {file_name}: zip 中未找到 markdown 文件 -->"
            
            return md_content, images_count
            
        except Exception as e:
            return f"<!-- {file_name}: 下载/解压异常 {e} -->", 0
    
    def _rewrite_image_paths(self, md_content, index):
        """
        重写 markdown 中的图片路径
        将 images/xxx.png 改为 images/{index:04d}_xxx.png
        """
        def replace_func(match):
            # 获取原始路径
            prefix = match.group(1)  # ![ 或 ![xxx
            alt_text = match.group(2)  # alt 文本
            img_path = match.group(3)  # 图片路径
            
            # 只处理 images/ 开头的路径
            if img_path.startswith('images/'):
                img_name = img_path[7:]  # 去掉 'images/' 前缀
                new_path = f"images/{index:04d}_{img_name}"
                return f"![{alt_text}]({new_path})"
            return match.group(0)
        
        # 匹配 markdown 图片语法 ![alt](path)
        pattern = r'(!\[)([^\]]*)\]\(([^)]+)\)'
        return re.sub(pattern, replace_func, md_content)
    
    def convert_images(self, image_dir, output_dir=None, output_name=None):
        """
        主流程：批量转换图片并打包
        
        Args:
            image_dir: 输入图片目录
            output_dir: 输出目录（可选，默认与 image_dir 同级）
            output_name: 输出文件夹/md文件的名称（可选，默认 "converted"）
        
        Returns:
            dict: {
                'output_dir': 输出目录路径,
                'md_file': markdown 文件路径,
                'images_dir': 图片目录路径,
                'zip_file': zip 文件路径,
                'image_count': 提取的图片数量
            }
        """
        
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}
        image_dir = Path(image_dir)
        
        images = sorted([
            f for f in image_dir.iterdir()
            if f.suffix.lower() in valid_exts
        ])
        
        if not images:
            print("⚠️ 未找到图片文件")
            return None
        
        # 设置输出目录和名称
        if output_name is None:
            output_name = "converted"
        
        if output_dir is None:
            # 默认放在 image_dir 的同级目录
            output_dir = image_dir.parent / output_name
        else:
            output_dir = Path(output_dir) / output_name
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📚 找到 {len(images)} 个文件")
        print(f"📝 输出目录: {output_dir}\n")
        
        # 步骤1: 申请上传链接
        print("📤 步骤1: 申请上传链接...")
        file_names = [img.name for img in images]
        batch_id, upload_urls = self.apply_upload_urls(file_names)
        print(f"   ✅ batch_id: {batch_id}\n")
        
        # 步骤2: 上传文件
        print("📤 步骤2: 上传文件...")
        file_paths = [str(img) for img in images]
        success = self.upload_files(file_paths, upload_urls)
        print(f"   📊 上传完成: {success}/{len(images)}\n")
        
        # 步骤3: 等待解析
        print("⏳ 步骤3: 等待解析完成...")
        results = self.wait_for_result(batch_id)
        print()
        
        # 步骤4: 下载、解压并合并
        print("📥 步骤4: 下载并解压 zip 文件...")
        
        # 创建临时目录
        temp_dir = Path(f"_temp_{int(time.time())}")
        temp_dir.mkdir(exist_ok=True)
        (temp_dir / "images").mkdir(exist_ok=True)
        
        try:
            # 按 data_id 排序确保顺序正确（按原始图片顺序）
            results_sorted = sorted(results, key=lambda x: x.get("data_id", ""))
            
            all_markdown = []
            total_images = 0
            
            for i, item in enumerate(results_sorted):
                file_name = item.get("file_name", f"file_{i}")
                state = item.get("state")
                zip_url = item.get("full_zip_url")
                
                if state == "done" and zip_url:
                    md_content, img_count = self.download_and_extract_zip(
                        zip_url, file_name, temp_dir, i
                    )
                    all_markdown.append(md_content)
                    total_images += img_count
                    print(f"   ✅ {file_name} (提取 {img_count} 张图片)")
                else:
                    err_msg = item.get("err_msg", "未知错误")
                    all_markdown.append(f"\n\n<!-- {file_name} 转换失败: {err_msg} -->\n\n")
                    print(f"   ❌ {file_name}: {err_msg}")
            
            print(f"\n   📊 共提取 {total_images} 张图片")
            
            # 步骤5: 合并 markdown 并保存到输出目录
            print("\n📝 步骤5: 合并 Markdown 文件...")
            final_content = "\n\n---\n\n".join(all_markdown)
            
            # 直接保存到输出目录
            md_file = output_dir / f"{output_name}.md"
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(final_content)
            print(f"   ✅ 已生成: {md_file}")
            
            # 步骤6: 复制图片到输出目录（如果有图片的话）
            print("\n📁 步骤6: 复制图片到输出目录...")
            
            final_images_dir = output_dir / "images"
            temp_images_dir = temp_dir / "images"
            
            if temp_images_dir.exists() and any(temp_images_dir.iterdir()):
                final_images_dir.mkdir(exist_ok=True)
                for img_file in temp_images_dir.iterdir():
                    if img_file.is_file():
                        shutil.copy2(img_file, final_images_dir / img_file.name)
                print(f"   ✅ 图片已保存到: {final_images_dir}")
            else:
                print(f"   ℹ️  无额外图片需要复制")
            
            # 步骤7: 打包成 zip（整个结果目录）
            print("\n📦 步骤7: 打包成 zip 文件...")
            
            result_root = output_dir.parent  # 例如 output/反演变换及其应用/
            zip_file = result_root.parent / f"{result_root.name}.zip"  # output/反演变换及其应用.zip
            
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 遍历整个结果目录
                for root, dirs, files in os.walk(result_root):
                    for file in files:
                        # 跳过 zip 文件本身（避免套娃）
                        if file.endswith('.zip'):
                            continue
                        file_path = Path(root) / file
                        # 相对于结果目录的路径
                        arcname = file_path.relative_to(result_root)
                        zf.write(file_path, arcname)
            
            print(f"   ✅ 已打包: {zip_file}")
            
            # 统计信息
            zip_size = zip_file.stat().st_size / 1024 / 1024  # MB
            print(f"\n🎉 完成！")
            print(f"   📄 Markdown: {md_file}")
            print(f"   🖼️  图片数量: {total_images}")
            print(f"   📦 ZIP 文件: {zip_file} ({zip_size:.2f} MB)")
            
            return {
                'output_dir': str(output_dir),
                'md_file': str(md_file),
                'images_dir': str(final_images_dir),
                'zip_file': str(zip_file),
                'image_count': total_images
            }
            
        finally:
            # 清理临时目录
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                print(f"   🧹 已清理临时文件")


# ============ 使用 ============
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # 加载 .env 文件
    load_dotenv()
    
    # 从环境变量读取 API Token
    API_TOKEN = os.getenv("MINERU_API_TOKEN")
    
    if not API_TOKEN:
        print("❌ 错误: 未找到 MINERU_API_TOKEN")
        print("   请创建 .env 文件并设置 MINERU_API_TOKEN=your_token")
        exit(1)
    
    converter = MinerUConverter(api_token=API_TOKEN)
    
    # 单独使用示例（配合 downloader.py 使用更佳）
    # 输出目录会放在 image_dir 的同级目录下
    result = converter.convert_images(
        image_dir="downloaded_images",
        output_name="converted"
    )
    
    if result:
        print(f"\n📊 转换结果:")
        print(f"   输出目录: {result['output_dir']}")
        print(f"   MD 文件: {result['md_file']}")
        print(f"   图片目录: {result['images_dir']}")
        print(f"   ZIP 文件: {result['zip_file']}")
