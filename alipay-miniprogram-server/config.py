# -*- coding: utf-8 -*-
"""
支付宝小程序后端配置
"""

import os
from datetime import timedelta

class Config:
    """基础配置"""
    # 密钥配置（生产环境请使用环境变量）
    SECRET_KEY = os.getenv('SECRET_KEY', 'alipay-miniprogram-secret-key-change-in-production')
    
    # 数据库配置 - 默认使用 SQLite，生产环境可使用 PostgreSQL
    # SQLite: sqlite:///alipay_miniprogram.db
    # PostgreSQL: postgresql://user:password@localhost/alipay_miniprogram
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 
        'sqlite:///alipay_miniprogram.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'False').lower() == 'true'
    
    # 支付宝配置
    ALIPAY_APP_ID = os.getenv('ALIPAY_APP_ID', '')
    ALIPAY_PRIVATE_KEY = os.getenv('ALIPAY_PRIVATE_KEY', '')  # 应用私钥
    ALIPAY_PUBLIC_KEY = os.getenv('ALIPAY_PUBLIC_KEY', '')    # 支付宝公钥
    ALIPAY_SERVER_URL = os.getenv('ALIPAY_SERVER_URL', 'https://openapi.alipay.com/gateway.do')
    
    # 小程序配置
    MINIPROGRAM_APP_ID = os.getenv('MINIPROGRAM_APP_ID', '')
    MINIPROGRAM_APP_SECRET = os.getenv('MINIPROGRAM_APP_SECRET', '')
    
    # 芝麻免押配置
    ZHIMA_SERVICE_ID = os.getenv('ZHIMA_SERVICE_ID', '')        # 芝麻信用服务ID（后台创建后获取）
    ZHIMA_CATEGORY = os.getenv('ZHIMA_CATEGORY', '')            # 业务类目（后台配置的类目编码）
    DEPOSIT_PRODUCT_MODE = os.getenv('DEPOSIT_PRODUCT_MODE', 'DEPOSIT_ONLY')  # 免押模式：DEPOSIT_ONLY/POSTPAY/POSTPAY_UNCERTAIN
    
    # 通知回调配置
    NOTIFY_URL = os.getenv('NOTIFY_URL', 'https://your-domain.com/api/orders/notify')
    RETURN_URL = os.getenv('RETURN_URL', 'https://your-domain.com/pay/return')
    
    # JWT配置
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    # 开发环境使用沙箱环境
    ALIPAY_SERVER_URL = os.getenv('ALIPAY_SERVER_URL', 'https://openapi-sandbox.dl.alipaydev.com/gateway.do')


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    # 生产环境使用正式环境
    ALIPAY_SERVER_URL = os.getenv('ALIPAY_SERVER_URL', 'https://openapi.alipay.com/gateway.do')
    
    # 生产环境必须使用环境变量设置密钥
    @classmethod
    def init_app(cls, app):
        required_vars = ['ALIPAY_APP_ID', 'ALIPAY_PRIVATE_KEY', 'ALIPAY_PUBLIC_KEY', 
                        'MINIPROGRAM_APP_ID', 'MINIPROGRAM_APP_SECRET']
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# 配置映射
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
