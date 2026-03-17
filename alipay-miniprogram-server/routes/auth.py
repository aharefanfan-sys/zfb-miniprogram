# -*- coding: utf-8 -*-
"""
用户授权相关路由
- 支付宝登录
- 获取用户信息
- 刷新Token
"""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import jwt
import time
from datetime import datetime
from models import Customer, db
from alipay_sdk import AlipaySDK

auth_bp = Blueprint('auth', __name__)


def generate_token(customer_id):
    """生成JWT Token"""
    payload = {
        'customer_id': customer_id,
        'exp': datetime.utcnow().timestamp() + 86400  # 24小时有效期
    }
    return jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )


def verify_token(token):
    """验证JWT Token"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload.get('customer_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': '未提供有效的认证信息'}), 401
        
        token = auth_header[7:]  # 去掉 'Bearer '
        customer_id = verify_token(token)
        
        if not customer_id:
            return jsonify({'success': False, 'message': '登录已过期，请重新登录'}), 401
        
        # 将用户信息附加到请求上下文
        customer = Customer.query.get(customer_id)
        if not customer or customer.status == 'blocked':
            return jsonify({'success': False, 'message': '用户不存在或已被封禁'}), 401
        
        request.customer = customer
        return f(*args, **kwargs)
    return decorated_function


def get_alipay_sdk():
    """获取支付宝SDK实例"""
    return AlipaySDK(
        app_id=current_app.config['ALIPAY_APP_ID'],
        private_key=current_app.config['ALIPAY_PRIVATE_KEY'],
        alipay_public_key=current_app.config['ALIPAY_PUBLIC_KEY'],
        server_url=current_app.config['ALIPAY_SERVER_URL']
    )


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    支付宝小程序登录
    前端传入auth_code，后端换取access_token并获取用户信息
    """
    data = request.get_json()
    auth_code = data.get('auth_code')
    
    if not auth_code:
        return jsonify({'success': False, 'message': '缺少授权码'}), 400
    
    try:
        # 初始化支付宝SDK
        alipay = get_alipay_sdk()
        
        # 1. 用auth_code换取access_token
        token_result = alipay.alipay_system_oauth_token(
            grant_type='authorization_code',
            code=auth_code
        )
        
        if not token_result.get('success'):
            return jsonify({
                'success': False, 
                'message': f"获取token失败: {token_result.get('message', '未知错误')}"
            }), 400
        
        token_data = token_result['data']
        access_token = token_data.get('access_token')
        alipay_user_id = token_data.get('user_id')
        open_id = token_data.get('open_id')
        
        if not alipay_user_id:
            return jsonify({'success': False, 'message': '无法获取用户ID'}), 400
        
        # 2. 获取用户信息
        user_info_result = alipay.alipay_user_info_share(auth_token=access_token)
        user_info = user_info_result.get('data', {}) if user_info_result.get('success') else {}
        
        # 3. 查询或创建用户
        customer = Customer.query.filter_by(alipay_user_id=alipay_user_id).first()
        
        if customer:
            # 更新用户信息
            customer.open_id = open_id or customer.open_id
            customer.nickname = user_info.get('nick_name') or customer.nickname
            customer.avatar = user_info.get('avatar') or customer.avatar
            customer.last_login_at = datetime.now()
            
            # 获取手机号（如果有）
            if user_info.get('mobile'):
                customer.phone = user_info.get('mobile')
        else:
            # 创建新用户
            customer = Customer(
                alipay_user_id=alipay_user_id,
                open_id=open_id,
                phone=user_info.get('mobile'),
                nickname=user_info.get('nick_name'),
                avatar=user_info.get('avatar'),
                status='active',
                last_login_at=datetime.now()
            )
            db.session.add(customer)
        
        db.session.commit()
        
        # 4. 生成JWT Token
        token = generate_token(customer.id)
        
        # 5. 获取芝麻信用分（可选，异步处理也可以）
        # credit_result = alipay.zhima_credit_score_brief_get(alipay_user_id)
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'token': token,
                'expires_in': 86400,
                'user': customer.to_dict()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'message': f'登录失败: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """获取当前用户信息"""
    return jsonify({
        'success': True,
        'data': request.customer.to_dict()
    })


@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用户信息"""
    data = request.get_json()
    customer = request.customer
    
    # 只允许更新特定字段
    allowed_fields = ['nickname', 'phone']
    for field in allowed_fields:
        if field in data:
            setattr(customer, field, data[field])
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '更新成功',
            'data': customer.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500


@auth_bp.route('/refresh-token', methods=['POST'])
@login_required
def refresh_token():
    """刷新访问令牌"""
    customer = request.customer
    new_token = generate_token(customer.id)
    
    return jsonify({
        'success': True,
        'message': '刷新成功',
        'data': {
            'token': new_token,
            'expires_in': 86400
        }
    })


@auth_bp.route('/check-credit', methods=['GET'])
@login_required
def check_credit_score():
    """
    检查用户芝麻信用分
    返回用户是否有免押资格
    """
    customer = request.customer
    
    try:
        alipay = get_alipay_sdk()
        
        # 生成业务流水号
        transaction_id = f"CREDIT_{customer.id}_{int(time.time())}"
        
        result = alipay.zhima_credit_score_brief_get(
            alipay_user_id=customer.alipay_user_id,
            transaction_id=transaction_id
        )
        
        if result.get('success'):
            credit_data = result['data']
            is_admitted = credit_data.get('is_admitted')  # 'Y' 表示通过
            
            # 更新用户信用状态
            customer.deposit_free_eligible = (is_admitted == 'Y')
            customer.credit_score = credit_data.get('score') if is_admitted == 'Y' else None
            db.session.commit()
            
            return jsonify({
                'success': True,
                'data': {
                    'eligible': is_admitted == 'Y',
                    'score': credit_data.get('score'),
                    'message': '您具备免押资格' if is_admitted == 'Y' else '暂不符合免押条件'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': f"查询失败: {result.get('message', '未知错误')}"
            })
            
    except Exception as e:
        current_app.logger.error(f"Check credit error: {e}")
        return jsonify({'success': False, 'message': f'查询失败: {str(e)}'}), 500
