#!/bin/bash
# 无人机柜控制系统部署脚本
# 适用于Ubuntu/Debian云服务器

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本"
        exit 1
    fi
}

# 更新系统包
update_system() {
    log_info "更新系统包..."
    sudo apt update
    sudo apt upgrade -y
}

# 安装依赖
install_dependencies() {
    log_info "安装系统依赖..."
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        mysql-server \
        git \
        supervisor \
        ufw
}

# 创建应用目录
setup_directories() {
    log_info "创建应用目录..."
    sudo mkdir -p /opt/drone-cabinet
    sudo chown $USER:$USER /opt/drone-cabinet
}

# 复制应用文件
copy_application() {
    log_info "复制应用文件..."
    cp -r . /opt/drone-cabinet/
    cd /opt/drone-cabinet
}

# 设置Python虚拟环境
setup_python_env() {
    log_info "设置Python虚拟环境..."
    cd /opt/drone-cabinet
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
}

# 配置数据库
setup_database() {
    log_info "配置MySQL数据库..."
    
    # 创建数据库和用户
    sudo mysql -e "CREATE DATABASE IF NOT EXISTS drone_cabinet CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    sudo mysql -e "CREATE USER IF NOT EXISTS 'drone_user'@'localhost' IDENTIFIED BY 'drone_password_123';"
    sudo mysql -e "GRANT ALL PRIVILEGES ON drone_cabinet.* TO 'drone_user'@'localhost';"
    sudo mysql -e "FLUSH PRIVILEGES;"
    
    # 导入数据库结构
    if [ -f "sql/drone_cabinet.sql" ]; then
        mysql -u drone_user -pdrone_password_123 drone_cabinet < sql/drone_cabinet.sql
    fi
    
    if [ -f "sql/machine_config.sql" ]; then
        mysql -u drone_user -pdrone_password_123 drone_cabinet < sql/machine_config.sql
    fi
}

# 配置Nginx
setup_nginx() {
    log_info "配置Nginx..."
    sudo cp nginx.conf /etc/nginx/sites-available/drone-cabinet
    sudo ln -sf /etc/nginx/sites-available/drone-cabinet /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # 测试配置
    sudo nginx -t
    sudo systemctl restart nginx
    sudo systemctl enable nginx
}

# 配置systemd服务
setup_systemd() {
    log_info "配置systemd服务..."
    sudo cp drone-cabinet.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable drone-cabinet
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    sudo ufw allow ssh
    sudo ufw allow 'Nginx Full'
    sudo ufw --force enable
}

# 设置日志轮转
setup_logrotate() {
    log_info "配置日志轮转..."
    sudo tee /etc/logrotate.d/drone-cabinet > /dev/null <<EOF
/opt/drone-cabinet/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload drone-cabinet
    endscript
}
EOF
}

# 启动服务
start_services() {
    log_info "启动服务..."
    sudo systemctl start drone-cabinet
    sudo systemctl status drone-cabinet --no-pager
}

# 显示部署信息
show_deployment_info() {
    log_info "部署完成！"
    echo ""
    echo "=== 部署信息 ==="
    echo "应用目录: /opt/drone-cabinet"
    echo "配置文件: /opt/drone-cabinet/production_config.py"
    echo "日志目录: /opt/drone-cabinet/logs"
    echo "服务名称: drone-cabinet"
    echo ""
    echo "=== 常用命令 ==="
    echo "查看服务状态: sudo systemctl status drone-cabinet"
    echo "重启服务: sudo systemctl restart drone-cabinet"
    echo "查看日志: sudo journalctl -u drone-cabinet -f"
    echo "查看应用日志: tail -f /opt/drone-cabinet/logs/production.log"
    echo ""
    echo "=== 重要提醒 ==="
    log_warn "请修改以下配置:"
    echo "1. 编辑 /etc/systemd/system/drone-cabinet.service 中的环境变量"
    echo "2. 修改 /etc/nginx/sites-available/drone-cabinet 中的域名"
    echo "3. 更改默认的数据库密码"
    echo "4. 设置强密码和API密钥"
}

# 主函数
main() {
    log_info "开始部署无人机柜控制系统..."
    
    check_root
    update_system
    install_dependencies
    setup_directories
    copy_application
    setup_python_env
    setup_database
    setup_nginx
    setup_systemd
    setup_firewall
    setup_logrotate
    start_services
    show_deployment_info
    
    log_info "部署脚本执行完成！"
}

# 执行主函数
main "$@"