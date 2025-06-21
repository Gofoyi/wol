#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
import requests
import json
import sys
import os

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
UBUNTU_SERVER_HOST = config['ubuntu_server_host']
UBUNTU_PORT = config['ubuntu_port']
WINDOWS_MAC = config['windows_mac']

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/wake', methods=['POST'])
def wake_windows():
    """唤醒Windows主机"""
    try:
        # 向Ubuntu服务器发送唤醒请求
        url = f"http://{UBUNTU_SERVER_HOST}:{UBUNTU_PORT}/wake"
        payload = {"mac_address": WINDOWS_MAC}
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "message": f"Ubuntu server returned status {response.status_code}"
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "message": "Timeout connecting to Ubuntu server"
        }), 500
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "message": "Cannot connect to Ubuntu server"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/sleep', methods=['POST'])
def sleep_windows():
    """使Windows主机进入睡眠状态"""
    try:
        url = f"http://{UBUNTU_SERVER_HOST}:{UBUNTU_PORT}/sleep"
        
        response = requests.post(url, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "message": f"Ubuntu server returned status {response.status_code}"
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "message": "Timeout connecting to Ubuntu server"
        }), 500
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "message": "Cannot connect to Ubuntu server"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/status', methods=['GET'])
def check_status():
    """检查Ubuntu服务器状态"""
    try:
        url = f"http://{UBUNTU_SERVER_HOST}:{UBUNTU_PORT}/health"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return jsonify({"ubuntu_server": "online"})
        else:
            return jsonify({"ubuntu_server": "error"})
    except:
        return jsonify({"ubuntu_server": "offline"})

@app.route('/win_status', methods=['GET'])
def win_status():
    """获取Windows主机状态（通过Ubuntu服务器转发）"""
    try:
        url = f"http://{UBUNTU_SERVER_HOST}:{UBUNTU_PORT}/win_status"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"online": False})
    except:
        return jsonify({"online": False})

if __name__ == '__main__':
    # 在IPv4和IPv6上都监听
    app.run(host='0.0.0.0', port=80, debug=False)
