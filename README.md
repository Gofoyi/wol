# 🔐 WOL远程控制系统

一个基于Web的远程Windows主机电源管理解决方案，支持网络唤醒(WOL)和远程睡眠功能，集成智能认证系统。

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com)
[![WebAuthn](https://img.shields.io/badge/WebAuthn-Supported-orange.svg)](https://webauthn.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 核心功能

### 🔒 智能认证系统
- **内网自动认证** - IP匹配时自动跳过生物识别认证
- **生物识别认证** - 支持WebAuthn标准的指纹、面部识别等
- **会话管理** - 5分钟自动超时保护
- **多重安全** - CSRF保护、XSS防护、安全HTTP头

### 🚀 设备控制
- **远程唤醒** - 通过Magic Packet技术唤醒Windows主机
- **远程睡眠** - 使用SSH + PowerShell安全执行睡眠命令
- **状态监控** - 实时检查主机在线状态

### 🌐 Web界面
- 现代化响应式设计
- 移动设备友好
- 实时状态显示

## 🏗️ 系统架构

```
┌─────────────────────┐    HTTPS/IPv6   ┌─────────────────────┐    内网LAN    ┌─────────────────────┐
│   云服务器           │ ◄─────────────►  │  Ubuntu服务器        │ ◄───────────► │   Windows主机        │
│  智能认证系统        │                 │   中继服务           │               │   目标设备           │
│  Flask + WebAuthn   │                 │  Flask + WOL        │               │ SSH + PowerShell    │
└─────────────────────┘                 └─────────────────────┘               └─────────────────────┘
```

## 📋 系统要求

### 云服务器
- Python 3.7+、Flask 2.0+
- 公网IPv6地址、端口80/443开放
- 支持WebAuthn的现代浏览器

### Ubuntu服务器  
- Ubuntu 18.04+、Python 3.7+
- IPv6网络连接、端口5000开放
- 与Windows主机在同一内网

### Windows主机
- Windows 10/11
- 启用网络唤醒功能、OpenSSH Server
- 网卡支持WOL功能

## 🚀 快速部署

### 1. 克隆项目
```bash
git clone https://github.com/Gofoyi/wol.git
cd wol
```

### 2. 配置云服务器
```bash
# 安装依赖
pip3 install flask requests

# 配置文件
cd cloud/
cp config.json.template config.json
nano config.json
```

编辑配置文件：
```json
{
    "ubuntu_server_host": "your-ubuntu-server.example.com",
    "ubuntu_port": 5000,
    "windows_mac": "AA:BB:CC:DD:EE:FF",
    "bypass_domain": "your-ubuntu-server.example.com"
}
```

**重要说明**：`bypass_domain` 用于内网自动认证，当客户端IP与该域名解析IP匹配时自动跳过生物识别。

### 3. 配置Ubuntu服务器
```bash
# 安装依赖
sudo apt update
sudo apt install -y python3 python3-pip iputils-ping
pip3 install flask requests paramiko

# 配置文件
cd lan/
cp config.json.template config.json
nano config.json
```

编辑配置文件：
```json
{
    "windows_host_ip": "192.168.1.100",
    "windows_ssh_user": "your_username", 
    "windows_ssh_password": "your_password",
    "windows_ssh_port": 22
}
```

### 4. 配置Windows主机

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

#### 启用网络唤醒
- 设备管理器 → 网络适配器 → 属性 → 电源管理
- ✅ 允许此设备唤醒计算机
- ✅ 只允许幻数据包唤醒计算机

### 5. 启动服务
```bash
# Ubuntu服务器
cd lan/
python3 wol.py

# 云服务器
cd cloud/
python3 cloud_server_production_optimized.py
```

## 🔒 认证系统使用

### 内网访问（自动认证）
- 系统自动检测IP环境
- IP匹配时自动跳过生物识别
- 显示"本地用户"身份

### 远程访问（生物识别）
1. **首次访问**：点击"注册生物识别"
2. **后续访问**：使用生物识别登录
3. **支持方式**：指纹、面部识别、PIN、硬件密钥

## 📁 项目结构

```
wol/
├── cloud/                                  # 云服务器代码
│   ├── cloud_server_production_optimized.py # 主服务程序
│   ├── config.json.template                # 配置模板
│   └── templates/                          # 网页模板
├── lan/                                    # Ubuntu服务器代码
│   ├── wol.py                             # 中继服务程序
│   └── config.json.template               # 配置模板
└── README.md                              # 项目文档
```

## 🔧 故障排除

### 常见问题

#### Windows主机无法唤醒
- 检查网卡WOL设置
- 确认BIOS中WOL已启用
- 验证MAC地址正确

#### SSH连接失败
- 确认OpenSSH Server已启动
- 检查防火墙设置
- 验证用户名密码

#### 生物识别注册失败
- 使用支持WebAuthn的浏览器
- 确保设备支持生物识别
- 检查Windows Hello设置

### 日志查看
```bash
# 云服务器日志
tail -f cloud/wol.log

# Ubuntu服务器日志  
tail -f lan/wol.out.log
```

## 🆕 版本特性

### v2.0.0 - 智能认证系统
- ✨ 内网自动认证功能
- 🔒 WebAuthn生物识别认证
- 🚀 网络环境智能检测
- 📊 完整日志系统
- 🎨 优化的用户界面

### v1.0.0 - 基础版本
- 🚀 基础WOL功能
- 😴 远程睡眠功能
- 🌐 简单Web界面

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- **项目作者**: [Gofoyi](https://github.com/Gofoyi)  
- **项目地址**: [https://github.com/Gofoyi/wol](https://github.com/Gofoyi/wol)
- **问题报告**: [GitHub Issues](https://github.com/Gofoyi/wol/issues)

---

⭐ 如果这个项目对你有帮助，请给个星标支持一下！
