# 无人机柜控制系统 - 云服务器部署指南

本指南将帮助您将无人机柜控制系统部署到云服务器上，不使用Docker。

## 系统要求

### 服务器配置
- **操作系统**: Ubuntu 20.04 LTS 或更高版本
- **CPU**: 2核心或以上
- **内存**: 4GB RAM 或以上
- **存储**: 20GB 可用空间或以上
- **网络**: 公网IP地址

### 软件依赖
- Python 3.8+
- MySQL 8.0+
- Nginx
- Systemd

## 快速部署

### 1. 准备服务器

```bash
# 连接到云服务器
ssh username@your-server-ip

# 创建部署用户（如果需要）
sudo adduser deploy
sudo usermod -aG sudo deploy
su - deploy
```

### 2. 上传项目文件

```bash
# 方法1: 使用scp上传
scp -r /path/to/project username@server-ip:/home/username/

# 方法2: 使用git克隆
git clone your-repository-url
cd your-project-directory
```

### 3. 执行自动部署脚本

```bash
# 给脚本执行权限
chmod +x deploy.sh

# 运行部署脚本
./deploy.sh
```

## 手动部署步骤

如果自动部署脚本遇到问题，可以按以下步骤手动部署：

### 1. 更新系统

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. 安装依赖

```bash
sudo apt install -y python3 python3-pip python3-venv nginx mysql-server git ufw
```

### 3. 配置MySQL

```bash
# 安全配置MySQL
sudo mysql_secure_installation

# 创建数据库和用户
sudo mysql -u root -p
```

```sql
CREATE DATABASE drone_cabinet CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'drone_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON drone_cabinet.* TO 'drone_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4. 设置应用目录

```bash
sudo mkdir -p /opt/drone-cabinet
sudo chown $USER:$USER /opt/drone-cabinet
cp -r . /opt/drone-cabinet/
cd /opt/drone-cabinet
```

### 5. 创建Python虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. 导入数据库结构

```bash
mysql -u drone_user -p drone_cabinet < sql/drone_cabinet.sql
mysql -u drone_user -p drone_cabinet < sql/machine_config.sql
```

### 7. 配置环境变量

编辑systemd服务文件：

```bash
sudo cp drone-cabinet.service /etc/systemd/system/
sudo nano /etc/systemd/system/drone-cabinet.service
```

修改以下环境变量：
```ini
Environment=SECRET_KEY=your-very-secure-secret-key
Environment=DB_PASSWORD=your_secure_password
Environment=API_KEY=your-api-key
Environment=MODBUS_HOST=your-modbus-device-ip
```

### 8. 配置Nginx

```bash
sudo cp nginx.conf /etc/nginx/sites-available/drone-cabinet
sudo ln -s /etc/nginx/sites-available/drone-cabinet /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# 修改域名配置
sudo nano /etc/nginx/sites-available/drone-cabinet
# 将 your-domain.com 替换为你的实际域名或IP

# 测试配置
sudo nginx -t
sudo systemctl restart nginx
```

### 9. 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable drone-cabinet
sudo systemctl start drone-cabinet
sudo systemctl enable nginx
```

### 10. 配置防火墙

```bash
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 配置说明

### 环境变量配置

在 `/etc/systemd/system/drone-cabinet.service` 中配置以下环境变量：

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| SECRET_KEY | Flask密钥 | your-very-secure-secret-key |
| DB_HOST | 数据库主机 | localhost |
| DB_USER | 数据库用户 | drone_user |
| DB_PASSWORD | 数据库密码 | your_secure_password |
| DB_NAME | 数据库名 | drone_cabinet |
| MODBUS_HOST | Modbus设备IP | 192.168.1.100 |
| MODBUS_PORT | Modbus端口 | 502 |
| API_KEY | API访问密钥 | your-api-key |
| HOST | 监听地址 | 0.0.0.0 |
| PORT | 监听端口 | 5000 |

### Nginx配置

编辑 `/etc/nginx/sites-available/drone-cabinet`：

1. 修改 `server_name` 为你的域名或IP地址
2. 如果需要HTTPS，取消注释SSL配置部分
3. 根据需要调整超时和缓存设置

## 服务管理

### 常用命令

```bash
# 查看服务状态
sudo systemctl status drone-cabinet

# 启动/停止/重启服务
sudo systemctl start drone-cabinet
sudo systemctl stop drone-cabinet
sudo systemctl restart drone-cabinet

# 查看服务日志
sudo journalctl -u drone-cabinet -f

# 查看应用日志
tail -f /opt/drone-cabinet/logs/production.log

# 重新加载配置
sudo systemctl daemon-reload
sudo systemctl restart drone-cabinet
```

### 日志文件位置

- 系统日志: `sudo journalctl -u drone-cabinet`
- 应用日志: `/opt/drone-cabinet/logs/production.log`
- Nginx访问日志: `/var/log/nginx/drone-cabinet-access.log`
- Nginx错误日志: `/var/log/nginx/drone-cabinet-error.log`

## 安全建议

### 1. 更改默认密码
- 数据库密码
- API密钥
- Flask密钥

### 2. 配置SSL/HTTPS

```bash
# 使用Let's Encrypt获取免费SSL证书
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. 定期更新

```bash
# 更新系统包
sudo apt update && sudo apt upgrade

# 更新Python依赖
cd /opt/drone-cabinet
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### 4. 备份策略

```bash
# 数据库备份
mysqldump -u drone_user -p drone_cabinet > backup_$(date +%Y%m%d).sql

# 应用文件备份
tar -czf drone-cabinet-backup-$(date +%Y%m%d).tar.gz /opt/drone-cabinet
```

## 故障排除

### 常见问题

1. **服务无法启动**
   ```bash
   sudo systemctl status drone-cabinet
   sudo journalctl -u drone-cabinet --no-pager
   ```

2. **数据库连接失败**
   - 检查数据库服务状态: `sudo systemctl status mysql`
   - 验证数据库用户权限
   - 检查防火墙设置

3. **Nginx 502错误**
   - 确认应用服务正在运行
   - 检查端口5000是否被占用: `sudo netstat -tlnp | grep 5000`

4. **权限问题**
   ```bash
   sudo chown -R www-data:www-data /opt/drone-cabinet/logs
   sudo chmod -R 755 /opt/drone-cabinet
   ```

### 性能优化

1. **调整Nginx配置**
   - 增加worker进程数
   - 调整缓存设置
   - 启用gzip压缩

2. **数据库优化**
   - 调整MySQL配置
   - 添加适当的索引
   - 定期清理日志

## 监控和维护

### 系统监控

```bash
# 查看系统资源使用
htop
df -h
free -h

# 查看网络连接
sudo netstat -tlnp
```

### 应用监控

- 访问 `http://your-domain.com/health` 检查应用健康状态
- 定期检查日志文件
- 监控数据库连接状态

## 联系支持

如果在部署过程中遇到问题，请：

1. 检查日志文件获取详细错误信息
2. 确认所有配置文件设置正确
3. 验证网络连接和防火墙设置
4. 联系技术支持团队

---

**注意**: 部署完成后，请及时更改所有默认密码和密钥，确保系统安全。