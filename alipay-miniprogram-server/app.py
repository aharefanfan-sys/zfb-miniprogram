# -*- coding: utf-8 -*-
"""
支付宝小程序后端服务
独立 Flask 应用，不与 rental-system 耦合
"""

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化扩展
db = SQLAlchemy()

def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 加载配置
    from config import config_by_name
    config = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config_by_name.get(config, config_by_name['development']))
    
    # 启用 CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })
    
    # 初始化数据库
    db.init_app(app)
    
    # 注册蓝图
    from routes.auth import auth_bp
    from routes.devices import devices_bp
    from routes.orders import orders_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(devices_bp, url_prefix='/api/devices')
    app.register_blueprint(orders_bp, url_prefix='/api/orders')
    
    # 全局错误处理
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'success': False, 'message': '请求参数错误'}), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'success': False, 'message': '资源不存在'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f"Internal error: {error}")
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500
    
    # 健康检查
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'success': True,
            'message': '服务正常运行',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })
    
    # 数据库初始化接口（仅在开发环境使用）
    @app.route('/api/init-db', methods=['POST'])
    def init_db():
        """初始化数据库表（仅用于首次部署）"""
        try:
            with app.app_context():
                db.create_all()
            return jsonify({'success': True, 'message': '数据库初始化成功'})
        except Exception as e:
            logger.error(f"Database init error: {e}")
            return jsonify({'success': False, 'message': f'数据库初始化失败: {str(e)}'}), 500
    
    # 创建应用上下文时自动创建表
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Starting server on port {port}, debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)
