# -*- coding: utf-8 -*-
"""
Gunicorn配置文件
用于生产环境的WSGI服务器配置
"""

import os
import multiprocessing

# 服务器配置
bind = "0.0.0.0:5000"
backlog = 2048

# Worker配置
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# 超时配置
timeout = 30
keepalive = 2
graceful_timeout = 30

# 日志配置
accesslog = "/opt/drone-cabinet/logs/gunicorn-access.log"
errorlog = "/opt/drone-cabinet/logs/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程配置
user = "www-data"
group = "www-data"
tmp_upload_dir = None

# 安全配置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 性能配置
max_requests_jitter = 50
worker_tmp_dir = "/dev/shm"

# 环境变量
raw_env = [
    'PYTHONPATH=/opt/drone-cabinet',
    'FLASK_ENV=production',
    'FLASK_DEBUG=False'
]

# 钩子函数
def on_starting(server):
    """服务器启动时调用"""
    server.log.info("无人机柜控制系统正在启动...")

def on_reload(server):
    """重新加载时调用"""
    server.log.info("无人机柜控制系统正在重新加载...")

def when_ready(server):
    """服务器准备就绪时调用"""
    server.log.info("无人机柜控制系统已准备就绪")

def worker_int(worker):
    """Worker收到SIGINT信号时调用"""
    worker.log.info("Worker收到中断信号")

def pre_fork(server, worker):
    """Worker fork之前调用"""
    server.log.info(f"Worker {worker.pid} 正在启动")

def post_fork(server, worker):
    """Worker fork之后调用"""
    server.log.info(f"Worker {worker.pid} 已启动")

def post_worker_init(worker):
    """Worker初始化完成后调用"""
    worker.log.info(f"Worker {worker.pid} 初始化完成")

def worker_abort(worker):
    """Worker异常终止时调用"""
    worker.log.info(f"Worker {worker.pid} 异常终止")

def pre_exec(server):
    """执行新的二进制文件之前调用"""
    server.log.info("正在执行新的二进制文件")

def pre_request(worker, req):
    """处理请求之前调用"""
    worker.log.debug(f"处理请求: {req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """处理请求之后调用"""
    worker.log.debug(f"请求完成: {req.method} {req.path} - {resp.status_code}")

def child_exit(server, worker):
    """Worker退出时调用"""
    server.log.info(f"Worker {worker.pid} 已退出")

def worker_exit(server, worker):
    """Worker进程退出时调用"""
    server.log.info(f"Worker {worker.pid} 进程已退出")

def nworkers_changed(server, new_value, old_value):
    """Worker数量改变时调用"""
    server.log.info(f"Worker数量从 {old_value} 改变为 {new_value}")

def on_exit(server):
    """服务器退出时调用"""
    server.log.info("无人机柜控制系统正在关闭...")