#!/usr/bin/env python3
import socket
import struct
import sys
import json
import paramiko
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# 读取配置文件
def load_config():
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(config_file):
        print("错误: config.json 文件不存在")
        print("请复制 config.json.template 为 config.json 并填入实际配置")
        print("Error: config.json file not found")
        print("Please copy config.json.template to config.json and fill in actual values")
        sys.exit(1)
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        print(f"Failed to read config file: {e}")
        sys.exit(1)

# 加载配置
config = load_config()
WINDOWS_HOST_IP = config['windows_host_ip']
WINDOWS_SSH_USER = config['windows_ssh_user']
WINDOWS_SSH_PASSWORD = config['windows_ssh_password']
WINDOWS_SSH_PORT = config['windows_ssh_port']

def send_magic_packet(mac_address, broadcast_ip='255.255.255.255', port=9):
    """发送Magic包唤醒设备"""
    # 移除MAC地址中的分隔符
    mac_address = mac_address.replace(':', '').replace('-', '')
    
    # 验证MAC地址格式
    if len(mac_address) != 12:
        return False, "Invalid MAC address format"
    
    try:
        # 创建Magic包
        # Magic包格式: 6个0xFF + 16次重复的MAC地址
        magic_packet = b'\xff' * 6
        mac_bytes = bytes.fromhex(mac_address)
        magic_packet += mac_bytes * 16
        
        # 发送UDP包
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast_ip, port))
        sock.close()
        
        return True, "Magic packet sent successfully"
    except Exception as e:
        return False, f"Error sending magic packet: {str(e)}"

def check_windows_status():
    """检查Windows主机是否在线"""
    try:
        import subprocess
        cmd = ['ping', '-c', '1', '-W', '1', WINDOWS_HOST_IP]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def sleep_windows_via_ssh():
    """通过SSH使Windows主机进入睡眠状态(使用优化的PowerShell命令)"""
    try:
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 连接到Windows主机
        ssh.connect(
            hostname=WINDOWS_HOST_IP,
            port=WINDOWS_SSH_PORT,
            username=WINDOWS_SSH_USER,
            password=WINDOWS_SSH_PASSWORD,
            timeout=10
        )
        
        # 使用您提供的优化命令：直接进入睡眠模式，无需禁用休眠
        # SetSuspendState参数说明:
        # - PowerState.Suspend: 睡眠模式
        # - $false: 不强制关闭应用程序
        # - $false: 允许唤醒事件
        powershell_sleep_cmd = '''powershell.exe -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $false, $false)"'''
        
        # 备用命令列表（按优先级排序）
        backup_commands = [
            # 备用方法1: 使用强制参数
            '''powershell.exe -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $true, $false)"''',
            # 备用方法2: 使用rundll32（如果PowerShell方法失败）
            'rundll32.exe powrprof.dll,SetSuspendState 0,1,0'
        ]
        
        try:
            # 首先尝试主要的睡眠命令
            stdin, stdout, stderr = ssh.exec_command(powershell_sleep_cmd, timeout=5)
            # 不等待命令完成，因为主机会立即进入睡眠
            ssh.close()
            return True, "Sleep command sent successfully."
            
        except Exception as e:
            # 如果主命令失败，尝试备用命令
            for i, backup_cmd in enumerate(backup_commands):
                try:
                    stdin, stdout, stderr = ssh.exec_command(backup_cmd, timeout=3)
                    ssh.close()
                    return True, f"Sleep command sent successfully (backup method {i+1})"
                except:
                    continue
            
            # 所有方法都失败
            ssh.close()
            return False, f"All sleep methods failed. Last error: {str(e)}"
        
    except paramiko.AuthenticationException:
        return False, "SSH authentication failed"
    except paramiko.SSHException as e:
        return False, f"SSH connection error: {str(e)}"
    except Exception as e:
        return False, f"Error sending sleep command: {str(e)}"

@app.route('/wake', methods=['POST'])
def wake_device():
    """接收来自云服务器的唤醒请求"""
    try:
        data = request.get_json()
        mac_address = data.get('mac_address')
        
        if not mac_address:
            return jsonify({"success": False, "message": "MAC address required"}), 400
        
        success, message = send_magic_packet(mac_address)
        
        return jsonify({
            "success": success,
            "message": message
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/sleep', methods=['POST'])
def sleep_device():
    """使Windows主机进入睡眠状态"""
    try:
        # 首先检查Windows主机是否在线
        if not check_windows_status():
            return jsonify({
                "success": False,
                "message": "Windows主机离线或无法访问"
            })
        
        success, message = sleep_windows_via_ssh()
        
        return jsonify({
            "success": success,
            "message": message
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({"status": "healthy"})

@app.route('/win_status', methods=['GET'])
def win_status():
    """获取Windows主机状态"""
    try:
        windows_online = check_windows_status()
        
        return jsonify({
            "win_status": "online" if windows_online else "offline"
        })
    except Exception as e:
        return jsonify({
            "win_status": "unknown",
            "error": str(e)
        })

if __name__ == '__main__':
    # 在IPv6地址上监听
    app.run(host='::', port=5000, debug=False)
