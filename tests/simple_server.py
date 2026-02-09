#!/usr/bin/env python3
"""
简单的量化监控系统Web服务器
提供静态文件和HTML页面
"""

import http.server
import socketserver
import os
import sys

PORT = 8089
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def do_GET(self):
        # 保存原始路径
        original_path = self.path
        
        # 如果访问根路径，返回index.html
        if self.path == '/' or self.path == '':
            self.path = '/templates/index.html'
        
        # 处理静态文件路径
        elif self.path.startswith('/static/'):
            # 静态文件直接访问
            pass
        
        # 处理其他路径
        elif self.path.startswith('/js/'):
            # JS文件
            pass
        elif self.path.startswith('/css/'):
            # CSS文件
            pass
        elif self.path.startswith('/images/'):
            # 图片文件
            pass
        
        # 如果文件不存在，尝试在正确目录中查找
        file_path = os.path.join(DIRECTORY, self.path.lstrip('/'))
        if not os.path.exists(file_path):
            # 尝试在static目录中查找
            if original_path.startswith('/static/'):
                static_path = original_path[7:]
                self.path = static_path
            elif original_path.startswith('/js/'):
                self.path = '/static' + original_path
            elif original_path.startswith('/css/'):
                self.path = '/static' + original_path
            elif original_path.startswith('/images/'):
                self.path = '/static' + original_path
        
        return super().do_GET()
    
    def end_headers(self):
        # 添加CORS头
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    print(f"🚀 启动量化监控系统Web服务器...")
    print(f"📁 目录: {DIRECTORY}")
    print(f"🌐 访问地址: http://localhost:{PORT}")
    print(f"📊 监控界面: http://localhost:{PORT}/")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 启动服务器时出错: {e}")
        sys.exit(1)