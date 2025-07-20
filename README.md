# 抖音图片下载器
## 一个用于从抖音个人收藏中批量下载图片的工具，支持多线程下载、自动去重和图片信息记录功能。

# 功能特点
1. 自动采集抖音个人收藏的图片作品
2. 多线程并行下载，提高效率
3. 智能去重，避免重复下载
4. 记录图片元数据到CSV文件
5. 详细日志记录，便于问题排查
6. 自动创建下载目录和管理文件
# 安装说明
## 环境要求
1. Python 3.8+
2. 谷歌浏览器（Chromium内核）
## 安装步骤
1. 克隆本仓库
<pre><code>git clone https://github.com/yourusername/douyin-image-downloader.git

cd douyin-image-downloader</code></pre>
2. 创建并激活虚拟环境
<pre><code>python -m venv .venv
  
# Windows激活虚拟环境
.venv\Scripts\activate
  
# macOS/Linux激活虚拟环境
source .venv/bin/activate</code></pre>

3. 安装依赖
<pre>pip install -r requirements.txt</pre>

# 使用方法
1. 确保已登录抖音网页版
2. 运行下载器
<pre>python "DY Picture Downloader/main.py"</pre>
3. 程序会自动打开浏览器并开始采集和下载图片
# 项目结构
* main.py - 程序主入口
* downloaded_images/ - 下载的图片存储目录
* image_info.csv - 图片元数据记录
* downloaded_ids.txt - 已下载图片ID记录
* downloader.log - 程序运行日志
# 注意事项
* 下载速度受网络环境和服务器限制
* 请遵守抖音用户协议，合理使用本工具
* 图片版权归原作者所有，仅供个人学习使用
* 程序默认下载前200页收藏内容，可在代码中调整
# 依赖库
* requests - HTTP请求处理
* DrissionPage - 网页自动化和数据采集
* python-dotenv - 环境变量管理
* logging - 日志系统
