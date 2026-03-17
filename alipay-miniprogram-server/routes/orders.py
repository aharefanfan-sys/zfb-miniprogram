# -*- coding: utf-8 -*-
"""
订单和免押API
- 创建订单
- 订单支付
- 订单列表/详情
- 免押授权
- 解冻押金
- 支付宝回调通知
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from models import Order, Device, Customer, db
from routes.auth import login_required
from alipay_sdk import AlipaySDK
import time
import json

orders_bp = Blueprint('orders', __name__)


def get_alipay_sdk():
    """获取支付宝SDK实例"""
    return AlipaySDK(
        app_id=current_app.config['ALIPAY_APP_ID'],
        private_key=current_app.config['ALIPAY_PRIVATE_KEY'],
        alipay_public_key=current_app.config['ALIPAY_PUBLIC_KEY'],
        server_url=current_app.config['ALIPAY_SERVER_URL']
    )


def generate_order_no():
    """生成订单号"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random = str(int(time.time() * 1000))[-6:]
    return f"ORD{timestamp}{random}"


def generate_out_request_no():
    """生成请求号（用于免押操作）"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random = str(int(time.time() * 1000))[-4:]
    return f"REQ{timestamp}{random}"


@orders_bp.route('/', methods=['GET'])
@login_required
def list_orders():
    """
    获取用户订单列表
    """
    customer = request.customer
    
    # 分页参数
    page = request.args.get('page', 1, type=int)
    page_size = min(request.args.get('page_size', 20, type=int), 100)
    
    # 状态筛选
    status = request.args.get('status')
    
    # 构建查询
    query = Order.query.filter_by(customer_id=customer.id)
    
    if status:
        query = query.filter_by(status=status)
    
    # 按创建时间倒序
    query = query.order_by(Order.created_at.desc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    orders = pagination.items
    
    return jsonify({
        'success': True,
        'data': {
            'list': [order.to_dict() for order in orders],
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }
    })


@orders_bp.route('/<int:order_id>', methods=['GET'])
@login_required
def get_order(order_id):
    """获取订单详情"""
    customer = request.customer
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'success': False, 'message': '订单不存在'}), 404
    
    # 只能查看自己的订单
    if order.customer_id != customer.id:
        return jsonify({'success': False, 'message': '无权查看该订单'}), 403
    
    return jsonify({
        'success': True,
        'data': order.to_dict()
    })


@orders_bp.route('/create', methods=['POST'])
@login_required
def create_order():
    """
    创建订单
    {
        "device_id": 1,
        "start_date": "2024-01-15",
        "end_date": "2024-01-20",
        "deposit_free": true,  // 是否使用免押
        "remark": "备注"
    }
    """
    customer = request.customer
    data = request.get_json()
    
    # 验证参数
    device_id = data.get('device_id')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    deposit_free = data.get('deposit_free', False)
    
    if not device_id or not start_date_str or not end_date_str:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    # 解析日期
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'message': '日期格式错误，应为 YYYY-MM-DD'}), 400
    
    if start_date >= end_date:
        return jsonify({'success': False, 'message': '结束日期必须晚于开始日期'}), 400
    
    # 计算天数
    days = (end_date - start_date).days
    if days < 1:
        return jsonify({'success': False, 'message': '租赁天数至少为1天'}), 400
    
    # 查询设备
    device = Device.query.get(device_id)
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    
    if device.status != 'available':
        return jsonify({'success': False, 'message': '该设备当前不可用'}), 400
    
    # 检查免押资格
    if deposit_free and not customer.deposit_free_eligible:
        return jsonify({'success': False, 'message': '您暂不具备免押资格'}), 400
    
    # 计算费用
    daily_price = float(device.daily_price)
    deposit_amount = 0 if deposit_free else float(device.deposit_amount)
    rental_amount = daily_price * days
    total_amount = rental_amount + deposit_amount
    
    # 创建订单
    order = Order(
        order_no=generate_order_no(),
        customer_id=customer.id,
        device_id=device.id,
        start_date=start_date,
        end_date=end_date,
        days=days,
        daily_price=daily_price,
        rental_amount=rental_amount,
        deposit_amount=deposit_amount,
        total_amount=total_amount,
        deposit_free=deposit_free,
        remark=data.get('remark'),
        status='pending_payment',
        pay_status='unpaid'
    )
    
    try:
        db.session.add(order)
        
        # 锁定设备状态
        device.status = 'rented'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '订单创建成功',
            'data': order.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create order error: {e}")
        return jsonify({'success': False, 'message': f'创建订单失败: {str(e)}'}), 500


@orders_bp.route('/<int:order_id>/pay', methods=['POST'])
@login_required
def pay_order(order_id):
    """
    发起订单支付
    返回支付参数供小程序调起支付
    """
    customer = request.customer
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'success': False, 'message': '订单不存在'}), 404
    
    if order.customer_id != customer.id:
        return jsonify({'success': False, 'message': '无权操作该订单'}), 403
    
    if order.status != 'pending_payment':
        return jsonify({'success': False, 'message': '订单状态不正确'}), 400
    
    if order.pay_status == 'paid':
        return jsonify({'success': False, 'message': '订单已支付'}), 400
    
    try:
        alipay = get_alipay_sdk()
        
        # 创建支付宝交易
        result = alipay.alipay_trade_create(
            out_trade_no=order.order_no,
            total_amount=float(order.total_amount),
            subject=f"租赁-{order.device.name}",
            buyer_id=customer.alipay_user_id,
            notify_url=current_app.config['NOTIFY_URL'],
            timeout_express='30m'  # 30分钟支付超时
        )
        
        if result.get('success'):
            trade_no = result['data'].get('trade_no')
            
            return jsonify({
                'success': True,
                'message': '支付单创建成功',
                'data': {
                    'trade_no': trade_no,
                    'order_no': order.order_no,
                    'amount': float(order.total_amount)
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': f"创建支付单失败: {result.get('message', '未知错误')}"
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Pay order error: {e}")
        return jsonify({'success': False, 'message': f'支付失败: {str(e)}'}), 500


@orders_bp.route('/<int:order_id>/deposit-free-auth', methods=['POST'])
@login_required
def deposit_free_auth(order_id):
    """
    发起免押预授权
    免押场景下冻结押金（不实际扣款）
    """
    customer = request.customer
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'success': False, 'message': '订单不存在'}), 404
    
    if order.customer_id != customer.id:
        return jsonify({'success': False, 'message': '无权操作该订单'}), 403
    
    if not order.deposit_free:
        return jsonify({'success': False, 'message': '该订单不是免押订单'}), 400
    
    if order.auth_no:
        return jsonify({'success': False, 'message': '已完成授权，无需重复操作'}), 400
    
    if order.status != 'pending_payment':
        return jsonify({'success': False, 'message': '订单状态不正确'}), 400
    
    try:
        alipay = get_alipay_sdk()
        
        # 创建授权
        out_order_no = f"AUTH_{order.order_no}"
        out_request_no = generate_out_request_no()
        
        result = alipay.alipay_fund_auth_order_freeze(
            out_order_no=out_order_no,
            out_request_no=out_request_no,
            amount=float(order.device.deposit_amount),  # 授权金额为押金金额
            order_title=f"押金授权-{order.device.name}",
            buyer_id=customer.alipay_user_id,
            notify_url=f"{current_app.config['NOTIFY_URL']}/auth"
        )
        
        if result.get('success'):
            auth_data = result['data']
            
            # 更新订单授权信息
            order.auth_no = auth_data.get('auth_no')
            order.auth_time = datetime.now()
            order.auth_amount = order.device.deposit_amount
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': '授权申请已提交',
                'data': {
                    'auth_no': order.auth_no,
                    'auth_amount': float(order.auth_amount)
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': f"授权失败: {result.get('message', '未知错误')}"
            }), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Deposit free auth error: {e}")
        return jsonify({'success': False, 'message': f'授权失败: {str(e)}'}), 500


@orders_bp.route('/<int:order_id>/unfreeze', methods=['POST'])
@login_required
def unfreeze_deposit(order_id):
    """
    解冻押金
    租赁结束后解冻免押授权金额
    """
    customer = request.customer
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'success': False, 'message': '订单不存在'}), 404
    
    if order.customer_id != customer.id:
        return jsonify({'success': False, 'message': '无权操作该订单'}), 403
    
    if not order.deposit_free or not order.auth_no:
        return jsonify({'success': False, 'message': '该订单无需解冻'}), 400
    
    if order.unfreeze_status == 'SUCCESS':
        return jsonify({'success': False, 'message': '押金已解冻'}), 400
    
    try:
        alipay = get_alipay_sdk()
        
        out_request_no = generate_out_request_no()
        
        result = alipay.alipay_fund_auth_order_unfreeze(
            auth_no=order.auth_no,
            out_request_no=out_request_no,
            amount=float(order.auth_amount),
            remark=f"订单{order.order_no}租赁结束，解冻押金",
            notify_url=f"{current_app.config['NOTIFY_URL']}/unfreeze"
        )
        
        if result.get('success'):
            # 更新解冻状态（等待异步通知最终确认）
            order.unfreeze_status = 'PROCESSING'
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': '解冻申请已提交，等待处理',
                'data': {
                    'auth_no': order.auth_no,
                    'unfreeze_amount': float(order.auth_amount)
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': f"解冻申请失败: {result.get('message', '未知错误')}"
            }), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unfreeze deposit error: {e}")
        return jsonify({'success': False, 'message': f'解冻失败: {str(e)}'}), 500


@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """取消订单"""
    customer = request.customer
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'success': False, 'message': '订单不存在'}), 404
    
    if order.customer_id != customer.id:
        return jsonify({'success': False, 'message': '无权操作该订单'}), 403
    
    if order.status != 'pending_payment':
        return jsonify({'success': False, 'message': '只能取消待支付订单'}), 400
    
    try:
        # 如果已创建授权，需要取消授权
        if order.auth_no:
            # TODO: 调用取消授权接口
            pass
        
        # 释放设备
        device = order.device
        device.status = 'available'
        
        # 更新订单状态
        order.status = 'cancelled'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '订单已取消'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'取消失败: {str(e)}'}), 500


# ==================== 支付宝异步通知接口 ====================

@orders_bp.route('/notify/pay', methods=['POST'])
def alipay_notify_pay():
    """
    支付宝支付异步通知
    """
    try:
        # 获取通知数据
        data = request.form.to_dict()
        
        current_app.logger.info(f"Received pay notify: {data}")
        
        # 验证签名
        alipay = get_alipay_sdk()
        if not alipay.verify_notify(data.copy()):
            current_app.logger.error("Pay notify signature verification failed")
            return 'fail'
        
        # 处理通知
        trade_status = data.get('trade_status')
        out_trade_no = data.get('out_trade_no')
        trade_no = data.get('trade_no')
        
        order = Order.query.filter_by(order_no=out_trade_no).first()
        
        if not order:
            current_app.logger.error(f"Order not found: {out_trade_no}")
            return 'fail'
        
        # 更新订单状态
        if trade_status in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
            order.pay_status = 'paid'
            order.pay_time = datetime.now()
            order.pay_trade_no = trade_no
            order.status = 'paid'
            
            db.session.commit()
            current_app.logger.info(f"Order {out_trade_no} paid successfully")
            
        elif trade_status == 'TRADE_CLOSED':
            order.pay_status = 'closed'
            order.status = 'cancelled'
            
            # 释放设备
            device = order.device
            device.status = 'available'
            
            db.session.commit()
            current_app.logger.info(f"Order {out_trade_no} closed")
        
        return 'success'
        
    except Exception as e:
        current_app.logger.error(f"Pay notify error: {e}")
        return 'fail'


@orders_bp.route('/notify/auth', methods=['POST'])
def alipay_notify_auth():
    """
    支付宝授权异步通知
    """
    try:
        data = request.form.to_dict()
        current_app.logger.info(f"Received auth notify: {data}")
        
        # 验证签名
        alipay = get_alipay_sdk()
        if not alipay.verify_notify(data.copy()):
            current_app.logger.error("Auth notify signature verification failed")
            return 'fail'
        
        # 处理授权结果
        notify_type = data.get('notify_type')
        auth_no = data.get('auth_no')
        
        # 查找订单
        order = Order.query.filter_by(auth_no=auth_no).first()
        
        if not order:
            current_app.logger.error(f"Order not found for auth: {auth_no}")
            return 'fail'
        
        # 更新授权状态
        if notify_type == 'alipay.fund.auth.freeze':
            status = data.get('status')
            if status == 'SUCCESS':
                current_app.logger.info(f"Auth {auth_no} frozen successfully")
            elif status == 'CLOSED':
                order.auth_no = None
                order.auth_time = None
                order.auth_amount = None
                db.session.commit()
                current_app.logger.info(f"Auth {auth_no} closed")
        
        return 'success'
        
    except Exception as e:
        current_app.logger.error(f"Auth notify error: {e}")
        return 'fail'


@orders_bp.route('/notify/unfreeze', methods=['POST'])
def alipay_notify_unfreeze():
    """
    支付宝解冻异步通知
    """
    try:
        data = request.form.to_dict()
        current_app.logger.info(f"Received unfreeze notify: {data}")
        
        # 验证签名
        alipay = get_alipay_sdk()
        if not alipay.verify_notify(data.copy()):
            current_app.logger.error("Unfreeze notify signature verification failed")
            return 'fail'
        
        auth_no = data.get('auth_no')
        status = data.get('status')
        
        order = Order.query.filter_by(auth_no=auth_no).first()
        
        if not order:
            current_app.logger.error(f"Order not found for unfreeze: {auth_no}")
            return 'fail'
        
        # 更新解冻状态
        if status == 'SUCCESS':
            order.unfreeze_status = 'SUCCESS'
            order.unfreeze_time = datetime.now()
            db.session.commit()
            current_app.logger.info(f"Auth {auth_no} unfrozen successfully")
        
        return 'success'
        
    except Exception as e:
        current_app.logger.error(f"Unfreeze notify error: {e}")
        return 'fail'
