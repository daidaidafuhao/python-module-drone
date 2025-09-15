#!/bin/bash
# 生产环境启动脚本
# 用于在云服务器上启动无人机柜控制系统

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查Python虚拟环境
check_venv() {
    if [ ! -d "venv" ]; then
        log_error "Python虚拟环境不存在，请先运行部署脚本"
        exit 1
    fi
}

# 激活虚拟环境
activate_venv() {
    log_info "激活Python虚拟环境..."
    source venv/bin/activate
}

# 检查依赖
check_dependencies() {
    log_info "检查Python依赖..."
    pip check || {
        log_warn "发现依赖问题，尝试修复..."
        pip install -r requirements.txt
    }
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."
    
    if [ ! -f "production_config.py" ]; then
        log_error "生产环境配置文件不存在"
        exit 1
    fi
    
    # 检查环境变量
    python3 -c "from production_config import config; config.validate_config()" || {
        log_warn "配置验证失败，请检查环境变量设置"
    }
}

# 检查数据库连接
check_database() {
    log_info "检查数据库连接..."
    python3 -c "
import mysql.connector
from production_config import config
try:
    conn = mysql.connector.connect(**config.DATABASE_CONFIG)
    conn.close()
    print('数据库连接正常')
except Exception as e:
    print(f'数据库连接失败: {e}')
    exit(1)
" || {
        log_error "数据库连接失败"
        exit 1
    }
}

# 创建必要目录
setup_directories() {
    log_info "创建必要目录..."
    mkdir -p logs
    mkdir -p temp
}

# 启动应用
start_application() {
    log_info "启动无人机柜控制系统..."
    
    # 设置环境变量
    export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
    export FLASK_ENV=production
    export FLASK_DEBUG=False
    
    # 启动应用
    python3 deploy.py
}

# 主函数
main() {
    log_info "开始启动无人机柜控制系统..."
    
    check_venv
    activate_venv
    check_dependencies
    check_config
    check_database
    setup_directories
    start_application
}

# 信号处理
trap 'log_info "收到停止信号，正在关闭应用..."; exit 0' SIGTERM SIGINT

# 执行主函数
main "$@"