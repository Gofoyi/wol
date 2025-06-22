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
import socket  # 添加socket模块用于DNS解析

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

# 域名常量
DOMAIN_NAME = config['bypass_domain']

# DNS缓存
_dns_cache = {}
_dns_cache_time = {}
DNS_CACHE_TTL = 300  # 5分钟缓存

def resolve_domain_ipv4(domain):
    """解析域名的IPv4地址（带缓存）"""
    try:
        current_time = datetime.now()
        
        # 检查缓存
        if (domain in _dns_cache and 
            domain in _dns_cache_time and 
            (current_time - _dns_cache_time[domain]).total_seconds() < DNS_CACHE_TTL):
            return _dns_cache[domain]
        
        # 执行DNS解析
        result = socket.getaddrinfo(domain, None, socket.AF_INET)
        if result:
            ip = result[0][4][0]
            # 缓存结果
            _dns_cache[domain] = ip
            _dns_cache_time[domain] = current_time
            return ip
            
    except Exception as e:
        logger.error(f"解析域名 {domain} 失败: {e}")
        # 如果解析失败但有缓存，返回缓存结果
        if domain in _dns_cache:
            logger.info(f"DNS解析失败，使用缓存: {_dns_cache[domain]}")
            return _dns_cache[domain]
    return None

def check_ip_bypass_auth(client_ip):
    """检查客户端IP是否与域名解析IP相同，如果相同则可跳过生物验证"""
    try:
        domain_ip = resolve_domain_ipv4(DOMAIN_NAME)
        
        if domain_ip and client_ip == domain_ip:
            logger.info(f"✅ IP认证通过: {client_ip} (本地网络)")
            return True
        else:
            logger.info(f"🌐 远程访问: {client_ip} != {domain_ip} (需生物验证)")
            return False
    except Exception as e:
        logger.error(f"IP检查异常: {e}")
        return False


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
    """需要生物识别认证或IP认证的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        
        # 检查IP认证
        if session.get('ip_bypass_authenticated') and session.get('auth_method') == 'ip_bypass':
            try:
                auth_time = datetime.fromisoformat(session['auth_time'])
                if datetime.now() - auth_time <= timedelta(seconds=SESSION_TIMEOUT):                    # IP认证有效，更新会话时间
                    session['auth_time'] = datetime.now().isoformat()
                    return f(*args, **kwargs)
                else:
                    # IP认证超时，重新检查IP
                    if check_ip_bypass_auth(client_ip):
                        session['auth_time'] = datetime.now().isoformat()
                        return f(*args, **kwargs)
                    else:
                        session.clear()
                        logger.info(f"IP认证失效: {client_ip}")
                        return jsonify({"error": "IP认证失效，需要生物识别认证", "redirect": "/"}), 401
            except ValueError:
                session.clear()
                logger.warning("无效的IP认证会话时间格式")
                return jsonify({"error": "会话数据无效", "redirect": "/"}), 401
        
        # 检查生物识别认证
        if ('biometric_authenticated' not in session or 
            not session['biometric_authenticated'] or
            'auth_time' not in session):
            # 如果没有生物识别认证，再次检查IP
            if check_ip_bypass_auth(client_ip):
                # 重新设置IP认证会话                
                session.permanent = True
                session['ip_bypass_authenticated'] = True
                session['username'] = 'local_user'
                session['auth_time'] = datetime.now().isoformat()
                session['auth_method'] = 'ip_bypass'
                logger.info(f"API访问IP认证: {client_ip}")
                return f(*args, **kwargs)            
            logger.warning(f"未认证访问: {client_ip} -> {request.endpoint}")
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
    # 检查现有的认证会话
    if (session.get('biometric_authenticated') or session.get('ip_bypass_authenticated')) and 'auth_time' in session:
        try:
            auth_time = datetime.fromisoformat(session['auth_time'])
            if datetime.now() - auth_time <= timedelta(seconds=SESSION_TIMEOUT):
                remaining_time = SESSION_TIMEOUT - int((datetime.now() - auth_time).total_seconds())
                auth_method = '生物识别' if session.get('biometric_authenticated') else 'IP认证'
                username = session.get('username', 'user')
                if session.get('ip_bypass_authenticated'):
                    username = '本地用户'
                
                return render_template('dashboard.html', 
                    session_timeout=remaining_time,
                    username=username,
                    auth_method=auth_method)
        except ValueError:
            pass
    
    session.clear()
    return render_template('biometric_auth.html')

@app.route('/check_ip_bypass', methods=['POST'])
def check_ip_bypass():
    """检查客户端IP是否可以跳过生物验证"""
    try:
        data = request.get_json()
        client_ip = data.get('client_ip') if data else None
        
        if not client_ip:
            return jsonify({
                "success": False,
                "bypass": False,
                "message": "无法获取客户端IP"
            })
        
        if check_ip_bypass_auth(client_ip):
            # IP匹配，设置会话并返回成功
            session.permanent = True
            session['ip_bypass_authenticated'] = True
            session['username'] = 'local_user'
            session['auth_time'] = datetime.now().isoformat()
            session['auth_method'] = 'ip_bypass'            
            logger.info(f"IP认证成功: {client_ip} (会话创建)")
            return jsonify({
                "success": True,
                "bypass": True,
                "message": "IP匹配，跳过生物验证",
                "redirect": "/"
            })
        else:
            return jsonify({
                "success": True,
                "bypass": False,
                "message": "需要生物验证"
            })
            
    except Exception as e:
        logger.error(f"IP检查失败: {e}")
        return jsonify({
            "success": False,
            "bypass": False,
            "message": "IP检查失败，需要生物验证"
        })

def get_real_client_ip():
    """获取客户端真实IP地址"""
    # 尝试从各种HTTP头获取真实IP
    headers_to_check = [
        'X-Forwarded-For',
        'X-Real-IP', 
        'CF-Connecting-IP',
        'X-Original-Forwarded-For',
        'X-Client-IP',
        'True-Client-IP'
    ]
    
    for header in headers_to_check:
        value = request.headers.get(header, '').strip()
        if value:
            # X-Forwarded-For可能包含多个IP，取第一个
            if ',' in value:
                value = value.split(',')[0].strip()
            
            # 排除本地IP
            if value and value != '127.0.0.1' and not value.startswith('192.168.') and not value.startswith('10.'):
                logger.info(f"真实IP: {value} (来源: {header})")
                return value
    
    # 如果都没有，返回remote_addr
    remote_addr = request.remote_addr
    logger.info(f"客户端IP: {remote_addr}")
    return remote_addr

@app.route('/quick_ip_check', methods=['GET'])
def quick_ip_check():
    """快速IP检查（用于初步判断）"""
    try:
        # 获取真实IP
        real_ip = get_real_client_ip()
        
        # 快速检查是否可能是本地网络
        domain_ip = resolve_domain_ipv4(DOMAIN_NAME)
        
        # 如果通过HTTP头能获取到真实IP，直接进行匹配
        if real_ip and real_ip != '127.0.0.1' and real_ip != request.remote_addr:
            is_likely_local = real_ip == domain_ip if domain_ip else False
        else:
            # 如果无法从HTTP头获取真实IP，返回false，让WebRTC处理
            is_likely_local = False
        
        logger.info(f"快速检查: {real_ip} {'✅ 本地' if is_likely_local else '🌐 远程'}")
        
        return jsonify({
            "success": True,
            "likely_local": is_likely_local,
            "detected_ip": real_ip,
            "domain_ip": domain_ip,
            "can_bypass": is_likely_local  # 添加明确的bypass标志
        })
        
    except Exception as e:
        logger.error(f"快速IP检查异常: {e}")
        return jsonify({
            "success": False,
            "likely_local": False,
            "detected_ip": None,
            "domain_ip": None,
            "can_bypass": False
        })

# 生物识别认证路由
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
    auth_method = session.get('auth_method', 'unknown')
    session.clear()
    logger.info(f"用户登出: {username} (认证方式: {auth_method})")
    return jsonify({"success": True, "message": "已安全登出", "redirect": "/"})

@app.route('/user_info', methods=['GET'])
@require_biometric_auth
def user_info():
    """获取用户信息"""
    try:
        username = session.get('username')
        auth_method = session.get('auth_method', '生物识别')
        
        if auth_method == 'ip_bypass':
            return jsonify({
                "username": username,
                "auth_method": "IP认证",
                "auth_method_detail": f"客户端IP与域名 {DOMAIN_NAME} 解析IP匹配",
                "registered_at": "N/A (IP认证)",
                "last_used": "N/A (IP认证)",
                "session_timeout": SESSION_TIMEOUT,
                "client_ip": request.remote_addr
            })
        
        # 生物识别认证用户
        user_credentials = load_user_credentials()
        if username in user_credentials:
            cred = user_credentials[username]
            return jsonify({
                "username": username,
                "auth_method": "生物识别",
                "registered_at": cred.get('registered_at'),
                "last_used": cred.get('last_used'),
                "session_timeout": SESSION_TIMEOUT,
                "client_ip": request.remote_addr
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
        debug=False  # 生产环境关闭debug以提高性能
    )
