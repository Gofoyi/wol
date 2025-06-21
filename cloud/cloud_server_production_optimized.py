#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, session
import requests
import json
import os
import sys
import secrets
import base64
from functools import wraps
from datetime import datetime, timedelta
import logging

app = Flask(__name__)

# 读取配置文件
def load_config():
    """从配置文件加载配置"""
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(config_file):
        logger.error("错误: config.json 文件不存在")
        logger.error("请复制 config.json.template 为 config.json 并填入实际配置")
        print("错误: config.json 文件不存在")
        print("请复制 config.json.template 为 config.json 并填入实际配置")
        print("Error: config.json file not found")
        print("Please copy config.json.template to config.json and fill in actual values")
        sys.exit(1)
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            logger.info("配置文件加载成功")
            return config_data
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        print(f"读取配置文件失败: {e}")
        print(f"Failed to read config file: {e}")
        sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wol.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 加载配置
config = load_config()

# 设置密钥用于session加密
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# 安全配置
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # 防止XSS
    SESSION_COOKIE_SAMESITE='Strict', # CSRF保护
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=5)
)

# 从配置文件读取服务器配置
UBUNTU_SERVER_HOST = config['ubuntu_server_host']
UBUNTU_PORT = config['ubuntu_port']
WINDOWS_MAC = config['windows_mac']

# 存储文件路径
USER_CREDENTIALS_FILE = 'user_credentials.json'
CHALLENGES_FILE = 'challenges.json'

# 内存存储（临时挑战）
CHALLENGES = {}
SESSION_TIMEOUT = 300  # 5分钟会话超时

def load_user_credentials():
    """从文件加载用户凭据"""
    try:
        if os.path.exists(USER_CREDENTIALS_FILE):
            with open(USER_CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加载用户凭据失败: {e}")
    return {}

def save_user_credentials(credentials):
    """保存用户凭据到文件"""
    try:
        # 创建备份
        if os.path.exists(USER_CREDENTIALS_FILE):
            backup_file = f"{USER_CREDENTIALS_FILE}.backup"
            os.rename(USER_CREDENTIALS_FILE, backup_file)
        
        with open(USER_CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(credentials, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"用户凭据已保存，共 {len(credentials)} 个用户")
        return True
    except Exception as e:
        logger.error(f"保存用户凭据失败: {e}")
        # 恢复备份
        backup_file = f"{USER_CREDENTIALS_FILE}.backup"
        if os.path.exists(backup_file):
            os.rename(backup_file, USER_CREDENTIALS_FILE)
        return False

def clean_expired_challenges():
    """清理过期的挑战"""
    try:
        current_time = datetime.now()
        expired_users = []
        
        for username, challenge_data in CHALLENGES.items():
            if current_time - challenge_data['timestamp'] > timedelta(minutes=5):
                expired_users.append(username)
        
        for username in expired_users:
            del CHALLENGES[username]
            
        if expired_users:
            logger.info(f"清理了 {len(expired_users)} 个过期挑战")
            
    except Exception as e:
        logger.error(f"清理过期挑战失败: {e}")

def require_biometric_auth(f):
    """需要生物识别认证的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if ('biometric_authenticated' not in session or 
            not session['biometric_authenticated'] or
            'auth_time' not in session):
            logger.warning(f"未认证访问尝试: {request.remote_addr} -> {request.endpoint}")
            return jsonify({"error": "需要生物识别认证", "redirect": "/"}), 401
        
        try:
            auth_time = datetime.fromisoformat(session['auth_time'])
            if datetime.now() - auth_time > timedelta(seconds=SESSION_TIMEOUT):
                session.clear()
                logger.info(f"会话超时: {session.get('username', 'unknown')}")
                return jsonify({"error": "认证已超时，请重新进行生物识别", "redirect": "/"}), 401
        except ValueError:
            session.clear()
            logger.warning("无效的会话时间格式")
            return jsonify({"error": "会话数据无效", "redirect": "/"}), 401
        
        # 更新会话时间
        session['auth_time'] = datetime.now().isoformat()
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def before_request():
    """请求前处理"""
    # 定期清理过期挑战
    clean_expired_challenges()

@app.after_request
def after_request(response):
    """添加安全头"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # 只在HTTPS下设置HSTS
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    return response

@app.route('/')
def index():
    """主页面"""
    if (session.get('biometric_authenticated') and 'auth_time' in session):
        try:
            auth_time = datetime.fromisoformat(session['auth_time'])
            if datetime.now() - auth_time <= timedelta(seconds=SESSION_TIMEOUT):
                remaining_time = SESSION_TIMEOUT - int((datetime.now() - auth_time).total_seconds())
                return render_template('dashboard.html', 
                    session_timeout=remaining_time,
                    username=session.get('username', 'user'))
        except ValueError:
            pass
    
    session.clear()
    return render_template('biometric_auth.html')

@app.route('/register/begin', methods=['POST'])
def register_begin():
    """开始注册生物识别凭据"""
    try:
        username = request.json.get('username', 'wol_user')
        
        # 简单验证
        if not username or len(username.strip()) == 0:
            return jsonify({"error": "用户名不能为空"}), 400
        
        username = username.strip()
        
        challenge = secrets.token_bytes(32)
        challenge_b64 = base64.urlsafe_b64encode(challenge).decode('utf-8').rstrip('=')
        
        CHALLENGES[username] = {
            'challenge': challenge,
            'timestamp': datetime.now()
        }
        
        # 使用实际域名
        host = request.host.split(':')[0]
        if host in ['127.0.0.1', 'localhost']:
            host = 'wol.gofoyi.shop'
        
        options = {
            "challenge": challenge_b64,
            "rp": {
                "name": "WOL远程控制系统",
                "id": host
            },
            "user": {
                "id": base64.urlsafe_b64encode(username.encode()).decode('utf-8').rstrip('='),
                "name": username,
                "displayName": f"WOL用户-{username}"
            },
            "pubKeyCredParams": [
                {"alg": -7, "type": "public-key"},   # ES256
                {"alg": -257, "type": "public-key"}  # RS256
            ],
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "userVerification": "preferred",
                "requireResidentKey": False
            },
            "timeout": 60000,
            "attestation": "none"
        }
        
        logger.info(f"开始注册生物识别: {username} from {request.remote_addr}")
        return jsonify(options)
        
    except Exception as e:
        logger.error(f"注册初始化失败: {e}")
        return jsonify({"error": f"注册初始化失败: {str(e)}"}), 500

@app.route('/register/complete', methods=['POST'])
def register_complete():
    """完成注册生物识别凭据"""
    try:
        username = request.json.get('username', 'wol_user')
        credential = request.json.get('credential')
        
        if not username or not credential:
            return jsonify({"error": "缺少必要参数"}), 400
        
        username = username.strip()
        
        if username not in CHALLENGES:
            logger.warning(f"注册完成时未找到挑战: {username}")
            return jsonify({"error": "未找到挑战，请重新开始注册"}), 400
            
        challenge_data = CHALLENGES[username]
        if datetime.now() - challenge_data['timestamp'] > timedelta(minutes=5):
            del CHALLENGES[username]
            return jsonify({"error": "挑战已过期，请重新开始注册"}), 400
        
        # 加载现有凭据
        user_credentials = load_user_credentials()
        
        # 保存新凭据
        user_credentials[username] = {
            'id': credential['id'],
            'rawId': credential['rawId'],
            'response': credential['response'],
            'type': credential['type'],
            'registered_at': datetime.now().isoformat(),
            'registered_ip': request.remote_addr,
            'last_used': None
        }
        
        # 保存到文件
        if save_user_credentials(user_credentials):
            del CHALLENGES[username]
            logger.info(f"生物识别注册成功: {username}")
            return jsonify({"success": True, "message": "生物识别注册成功！"})
        else:
            return jsonify({"error": "保存凭据失败，请重试"}), 500
        
    except Exception as e:
        logger.error(f"注册完成失败: {e}")
        return jsonify({"error": f"注册完成失败: {str(e)}"}), 500

@app.route('/authenticate/begin', methods=['POST'])
def authenticate_begin():
    """开始生物识别认证"""
    try:
        username = request.json.get('username', 'wol_user')
        
        if not username:
            return jsonify({"error": "用户名不能为空"}), 400
        
        username = username.strip()
        
        # 加载用户凭据
        user_credentials = load_user_credentials()
        
        if username not in user_credentials:
            logger.warning(f"认证失败 - 用户未注册: {username}")
            return jsonify({"error": "用户未注册生物识别，请先注册"}), 400
        
        challenge = secrets.token_bytes(32)
        challenge_b64 = base64.urlsafe_b64encode(challenge).decode('utf-8').rstrip('=')
        
        CHALLENGES[username] = {
            'challenge': challenge,
            'timestamp': datetime.now()
        }
        
        # 使用实际域名
        host = request.host.split(':')[0]
        if host in ['127.0.0.1', 'localhost']:
            host = 'wol.gofoyi.shop'
        
        options = {
            "challenge": challenge_b64,
            "timeout": 60000,
            "rpId": host,
            "allowCredentials": [
                {
                    "id": user_credentials[username]['rawId'],
                    "type": "public-key",
                    "transports": ["internal", "usb", "nfc", "ble"]
                }
            ],
            "userVerification": "preferred"
        }
        
        logger.info(f"开始生物识别认证: {username}")
        return jsonify(options)
        
    except Exception as e:
        logger.error(f"认证初始化失败: {e}")
        return jsonify({"error": f"认证初始化失败: {str(e)}"}), 500

@app.route('/authenticate/complete', methods=['POST'])
def authenticate_complete():
    """完成生物识别认证"""
    try:
        username = request.json.get('username', 'wol_user')
        credential = request.json.get('credential')
        
        if not username or not credential:
            return jsonify({"error": "缺少必要参数"}), 400
        
        username = username.strip()
        
        if username not in CHALLENGES:
            logger.warning(f"认证完成时未找到挑战: {username}")
            return jsonify({"error": "未找到挑战，请重新开始认证"}), 400
        
        # 加载用户凭据
        user_credentials = load_user_credentials()
        
        if username not in user_credentials:
            return jsonify({"error": "用户未注册"}), 400
        
        challenge_data = CHALLENGES[username]
        if datetime.now() - challenge_data['timestamp'] > timedelta(minutes=5):
            del CHALLENGES[username]
            return jsonify({"error": "挑战已过期，请重新开始认证"}), 400
        
        stored_credential = user_credentials[username]
        if credential['id'] != stored_credential['id']:
            logger.warning(f"认证失败 - 凭据不匹配: {username}")
            return jsonify({"error": "认证失败，凭据不匹配"}), 400
        
        # 更新最后使用时间
        user_credentials[username]['last_used'] = datetime.now().isoformat()
        user_credentials[username]['last_used_ip'] = request.remote_addr
        save_user_credentials(user_credentials)
        
        # 设置会话
        session.permanent = True
        session['biometric_authenticated'] = True
        session['username'] = username
        session['auth_time'] = datetime.now().isoformat()
        
        del CHALLENGES[username]
        
        logger.info(f"生物识别认证成功: {username} from {request.remote_addr}")
        return jsonify({
            "success": True, 
            "message": "生物识别认证成功！",
            "redirect": "/"
        })
        
    except Exception as e:
        logger.error(f"认证失败: {e}")
        return jsonify({"error": f"认证失败: {str(e)}"}), 500

@app.route('/logout', methods=['POST'])
def logout():
    """登出"""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"用户登出: {username}")
    return jsonify({"success": True, "message": "已安全登出", "redirect": "/"})

@app.route('/user_info', methods=['GET'])
@require_biometric_auth
def user_info():
    """获取用户信息"""
    try:
        username = session.get('username')
        user_credentials = load_user_credentials()
        
        if username in user_credentials:
            cred = user_credentials[username]
            return jsonify({
                "username": username,
                "registered_at": cred.get('registered_at'),
                "last_used": cred.get('last_used'),
                "session_timeout": SESSION_TIMEOUT
            })
        else:
            return jsonify({"error": "用户信息不存在"}), 404
            
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return jsonify({"error": "获取用户信息失败"}), 500

# WOL功能路由（保持原有功能）
@app.route('/wake', methods=['POST'])
@require_biometric_auth
def wake_windows():
    """唤醒Windows主机"""
    try:
        url = f"http://{UBUNTU_SERVER_HOST}:{UBUNTU_PORT}/wake"
        payload = {"mac_address": WINDOWS_MAC}
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"唤醒命令发送成功: {session.get('username')}")
            return jsonify(result)
        else:
            logger.error(f"Ubuntu服务器返回错误状态: {response.status_code}")
            return jsonify({
                "success": False,
                "message": f"Ubuntu server returned status {response.status_code}"
            }), 500
            
    except Exception as e:
        logger.error(f"唤醒Windows失败: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/sleep', methods=['POST'])
@require_biometric_auth
def sleep_windows():
    """使Windows主机进入睡眠状态"""
    try:
        url = f"http://{UBUNTU_SERVER_HOST}:{UBUNTU_PORT}/sleep"
        response = requests.post(url, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"睡眠命令发送成功: {session.get('username')}")
            return jsonify(result)
        else:
            logger.error(f"Ubuntu服务器返回错误状态: {response.status_code}")
            return jsonify({
                "success": False,
                "message": f"Ubuntu server returned status {response.status_code}"
            }), 500
            
    except Exception as e:
        logger.error(f"使Windows睡眠失败: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/status', methods=['GET'])
@require_biometric_auth
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
@require_biometric_auth
def win_status():
    """获取Windows主机状态"""
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
    print("=== WOL远程控制系统 - 生产模式 ===")
    print("Flask应用运行在: http://127.0.0.1:5000")
    print("公网访问地址: https://wol.gofoyi.shop")
    print("请确保Nginx反向代理已正确配置")
    print(f"Ubuntu服务器: {UBUNTU_SERVER_HOST}:{UBUNTU_PORT}")
    print(f"Windows主机MAC: {WINDOWS_MAC}")
    print(f"用户凭据存储文件: {USER_CREDENTIALS_FILE}")
    print("=====================================")
    
    # 确保存储目录存在
    os.makedirs(os.path.dirname(os.path.abspath(USER_CREDENTIALS_FILE)), exist_ok=True)
    
    # 只在本地运行HTTP，让Nginx处理HTTPS
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False
    )
