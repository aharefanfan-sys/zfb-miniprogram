# -*- coding: utf-8 -*-
"""
数据库模型定义
精简模型：Customer、Device、Order
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from app import db


class Customer(db.Model):
    """客户/用户表 - 支付宝小程序用户"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    alipay_user_id = db.Column(db.String(64), unique=True, nullable=False, index=True, comment='支付宝用户ID')
    open_id = db.Column(db.String(64), unique=True, nullable=True, comment='支付宝小程序OpenID')
    phone = db.Column(db.String(20), nullable=True, comment='手机号')
    nickname = db.Column(db.String(100), nullable=True, comment='昵称')
    avatar = db.Column(db.String(500), nullable=True, comment='头像URL')
    
    # 状态字段
    status = db.Column(db.String(20), default='active', comment='状态: active-正常, blocked-封禁')
    
    # 免押相关
    credit_score = db.Column(db.Integer, nullable=True, comment='芝麻信用分')
    deposit_free_eligible = db.Column(db.Boolean, default=False, comment='是否具备免押资格')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    last_login_at = db.Column(db.DateTime, nullable=True, comment='最后登录时间')
    
    # 关联
    orders = db.relationship('Order', backref='customer', lazy='dynamic')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'alipay_user_id': self.alipay_user_id,
            'open_id': self.open_id,
            'phone': self.phone,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'status': self.status,
            'credit_score': self.credit_score,
            'deposit_free_eligible': self.deposit_free_eligible,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Customer {self.alipay_user_id}>'


class Device(db.Model):
    """设备表 - 可租赁设备"""
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    device_no = db.Column(db.String(50), unique=True, nullable=False, index=True, comment='设备编号')
    name = db.Column(db.String(200), nullable=False, comment='设备名称')
    model = db.Column(db.String(100), nullable=True, comment='型号')
    category = db.Column(db.String(50), nullable=True, comment='类别')
    brand = db.Column(db.String(50), nullable=True, comment='品牌')
    
    # 设备图片
    images = db.Column(db.Text, nullable=True, comment='图片URL列表，JSON格式')
    
    # 位置信息
    location = db.Column(db.String(200), nullable=True, comment='位置描述')
    latitude = db.Column(db.Float, nullable=True, comment='纬度')
    longitude = db.Column(db.Float, nullable=True, comment='经度')
    
    # 价格和押金
    daily_price = db.Column(db.Numeric(10, 2), nullable=False, comment='日租金')
    deposit_amount = db.Column(db.Numeric(10, 2), nullable=False, comment='押金金额')
    
    # 设备状态
    # available: 可用
    # rented: 已租出
    # maintenance: 维护中
    # offline: 离线/不可用
    status = db.Column(db.String(20), default='available', comment='设备状态')
    
    # 描述
    description = db.Column(db.Text, nullable=True, comment='设备描述')
    specs = db.Column(db.Text, nullable=True, comment='规格参数，JSON格式')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关联
    orders = db.relationship('Order', backref='device', lazy='dynamic')
    
    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'device_no': self.device_no,
            'name': self.name,
            'model': self.model,
            'category': self.category,
            'brand': self.brand,
            'images': json.loads(self.images) if self.images else [],
            'location': self.location,
            'latitude': self.float_or_none(self.latitude),
            'longitude': self.float_or_none(self.longitude),
            'daily_price': float(self.daily_price) if self.daily_price else 0,
            'deposit_amount': float(self.deposit_amount) if self.deposit_amount else 0,
            'status': self.status,
            'description': self.description,
            'specs': json.loads(self.specs) if self.specs else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def float_or_none(value):
        return float(value) if value is not None else None
    
    def __repr__(self):
        return f'<Device {self.device_no}>'


class Order(db.Model):
    """订单表 - 租赁订单"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False, index=True, comment='订单编号')
    
    # 关联
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, comment='客户ID')
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False, comment='设备ID')
    
    # 租赁时间
    start_date = db.Column(db.DateTime, nullable=False, comment='租赁开始日期')
    end_date = db.Column(db.DateTime, nullable=False, comment='租赁结束日期')
    days = db.Column(db.Integer, nullable=False, comment='租赁天数')
    
    # 费用明细
    daily_price = db.Column(db.Numeric(10, 2), nullable=False, comment='日租金单价')
    rental_amount = db.Column(db.Numeric(10, 2), nullable=False, comment='租金总额')
    deposit_amount = db.Column(db.Numeric(10, 2), nullable=False, comment='押金金额')
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, comment='订单总金额')
    
    # 订单状态
    # pending_payment: 待支付
    # paid: 已支付/租赁中
    # completed: 已完成
    # cancelled: 已取消
    # refunding: 退款中
    # refunded: 已退款
    status = db.Column(db.String(20), default='pending_payment', comment='订单状态')
    
    # 支付信息
    pay_status = db.Column(db.String(20), default='unpaid', comment='支付状态: unpaid-未支付, paid-已支付')
    pay_time = db.Column(db.DateTime, nullable=True, comment='支付时间')
    pay_trade_no = db.Column(db.String(100), nullable=True, comment='支付宝交易号')
    
    # 免押相关
    deposit_free = db.Column(db.Boolean, default=False, comment='是否使用免押')
    auth_no = db.Column(db.String(100), nullable=True, comment='支付宝资金授权单号')
    auth_time = db.Column(db.DateTime, nullable=True, comment='授权时间')
    auth_amount = db.Column(db.Numeric(10, 2), nullable=True, comment='授权金额')
    zhima_order_no = db.Column(db.String(100), nullable=True, comment='芝麻侧借还订单号')

    # 订单完结信息
    complete_status = db.Column(db.String(20), nullable=True, comment='完结状态: PROCESSING-处理中, SUCCESS-成功')
    complete_time = db.Column(db.DateTime, nullable=True, comment='完结时间')
    actual_pay_amount = db.Column(db.Numeric(10, 2), nullable=True, comment='实际扣款金额')

    # 解冻/退款信息
    unfreeze_status = db.Column(db.String(20), nullable=True, comment='解冻状态')
    unfreeze_time = db.Column(db.DateTime, nullable=True, comment='解冻时间')
    
    # 备注
    remark = db.Column(db.Text, nullable=True, comment='订单备注')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_id': self.customer_id,
            'device_id': self.device_id,
            'device': self.device.to_dict() if self.device else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'days': self.days,
            'daily_price': float(self.daily_price) if self.daily_price else 0,
            'rental_amount': float(self.rental_amount) if self.rental_amount else 0,
            'deposit_amount': float(self.deposit_amount) if self.deposit_amount else 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'status': self.status,
            'pay_status': self.pay_status,
            'pay_time': self.pay_time.isoformat() if self.pay_time else None,
            'pay_trade_no': self.pay_trade_no,
            'deposit_free': self.deposit_free,
            'auth_no': self.auth_no,
            'auth_time': self.auth_time.isoformat() if self.auth_time else None,
            'auth_amount': float(self.auth_amount) if self.auth_amount else None,
            'zhima_order_no': self.zhima_order_no,
            'complete_status': self.complete_status,
            'complete_time': self.complete_time.isoformat() if self.complete_time else None,
            'actual_pay_amount': float(self.actual_pay_amount) if self.actual_pay_amount else None,
            'unfreeze_status': self.unfreeze_status,
            'unfreeze_time': self.unfreeze_time.isoformat() if self.unfreeze_time else None,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Order {self.order_no}>'
