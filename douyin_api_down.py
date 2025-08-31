import requests
import os
import json
import time
import asyncio
import aiohttp
import aiofiles
from urllib.parse import urlparse
from pathlib import Path
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
import logging


def save_cookie(cookie):
    """保存cookie到本地文件"""
    with open('cookie.txt', 'w', encoding='utf-8') as f:
        f.write(cookie)


def load_cookie():
    """从本地文件加载cookie"""
    if os.path.exists('cookie.txt'):
        with open('cookie.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None


def validate_cookie(cookie):
    """验证cookie是否有效"""
    try:
        base_url = "http://192.168.68.10:2380"
        url = base_url + '/api/douyin/web/fetch_user_collection_videos'
        params = {
            'cookie': cookie,
            'max_cursor': 0,
            'count': 1
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # 检查返回的数据结构，如果有data字段且不是错误信息，则认为cookie有效
            if 'data' in data and 'error' not in str(data).lower():
                return True
        return False
    except Exception as e:
        print(f"验证cookie时出错: {e}")
        return False


def load_cookie_from_douyin_cookie():
    """从douyin_cookies.json文件获取cookie字符串"""
    try:
        # 检查douyin_cookies.json文件路径
        json_path = '../douyin_cookies.json'  # 上级目录
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)
            
            # 直接使用cookie_string字段
            cookie_str = cookies_data.get('cookie_string', '')
            if cookie_str:
                print("从douyin_cookies.json成功加载cookie")
                return cookie_str
                
    except json.JSONDecodeError as e:
        print(f"解析douyin_cookies.json文件失败: {e}")
    except Exception as e:
        print(f"从douyin_cookies.json加载cookie时出错: {e}")
    
    return None


def run_douyin_cookie_script():
    """运行douyin_cookie.py脚本来获取新的cookie"""
    try:
        print("正在运行douyin_cookie.py来获取新的cookie...")
        # 使用当前Python环境运行douyin_cookie.py
        result = subprocess.run([sys.executable, 'douyin_cookie.py'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        if result.returncode == 0:
            print("douyin_cookie.py执行成功")
            # 执行成功后重新尝试加载cookie
            return load_cookie_from_douyin_cookie()
        else:
            print(f"douyin_cookie.py执行失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"运行douyin_cookie.py时出错: {e}")
        return None


def get_valid_cookie():
    """获取有效的cookie，自动从douyin_cookie.py获取"""
    
    # 步骤1: 尝试从douyin_cookie.py加载cookie
    print("正在尝试从douyin_cookie.py获取cookie...")
    cookie = load_cookie_from_douyin_cookie()
    
    if cookie:
        print("检测到douyin_cookie.py中的cookie，正在验证有效性...")
        if validate_cookie(cookie):
            print("douyin_cookie.py中的cookie有效，将直接使用")
            # 同时保存到本地cookie.txt，保持一致性
            save_cookie(cookie)
            return cookie
        else:
            print("douyin_cookie.py中的cookie已失效")
    else:
        print("未在douyin_cookie.py中找到cookie")
    
    # 步骤2: 尝试从本地cookie.txt加载cookie
    saved_cookie = load_cookie()
    if saved_cookie:
        print("检测到本地cookie.txt中的cookie，正在验证有效性...")
        if validate_cookie(saved_cookie):
            print("本地cookie有效，将直接使用")
            return saved_cookie
        else:
            print("本地cookie已失效")
    
    # 步骤3: 运行douyin_cookie.py来获取新的cookie
    print("正在自动运行douyin_cookie.py来获取新的cookie...")
    new_cookie = run_douyin_cookie_script()
    
    if new_cookie:
        print("成功获取到新的cookie")
        if validate_cookie(new_cookie):
            print("新cookie验证成功")
            save_cookie(new_cookie)  # 保存到本地cookie.txt
            return new_cookie
        else:
            print("新cookie验证失败")
    else:
        print("无法从douyin_cookie.py获取cookie")
    
    # 步骤4: 如果以上方法都失败，回退到手动输入
    print("所有自动获取方式都失败了，请手动输入cookie")
    while True:
        cookie = input('请输入抖音cookie: ').strip()
        if not cookie:
            print("cookie不能为空，请重新输入")
            continue
            
        print("正在验证cookie有效性...")
        if validate_cookie(cookie):
            save_cookie(cookie)
            print("cookie验证成功，已保存到本地")
            return cookie
        else:
            print("cookie无效，请重新输入")


async def async_download_image(session, url, filepath, semaphore):
    """异步下载单张图片"""
    async with semaphore:  # 限制并发数量
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.douyin.com/',
            }
            
            async with session.get(url, headers=headers, timeout=30) as response:
                response.raise_for_status()
                
                # 确保目录存在
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # 异步写入文件
                async with aiofiles.open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                
                print(f"✓ 下载成功: {os.path.basename(filepath)}")
                return True
                
        except Exception as e:
            print(f"✗ 下载失败: {url} - {str(e)}")
            return False


async def async_download_images_for_video(session, video_data, save_dir, max_concurrent=5):
    """异步下载单个作品的所有图片"""
    video_id = video_data.get('aweme_id', 'unknown')
    desc = video_data.get('desc', '')[:50]
    
    # 清理文件名中的特殊字符
    safe_desc = "".join(c for c in desc if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_desc = safe_desc[:30]
    
    images = extract_images_from_video_data(video_data)
    
    if not images:
        print(f"⚠ 作品 {video_id} 未找到可下载的图片")
        return 0
    
    print(f"\n📸 正在异步下载作品 {video_id} 的图片 ({len(images)} 张)...")
    
    # 创建信号量限制并发数
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # 准备下载任务
    tasks = []
    for idx, img_url in enumerate(images, 1):
        # 获取文件扩展名
        parsed_url = urlparse(img_url)
        ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
        
        # 构建文件名
        if len(images) > 1:
            filename = f"{video_id}_{safe_desc}_{idx}{ext}"
        else:
            filename = f"{video_id}_{safe_desc}{ext}"
        
        filepath = os.path.join(save_dir, filename)
        
        # 避免重复下载
        if os.path.exists(filepath):
            print(f"⚡ 已存在: {filename}")
            continue
        
        # 创建异步任务
        task = async_download_image(session, img_url, filepath, semaphore)
        tasks.append(task)
    
    if not tasks:
        return 0
    
    # 执行所有异步任务
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 统计成功数量
    success_count = sum(1 for result in results if result is True)
    print(f"✅ 作品 {video_id} 下载完成: {success_count}/{len(tasks)} 成功")
    
    return success_count


def download_images_for_video_async(video_data, save_dir, max_concurrent=5):
    """同步包装函数，用于异步下载"""
    async def _run_async():
        async with aiohttp.ClientSession() as session:
            return await async_download_images_for_video(session, video_data, save_dir, max_concurrent)
    
    # 运行异步事件循环
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已有运行的事件循环，使用它
            return asyncio.create_task(_run_async())
        else:
            # 否则创建新的事件循环
            return asyncio.run(_run_async())
    except Exception as e:
        print(f"异步下载出错: {e}")
        return 0


async def async_download_all_videos(all_aweme_list, save_dir, max_concurrent=5):
    """异步批量下载所有作品的图片"""
    print(f"\n🚀 开始异步批量下载 {len(all_aweme_list)} 个作品的图片...")
    
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 为每个作品创建异步任务
        tasks = []
        for video_data in all_aweme_list:
            task = async_download_images_for_video(session, video_data, save_dir, max_concurrent)
            tasks.append(task)
        
        # 执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计总成功数量
        total_success = sum(result for result in results if isinstance(result, int))
        print(f"\n🎉 批量下载完成! 总共处理了 {len(all_aweme_list)} 个作品")
        
        return total_success


def extract_images_from_video_data(video_data):
    """从视频数据中提取无水印原图URL"""
    images = []
    
    try:
        # 检查是否是图文作品
        if 'images' in video_data and video_data['images']:
            # 图文作品的图片列表
            for img_data in video_data['images']:
                if 'url_list' in img_data and img_data['url_list']:
                    # 取最高质量的图片URL
                    img_url = img_data['url_list'][-1]  # 通常最后一个是无水印原图
                    images.append(img_url)
        
        # 检查视频封面图
        elif 'video' in video_data and video_data['video']:
            video_info = video_data['video']
            if 'cover' in video_info and video_info['cover']:
                cover_data = video_info['cover']
                if 'url_list' in cover_data and cover_data['url_list']:
                    cover_url = cover_data['url_list'][-1]
                    images.append(cover_url)
        
        # 检查动态封面
        elif 'dynamic_cover' in video_data and video_data['dynamic_cover']:
            dynamic_cover = video_data['dynamic_cover']
            if 'url_list' in dynamic_cover and dynamic_cover['url_list']:
                dynamic_url = dynamic_cover['url_list'][-1]
                images.append(dynamic_url)
                
    except Exception as e:
        print(f"提取图片时出错: {e}")
    
    return images


def download_images_for_video(video_data, save_dir):
    """下载单个作品的所有图片"""
    video_id = video_data.get('aweme_id', 'unknown')
    desc = video_data.get('desc', '')[:50]  # 限制描述长度
    
    # 清理文件名中的特殊字符
    safe_desc = "".join(c for c in desc if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_desc = safe_desc[:30]  # 限制长度
    
    images = extract_images_from_video_data(video_data)
    
    if not images:
        print(f"⚠ 作品 {video_id} 未找到可下载的图片")
        return
    
    print(f"\n📸 正在下载作品 {video_id} 的图片 ({len(images)} 张)...")
    
    for idx, img_url in enumerate(images, 1):
        # 获取文件扩展名
        parsed_url = urlparse(img_url)
        ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
        
        # 构建文件名
        if len(images) > 1:
            filename = f"{video_id}_{safe_desc}_{idx}{ext}"
        else:
            filename = f"{video_id}_{safe_desc}{ext}"
        
        filepath = os.path.join(save_dir, filename)
        
        # 避免重复下载
        if os.path.exists(filepath):
            print(f"⚡ 已存在: {filename}")
            continue
        
        download_image(img_url, filepath)
        time.sleep(0.5)  # 避免请求过快


# 主程序
if __name__ == "__main__":
    # 获取有效的cookie
    cookie = get_valid_cookie()
    
    # 使用有效的cookie进行数据获取
    a = '/api/douyin/web/fetch_user_collection_videos'  # 获取用户收藏作品数据
    b = '/api/douyin/web/fetch_one_video'               # 获取单个作品数据

    base_url = "http://192.168.68.10:2380"
    url = base_url + a
    
    all_aweme_list = []  # 存储所有获取到的作品
    max_cursor = 0  # 从第0页开始
    has_more = True  # 是否还有更多数据
    
    print("正在获取所有收藏作品...")
    
    # 循环获取所有页面的数据
    page = 1
    while has_more:
        params = {
            'cookie': cookie,
            'max_cursor': max_cursor,
            'count': 20  # 每页20个作品
        }
        
        try:
            print(f"正在获取第{page}页数据...")
            response = requests.get(url, params=params).json()
            
            if 'data' not in response:
                print("响应中缺少'data'字段")
                break
                
            data = response['data']
            
            # 检查是否有aweme_list字段
            if 'aweme_list' not in data:
                print("data中缺少'aweme_list'字段，可用字段:", list(data.keys()))
                break
                
            aweme_list = data['aweme_list'] or []  # 处理null情况
            if aweme_list:
                all_aweme_list.extend(aweme_list)
                print(f"第{page}页获取到 {len(aweme_list)} 个作品")
            else:
                print(f"第{page}页没有获取到作品")
            
            # 检查是否还有更多数据
            has_more = data.get('has_more', 0)
            
            # 重要：使用cursor字段来更新游标，而不是max_cursor
            cursor = data.get('cursor', max_cursor)
            if cursor == max_cursor and page > 1:
                # 如果游标没有变化，说明没有更多数据
                has_more = False
                print("游标未更新，停止获取")
            else:
                max_cursor = cursor
            
            print(f"游标更新: {max_cursor}, has_more: {has_more}")
            
            if not has_more:
                print("已获取完所有数据")
                
            page += 1
            time.sleep(1)  # 避免请求过快
            
        except Exception as e:
            print(f"获取第{page}页数据时出错: {e}")
            break
    
    if not all_aweme_list:
        print("未获取到任何作品数据")
        exit()
    
    print(f"\n总共获取到 {len(all_aweme_list)} 个作品")
    
    # 创建保存图片的目录
    save_dir = os.path.join(os.path.dirname(__file__), 'downloaded_images')
    os.makedirs(save_dir, exist_ok=True)
    print(f"图片将保存到: {save_dir}")
    
    # 询问用户选择下载方式
    print("\n请选择下载方式:")
    print("1. 同步下载 (稳定但较慢)")
    print("2. 异步下载 (快速并发)")
    choice = input("请输入选择 (1/2): ").strip()
    
    if choice == "2":
        # 异步下载
        print("\n🚀 开始异步批量下载...")
        start_time = time.time()
        
        async def run_async_download():
            async with aiohttp.ClientSession() as session:
                semaphore = asyncio.Semaphore(10)  # 限制并发数
                
                # 为每个作品创建异步任务
                tasks = []
                for idx, video_data in enumerate(all_aweme_list, 1):
                    print(f"\n📋 准备下载第 {idx}/{len(all_aweme_list)} 个作品...")
                    task = async_download_images_for_video(session, video_data, save_dir, 10)
                    tasks.append(task)
                
                # 执行所有任务
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 统计总成功数量
                total_success = sum(result for result in results if isinstance(result, int))
                return total_success
        
        try:
            total_success = asyncio.run(run_async_download())
            elapsed_time = time.time() - start_time
            print(f"\n🎉 异步下载完成!")
            print(f"✅ 成功处理了 {total_success} 个作品")
            print(f"⏱️  耗时: {elapsed_time:.2f} 秒")
            print(f"📁 图片保存路径: {save_dir}")
        except Exception as e:
            print(f"异步下载出错: {e}")
            print("正在回退到同步下载...")
            
            # 回退到同步下载
            success_count = 0
            for idx, item in enumerate(all_aweme_list, 1):
                print(f"\n{'='*50}")
                print(f"处理第 {idx}/{len(all_aweme_list)} 个作品...")
                
                video_id = item.get('aweme_id', 'unknown')
                print(f"作品ID: {video_id}")
                
                download_images_for_video(item, save_dir)
                success_count += 1
                
                time.sleep(0.5)
            
            print(f"\n{'='*50}")
            print(f"✅ 同步下载完成! 成功处理了 {success_count} 个作品")
            print(f"📁 图片保存路径: {save_dir}")
    
    else:
        # 同步下载
        success_count = 0
        for idx, item in enumerate(all_aweme_list, 1):
            print(f"\n{'='*50}")
            print(f"处理第 {idx}/{len(all_aweme_list)} 个作品...")
            
            video_id = item.get('aweme_id', 'unknown')
            print(f"作品ID: {video_id}")
            
            download_images_for_video(item, save_dir)
            success_count += 1
            
            time.sleep(0.5)
        
        print(f"\n{'='*50}")
        print(f"✅ 同步下载完成! 成功处理了 {success_count} 个作品")
        print(f"📁 图片保存路径: {save_dir}")


def download_single_video_images():
    """下载单个指定作品的图片"""
    video_id = input("请输入要下载的作品ID: ").strip()
    if not video_id:
        print("作品ID不能为空")
        return
    
    cookie = get_valid_cookie()
    base_url = "http://192.168.68.10:2380"
    url = base_url + '/api/douyin/web/fetch_one_video'
    params = {
        'cookie': cookie,
        'aweme_id': video_id
    }
    
    try:
        response = requests.get(url, params=params).json()
        video_data = response.get('data')
        
        if not video_data:
            print("未获取到作品数据")
            return
        
        save_dir = os.path.join(os.path.dirname(__file__), 'downloaded_images')
        download_images_for_video(video_data, save_dir)
        print(f"✅ 单个作品处理完成! 图片保存路径: {save_dir}")
        
    except Exception as e:
        print(f"获取单个作品数据时出错: {e}")


def download_image(url, filepath):
    """下载单张图片"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.douyin.com/',
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'wb') as f:
            f.write(response.content)

        print(f"✓ 下载成功: {filepath}")
        return True
    except Exception as e:
        print(f"✗ 下载失败: {url} - {str(e)}")
        return False
