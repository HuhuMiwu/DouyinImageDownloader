from DrissionPage import ChromiumPage
import json
import time
import os


def get_douyin_cookie():
    """获取抖音cookie"""
    try:
        # 创建页面对象
        dp = ChromiumPage()
        
        # 访问抖音登录页面
        print("正在打开抖音页面...")
        dp.get('https://www.douyin.com/user/self?from_tab_name=main&showTab=favorite_collection')
        
        # 等待用户手动登录
        print("请在浏览器中完成登录操作...")
        print("登录完成后，按回车键继续...")
        input()
        
        # 获取当前页面的cookie
        cookies = dp.cookies()
        
        # 将cookie转换为字符串格式
        cookie_str = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
        
        # 清理旧的cookie文件
        cookie_file = 'douyin_cookies.json'
        if os.path.exists(cookie_file):
            try:
                os.remove(cookie_file)
                print("已清理旧的cookie文件")
            except Exception as e:
                print(f"清理旧文件时出错: {e}")
        
        # 保存新的cookie到文件
        cookie_data = {
            'cookies': cookies,
            'cookie_string': cookie_str,
            'timestamp': time.time(),
            'url': dp.url
        }
        
        with open(cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookie_data, f, ensure_ascii=False, indent=2)
        
        print(f"新Cookie已保存到 {cookie_file} 文件")
        print(f"Cookie字符串: {cookie_str[:100]}...")
        
        # 关闭浏览器
        dp.quit()
        
        return cookie_str
        
    except Exception as e:
        print(f"获取cookie时出错: {e}")
        return None


def load_cookie_from_file():
    """从文件加载cookie"""
    try:
        with open('douyin_cookies.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['cookie_string']
    except FileNotFoundError:
        print("Cookie文件不存在")
        return None
    except Exception as e:
        print(f"加载cookie文件时出错: {e}")
        return None


if __name__ == "__main__":
    print("=== 抖音Cookie获取工具 ===")
    print("正在启动自动获取Cookie功能...")
    
    # 直接获取最新cookie
    cookie = get_douyin_cookie()
    if cookie:
        print("\nCookie获取成功！")
        print(f"Cookie已保存到文件: douyin_cookies.json")
        print(f"Cookie字符串长度: {len(cookie)} 字符")
    else:
        print("\nCookie获取失败，请检查网络连接和登录状态")
