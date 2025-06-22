# 🔐 WOL远程控制系统

一个基于Web的远程Windows主机电源管理解决方案，支持网络唤醒(WOL)和远程睡眠功能，集成生物识别认证、内网自动认证和多层安全保护。

A web-based remote Windows host power management solution that supports Wake-on-LAN (WOL) and remote sleep functions, integrated with biometric authentication, local network auto-authentication and multi-layer security protection.

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com)
[![WebAuthn](https://img.shields.io/badge/WebAuthn-Supported-orange.svg)](https://webauthn.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 功能特性

### 🔒 智能认证系统
- **内网自动认证** - 当客户端IP与指定域名解析IP匹配时，自动跳过生物识别直接进入控制面板
- **生物识别认证** - 支持指纹、面部识别、PIN等WebAuthn认证方式
- **双重检测机制** - 结合服务器端IP检测和WebRTC客户端IP获取，提供快速准确的网络环境判断
- **会话管理** - 自动超时保护，防止未授权访问
- **多层安全** - CSRF保护、XSS防护、安全HTTP头
- **用户管理** - 支持多用户注册和认证

### 🌐 网络智能检测
- **DNS缓存机制** - 5分钟DNS解析缓存，提升检测速度
- **并行检测** - 前端WebRTC和服务器端检测并行执行，减少等待时间
- **HTTP头解析** - 支持多种代理环境下的真实IP获取（X-Forwarded-For、X-Real-IP等）
- **状态优化** - 优化前端状态管理，避免认证界面闪烁

### 🚀 远程唤醒 (Wake-on-LAN)
- 通过Magic Packet技术远程唤醒Windows主机
- 支持IPv4/IPv6双栈网络环境
- 实时监控主机启动状态

### 😴 远程睡眠
- 使用优化的PowerShell方法进入真正的睡眠模式（非休眠）
- 无需修改系统休眠设置
- 通过SSH安全连接执行睡眠命令

### 🌐 Web界面
- 现代化的响应式设计
- 实时状态监控和用户信息展示
- 移动设备友好的交互界面
- 会话超时倒计时显示

### 🔧 架构特点
- 三层架构：云服务器 ↔ Ubuntu服务器 ↔ Windows主机
- 智能认证：内网环境自动跳过生物识别，远程访问安全认证
- 配置文件驱动：支持通过JSON配置文件管理系统参数
- 多重检测机制：SSH、TCP端口、ICMP ping
- 容错处理和自动重试
- 生产级优化：日志记录、错误处理、安全配置
- 前端优化：WebRTC并行检测、Promise优化、状态管理

## 🏗️ 系统架构

```
┌─────────────────────┐    HTTPS/IPv6   ┌─────────────────────┐    内网LAN    ┌─────────────────────┐
│   云服务器           │ ◄─────────────►  │  Ubuntu服务器        │ ◄───────────► │   Windows主机        │
│  生物识别认证        │                 │   中继服务           │               │   目标设备           │
│  Flask + WebAuthn   │                 │  Flask + WOL        │               │ SSH + PowerShell    │
│  配置文件管理        │                 │  JSON配置           │               │ 网络唔醒功能         │
└─────────────────────┘                 └─────────────────────┘               └─────────────────────┘
```

### 版本说明

项目包含两个主要版本：

#### 🔒 生产优化版本 (`cloud_server_production_optimized.py`)
- **智能认证系统**：内网自动认证 + 生物识别认证双重模式
- **网络环境检测**：自动识别内网/外网环境，内网访问跳过生物识别
- **WebRTC集成**：客户端真实IP获取，提升检测准确性
- **生物识别认证**：支持WebAuthn标准的多种认证方式
- **高级安全特性**：会话管理、CSRF保护、安全HTTP头
- **配置文件支持**：通过JSON文件管理所有配置参数
- **完整日志记录**：详细的操作日志和错误追踪，简洁直观的日志输出
- **生产级优化**：错误处理、备份机制、自动清理、前端状态优化

#### 🚀 基础版本 (`cloud_server.py`)
- **简单易用**：快速部署的基础WOL功能
- **配置文件支持**：同样支持JSON配置管理
- **核心功能**：包含所有基本的唤醒和睡眠操作

## 📋 系统要求

### 云服务器
- Python 3.7+
- Flask 2.0+
- 公网IPv6地址
- 端口80/443开放（支持HTTPS）
- 支持WebAuthn的现代浏览器

### Ubuntu服务器  
- Ubuntu 18.04+
- Python 3.7+
- IPv6网络连接
- 与Windows主机在同一内网
- 端口5000开放

### Windows主机
- Windows 10/11
- 启用网络唤醒功能
- OpenSSH Server已安装并启动
- 网卡支持WOL功能

### 浏览器支持
- Chrome 67+
- Firefox 60+
- Safari 14+
- Edge 18+

## 🚀 快速开始

### 方式一：生产环境部署（推荐）

使用生物识别认证的安全版本，适合生产环境使用。

#### 1. 克隆项目
```bash
git clone https://github.com/Gofoyi/Wol.git
cd Wol
```

#### 2. 配置云服务器（生产版本）

```bash
# 安装依赖
pip3 install flask requests

# 进入云服务器目录
cd cloud/

# 创建配置文件
cp config.json.template config.json
nano config.json
```

编辑 `config.json` 文件：
```json
{
    "ubuntu_server_host": "your-ubuntu-server.example.com",
    "ubuntu_port": 5000,
    "windows_mac": "AA:BB:CC:DD:EE:FF"
}
```

**重要说明：**
- `ubuntu_server_host`: 同时用作Ubuntu服务器地址和内网自动认证的域名
- 当客户端IP与该域名解析的IPv4地址匹配时，系统将自动跳过生物识别认证
- 远程访问时仍需要生物识别认证以确保安全

#### 3. 启动生产版本服务
```bash
python3 cloud_server_production_optimized.py
```

#### 4. 首次使用
1. 访问 `https://your-domain.com`
2. **内网访问**：系统自动检测到内网环境，直接进入控制面板
3. **远程访问**：点击"注册生物识别"按钮，完成生物识别注册
4. 后续远程访问使用生物识别登录并控制设备

### 认证流程说明

#### 🏠 内网访问 (自动认证)
- 系统检测客户端IP与配置域名解析IP是否匹配
- 匹配成功：自动跳过生物识别，直接进入控制面板
- 显示"本地用户"身份，认证方式为"IP认证"

#### 🌍 远程访问 (生物识别)
- IP不匹配时要求进行生物识别认证
- 支持指纹、面部识别、PIN等多种方式
- 认证成功后显示注册的用户名和"生物识别"认证方式

### 方式二：快速部署（基础版本）

使用基础版本快速体验WOL功能。

### 方式二：快速部署（基础版本）

使用基础版本快速体验WOL功能。

#### 1. 配置云服务器（基础版本）
```bash
# 进入云服务器目录
cd cloud/

# 创建配置文件
cp config.json.template config.json
nano config.json
```

#### 2. 启动基础版本服务
```bash
python3 cloud_server.py
```

### 共同配置步骤

#### 3. 配置Ubuntu服务器

#### 安装OpenSSH Server
```powershell
# 以管理员身份运行PowerShell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# 配置防火墙
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

#### 获取MAC地址
```powershell
Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Select-Object Name, InterfaceDescription, MacAddress
```

### 3. 配置Ubuntu服务器

#### 3. 配置Ubuntu服务器

##### 安装依赖
```bash
sudo apt update
sudo apt install -y python3 python3-pip iputils-ping
pip3 install flask requests paramiko
```

##### 配置服务
```bash
# 进入Ubuntu服务器目录
cd lan/

# 创建配置文件
cp config.json.template config.json
nano config.json
```

编辑 `lan/config.json` 文件：
```json
{
    "windows_host_ip": "192.168.1.100",
    "windows_ssh_user": "your_username", 
    "windows_ssh_password": "your_password",
    "windows_ssh_port": 22
}
```

##### 启动Ubuntu服务器
```bash
python3 wol.py
```

#### 4. 配置Windows主机

##### 安装OpenSSH Server
```powershell
# 以管理员身份运行PowerShell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# 配置防火墙
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

##### 获取MAC地址
```powershell
Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Select-Object Name, InterfaceDescription, MacAddress
```

## 🔒 智能认证系统使用指南

### 认证模式

#### 🏠 内网自动认证
当满足以下条件时，系统自动跳过生物识别：
- 客户端IP与配置文件中`ubuntu_server_host`域名解析的IPv4地址匹配
- 系统将显示"检测到本地网络访问，正在自动登录..."
- 直接进入控制面板，显示为"本地用户"

**技术实现：**
- 服务器端HTTP头检测（X-Forwarded-For、X-Real-IP等）
- 客户端WebRTC真实IP获取
- DNS解析缓存机制（5分钟TTL）
- 并行检测优化，减少等待时间

#### 🌍 远程生物识别认证
当IP不匹配或检测失败时：
- 要求进行标准生物识别认证流程
- 支持多种WebAuthn认证方式
- 5分钟会话超时保护

### 支持的认证方式
- **指纹识别**：Windows Hello、Touch ID等
- **面部识别**：Windows Hello Face、Face ID等  
- **PIN码**：设备PIN、生物识别PIN
- **硬件密钥**：YubiKey、其他FIDO2设备

### 安全特性
- **WebAuthn标准**：符合W3C WebAuthn规范
- **本地存储**：生物识别数据不离开设备
- **会话管理**：5分钟自动超时保护
- **多用户支持**：支持多个用户独立注册

### 使用流程

#### 内网访问流程
1. **自动检测阶段**：
   - 系统显示"正在检测网络环境..."
   - 并行执行快速IP检查和WebRTC检测
   - 通常在1-2秒内完成检测

2. **自动登录阶段**：
   - 检测到内网环境：显示"检测到本地网络访问，正在自动登录..."
   - 自动跳转到控制面板
   - 会话5分钟自动超时，超时后重新检测

#### 远程访问流程
1. **注册阶段**：
   - 检测到远程环境后显示认证界面
   - 首次使用：点击"注册生物识别"
   - 输入用户名并完成生物识别设置

2. **认证阶段**：
   - 输入用户名，点击"生物识别登录"
   - 使用注册的生物识别方式认证

3. **使用阶段**：
   - 认证成功后可以控制设备
   - 会话5分钟自动超时
   - 超时后需要重新认证

## ⚙️ 配置详解

### 配置文件结构

项目使用JSON配置文件管理系统参数，支持两个配置文件：

#### 云服务器配置 (`cloud/config.json`)
```json
{
    "ubuntu_server_host": "your-ubuntu-server.example.com",
    "ubuntu_port": 5000,
    "windows_mac": "AA:BB:CC:DD:EE:FF"
}
```

**配置说明：**
- `ubuntu_server_host`: Ubuntu服务器的域名或IP地址
  - **重要**: 此域名同时用于内网自动认证功能
  - 当客户端IP与此域名解析IP匹配时，自动跳过生物识别
- `ubuntu_port`: Ubuntu服务器端口（默认5000）
- `windows_mac`: 目标Windows主机的MAC地址（用于WOL）

#### Ubuntu服务器配置 (`lan/config.json`)
```json
{
    "windows_host_ip": "192.168.1.100",
    "windows_ssh_user": "your_username",
    "windows_ssh_password": "your_password", 
    "windows_ssh_port": 22
}
```

### 环境变量配置

生产版本支持环境变量配置：

```bash
# 设置加密密钥（推荐）
export SECRET_KEY="your-secret-key-here"

# Ubuntu服务器端口（可选）
export UBUNTU_PORT="5000"
```

### Windows主机配置

1. **网络适配器设置**
   ```
   设备管理器 → 网络适配器 → 属性 → 电源管理
   ✅ 允许此设备唤醒计算机
   ✅ 只允许幻数据包唤醒计算机
   ```

2. **BIOS设置**
   ```
   启用 Wake-on-LAN
   启用 PCI设备唤醒
   ```

3. **电源设置**
   ```powershell
   # 快速启动设置
   powercfg /hibernate off  # 可选：禁用休眠以确保纯睡眠模式
   
   # 网络适配器电源管理
   powercfg /devicedisablewake "网络适配器名称"  # 如需禁用特定设备唤醒
   ```

### Ubuntu服务器配置

1. **网络配置与要求**
   - 公网ipv6地址
   - 端口5000开放
   ```bash
   # 确保IPv6连接正常
   ping6 -c 3 2001:4860:4860::8888
   
   # 检查防火墙设置
   sudo ufw status
   sudo ufw allow 5000/tcp  # 如需要
   ```

2. **服务状态检查**
   ```bash
   # 检查服务状态
   sudo systemctl status wol-server
   
   # 查看日志
   sudo journalctl -u wol-server -f
   
   # 重启服务
   sudo systemctl restart wol-server
   ```

### 云服务器配置

1. **网络要求**
   - 公网IPv4地址与公网ipv6地址
   - 端口80开放
   - 与Ubuntu服务器IPv6连通

2. **SSL配置（可选）**
   ```nginx
   # Nginx反向代理配置示例
   server {
       listen 443 ssl;
       server_name your-domain.com;
       
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       
       location / {
           proxy_pass http://127.0.0.1:80;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```


## 🚀 运行程序

### 1. 启动Ubuntu服务器

```bash
cd lan/
python3 wol.py
```
服务运行在 `http://[::]:5000` (支持内网IPv4和外网IPv6)

### 2. 启动云服务器

```bash
cd cloud/
python3 cloud_server_production_optimized.py
```



服务运行在 `http://127.0.0.1:5000`

## 🌐 访问Web界面

### 生产版本
1. 打开浏览器访问云服务器地址
2. 首次访问需要注册生物识别
3. 后续访问使用生物识别登录
4. 登录后可以看到设备控制面板

### 基础版本
直接访问云服务器地址，立即使用WOL功能。

## 📁 项目结构

```
Wol/
├── README.md                               # 项目说明文档
├── LICENSE                                 # 开源协议
├── cloud/                                  # 云服务器代码
│   ├── cloud_server_production_optimized.py # 生产优化版本
│   ├── config.json.template                # 配置文件模板
│   ├── config.json                         # 实际配置文件
│   ├── wol.log                            # 日志文件
│   └── templates/                          # 网页模板
│       ├── biometric_auth.html            # 生物识别认证页面
│       └── dashboard.html                  # 控制面板页面
├── lan/                                    # Ubuntu服务器代码
│   ├── wol.py                             # Ubuntu服务器程序
│   ├── config.json.template               # 配置文件模板
│   ├── config.json                        # 实际配置文件
│   ├── wol.out.log                        # 输出日志
│   └── wol.err.log                        # 错误日志
```

## 🔧 故障排除

### 生物识别认证问题

#### 1. 浏览器不支持WebAuthn
**错误现象：** 生物识别按钮无响应或提示不支持

**解决方案：**
- 使用支持WebAuthn的现代浏览器（Chrome 67+、Firefox 60+等）
- 确保浏览器已更新到最新版本
- 检查浏览器是否启用了WebAuthn功能

#### 2. 生物识别注册失败
**错误现象：** 注册过程中断或提示失败

**解决方案：**
- 确保设备支持生物识别功能
- 检查Windows Hello或Touch ID是否已设置
- 尝试使用不同的认证方式（指纹、面部、PIN）

#### 3. 会话频繁超时
**错误现象：** 5分钟内频繁要求重新认证

**解决方案：**
- 检查系统时间是否正确
- 确认浏览器cookie设置正常
- 查看服务器日志确认会话管理是否正常

### 配置文件问题

#### 1. 配置文件不存在
**错误现象：** 启动时提示"config.json 文件不存在"

**解决方案：**
```bash
# 复制配置模板
cp config.json.template config.json
# 编辑配置文件
nano config.json
```

#### 2. 配置文件格式错误
**错误现象：** JSON解析失败

**解决方案：**
- 检查JSON语法是否正确
- 确认所有字符串都用双引号包围
- 验证文件编码为UTF-8

### 网络连接问题

#### 1. Windows主机无法唤醒
```bash
# 检查Magic Packet发送
sudo tcpdump -i any port 9 -v

# 测试网络连通性
ping 192.168.1.100
```

**解决方案：**
- 检查网卡WOL设置
- 确认BIOS中WOL已启用
- 检查Windows电源计划设置

#### 2. SSH连接失败
```bash
# 测试SSH连接
ssh username@192.168.1.100

# 检查SSH服务状态
ssh username@192.168.1.100 "Get-Service sshd"
```

**解决方案：**
- 确认OpenSSH Server已安装并启动
- 检查Windows防火墙设置
- 验证用户名密码正确

#### 3. 睡眠命令不生效
```powershell
# 测试PowerShell命令
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $false, $false)
```

**解决方案：**
- 检查用户权限
- 确认电源计划允许睡眠
- 尝试禁用快速启动

## 📈 性能优化建议

### 生产环境部署

#### 1. 使用HTTPS
```nginx
# Nginx反向代理配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 2. 使用系统服务
创建systemd服务文件：
```ini
# /etc/systemd/system/wol-cloud.service
[Unit]
Description=WOL Cloud Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/wol/cloud
ExecStart=/usr/bin/python3 cloud_server_production_optimized.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable wol-cloud
sudo systemctl start wol-cloud
```

#### 3. 日志管理
```bash
# 设置日志轮转
sudo nano /etc/logrotate.d/wol
```

#### 4. 安全强化
- 定期更新系统和依赖包
- 使用强密码和密钥
- 限制SSH访问IP范围
- 启用防火墙规则

## 🔍 API 文档

### 生产版本API

#### 智能认证相关
- `GET /quick_ip_check` - 快速IP检查（服务器端检测）
- `POST /check_ip_bypass` - 检查IP是否可跳过生物验证（支持WebRTC IP）
- `POST /register/begin` - 开始生物识别注册
- `POST /register/complete` - 完成生物识别注册  
- `POST /authenticate/begin` - 开始生物识别认证
- `POST /authenticate/complete` - 完成生物识别认证
- `POST /logout` - 用户登出
- `GET /user_info` - 获取用户信息

#### 设备控制
- `POST /wake` - 唤醒Windows主机
- `POST /sleep` - 使Windows主机睡眠
- `GET /status` - 检查Ubuntu服务器状态
- `GET /win_status` - 获取Windows主机状态

### 新增API详解

#### IP检测API
```http
GET /quick_ip_check
响应：
{
  "success": true,
  "likely_local": false,
  "detected_ip": "1.2.3.4",
  "domain_ip": "1.2.3.5",
  "can_bypass": false
}
```

```http
POST /check_ip_bypass
请求：{"client_ip": "1.2.3.4"}
响应：
{
  "success": true,
  "bypass": true,
  "message": "IP匹配，跳过生物验证",
  "redirect": "/"
}
```

### Ubuntu服务器API
- `POST /wake` - 发送Magic包唤醒设备
- `POST /sleep` - 通过SSH使设备睡眠
- `GET /health` - 服务器健康检查
- `GET /win_status` - Windows主机状态检测

## 🆕 更新日志

### v2.0.0 - 智能认证系统 (2025-06-22)
#### 🎉 重大功能更新
- **内网自动认证**: 新增基于IP匹配的内网自动认证功能
- **智能网络检测**: 集成WebRTC和服务器端双重IP检测机制
- **并行优化**: 前端检测流程并行执行，大幅提升响应速度

#### 🔧 技术改进
- **DNS缓存**: 新增5分钟DNS解析缓存，提升检测效率
- **HTTP头解析**: 支持多种代理环境下的真实IP获取
- **状态管理优化**: 修复前端认证界面闪烁问题
- **日志优化**: 简化日志输出，提供更直观的状态信息

#### 🚀 性能提升
- **检测速度**: 内网检测时间从3-5秒优化到1-2秒
- **用户体验**: 自动检测网络环境，无需手动选择认证方式
- **前端优化**: Promise并行执行，减少等待时间

#### 🛠️ Bug修复
- 修复首次访问时检测不准确的问题
- 修复反向代理环境下IP获取错误
- 修复前端状态切换导致的界面闪烁
- 优化WebRTC检测的稳定性

#### 📝 API更新
- 新增 `GET /quick_ip_check` 快速IP检测接口
- 新增 `POST /check_ip_bypass` IP认证绕过接口
- 优化现有认证接口的错误处理

### v1.0.0 - 基础版本
- 基础WOL远程唤醒功能
- 生物识别认证系统
- Ubuntu中继服务器
- 基本的Web控制界面

### v2.0.0 (2025-06-22)
- ✨ **新增生物识别认证**：支持WebAuthn标准的多种认证方式
- 🔒 **增强安全性**：添加会话管理、CSRF保护、XSS防护
- 📁 **配置文件支持**：统一使用JSON配置文件管理参数
- 🎨 **界面优化**：全新的认证界面和控制面板设计
- 📊 **日志系统**：完整的日志记录和错误追踪
- 👥 **多用户支持**：支持多个用户独立注册和认证
- 🔧 **生产级优化**：错误处理、备份机制、自动清理

### v1.0.0 (2025)
- 🚀 基础WOL功能实现
- 😴 远程睡眠功能
- 🌐 简单的Web界面
- 🏗️ 三层架构设计

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！


## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- **Flask** - 优秀的Python Web框架
- **WebAuthn** - 现代化的认证标准
- **所有贡献者** - 感谢所有为这个项目做出贡献的开发者

## 📞 联系方式

- **项目作者**: [Gofoyi](https://github.com/Gofoyi)  
- **项目地址**: [https://github.com/Gofoyi/Wol](https://github.com/Gofoyi/Wol)
- **问题报告**: [GitHub Issues](https://github.com/Gofoyi/Wol/issues)

---

⭐ 如果这个项目对你有帮助，请给个星标支持一下！
