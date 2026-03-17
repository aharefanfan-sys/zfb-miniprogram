# -*- coding: utf-8 -*-
"""
工具函数
"""

import random
import string
import hashlib
import time
from datetime import datetime, date
import json


def generate_random_string(length=16):
    """生成随机字符串"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def generate_timestamp():
    """生成时间戳（毫秒）"""
    return int(time.time() * 1000)


def format_datetime(dt, format='%Y-%m-%d %H:%M:%S'):
    """格式化日期时间"""
    if not dt:
        return None
    if isinstance(dt, (datetime, date)):
        return dt.strftime(format)
    return dt


def parse_datetime(dt_str, format='%Y-%m-%d %H:%M:%S'):
    """解析日期时间字符串"""
    if not dt_str:
        return None
    try:
        return datetime.strptime(dt_str, format)
    except ValueError:
        return None


def calculate_rental_days(start_date, end_date):
    """计算租赁天数"""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    delta = end_date - start_date
    return delta.days


def calculate_rental_amount(daily_price, days):
    """计算租金总额"""
    return float(daily_price) * int(days)


def md5_hash(text):
    """计算MD5哈希"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def sha256_hash(text):
    """计算SHA256哈希"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def safe_json_loads(text, default=None):
    """安全解析JSON"""
    if not text:
        return default if default is not None else {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def safe_json_dumps(data, ensure_ascii=False):
    """安全序列化为JSON"""
    try:
        return json.dumps(data, ensure_ascii=ensure_ascii, default=str)
    except (TypeError, ValueError):
        return '{}'


def mask_phone(phone):
    """手机号脱敏"""
    if not phone or len(phone) != 11:
        return phone
    return phone[:3] + '****' + phone[7:]


def mask_alipay_user_id(user_id):
    """支付宝用户ID脱敏"""
    if not user_id or len(user_id) <= 8:
        return user_id
    return user_id[:4] + '****' + user_id[-4:]


def validate_phone(phone):
    """验证手机号格式"""
    import re
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))


def validate_date_range(start_date, end_date):
    """验证日期范围是否有效"""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # 开始日期不能早于今天
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if start_date < today:
        return False, '开始日期不能早于今天'
    
    # 结束日期必须晚于开始日期
    if end_date <= start_date:
        return False, '结束日期必须晚于开始日期'
    
    # 最大租赁天数限制（例如90天）
    max_days = 90
    if (end_date - start_date).days > max_days:
        return False, f'单次租赁最多{max_days}天'
    
    return True, None


def paginate(query, page=1, per_page=20):
    """通用分页函数"""
    per_page = min(per_page, 100)  # 最大100条
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return {
        'items': pagination.items,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'next_num': pagination.next_num,
        'prev_num': pagination.prev_num
    }


class APIResponse:
    """统一API响应格式"""
    
    @staticmethod
    def success(data=None, message='操作成功'):
        return {
            'success': True,
            'message': message,
            'data': data
        }
    
    @staticmethod
    def error(message='操作失败', code=None, data=None):
        response = {
            'success': False,
            'message': message
        }
        if code:
            response['code'] = code
        if data:
            response['data'] = data
        return response


def get_client_ip():
    """获取客户端IP地址"""
    from flask import request
    
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        ip = request.remote_addr
    
    return ip
