# -*- coding: utf-8 -*-
"""
设备管理API
- 设备列表
- 设备详情
- 设备搜索
"""

from flask import Blueprint, request, jsonify, current_app
from models import Device, db
from routes.auth import login_required
import json

devices_bp = Blueprint('devices', __name__)


@devices_bp.route('/', methods=['GET'])
def list_devices():
    """
    获取设备列表
    支持分页、筛选、排序
    """
    # 分页参数
    page = request.args.get('page', 1, type=int)
    page_size = min(request.args.get('page_size', 20, type=int), 100)
    
    # 筛选参数
    status = request.args.get('status')
    category = request.args.get('category')
    keyword = request.args.get('keyword')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    # 排序参数
    sort_by = request.args.get('sort_by', 'created_at')  # price, name, created_at
    sort_order = request.args.get('sort_order', 'desc')  # asc, desc
    
    # 构建查询
    query = Device.query
    
    # 应用筛选
    if status:
        query = query.filter_by(status=status)
    else:
        # 默认只显示可用设备
        query = query.filter(Device.status.in_(['available', 'rented']))
    
    if category:
        query = query.filter_by(category=category)
    
    if keyword:
        search = f"%{keyword}%"
        query = query.filter(
            db.or_(
                Device.name.like(search),
                Device.model.like(search),
                Device.brand.like(search),
                Device.location.like(search)
            )
        )
    
    if min_price is not None:
        query = query.filter(Device.daily_price >= min_price)
    
    if max_price is not None:
        query = query.filter(Device.daily_price <= max_price)
    
    # 应用排序
    order_column = getattr(Device, sort_by, Device.created_at)
    if sort_order == 'desc':
        order_column = order_column.desc()
    query = query.order_by(order_column)
    
    # 分页
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    devices = pagination.items
    
    return jsonify({
        'success': True,
        'data': {
            'list': [device.to_dict() for device in devices],
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


@devices_bp.route('/<int:device_id>', methods=['GET'])
def get_device(device_id):
    """获取设备详情"""
    device = Device.query.get(device_id)
    
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    
    return jsonify({
        'success': True,
        'data': device.to_dict()
    })


@devices_bp.route('/<string:device_no>', methods=['GET'])
def get_device_by_no(device_no):
    """通过设备编号获取详情"""
    device = Device.query.filter_by(device_no=device_no).first()
    
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    
    return jsonify({
        'success': True,
        'data': device.to_dict()
    })


@devices_bp.route('/categories', methods=['GET'])
def list_categories():
    """获取设备分类列表"""
    categories = db.session.query(Device.category).distinct().all()
    category_list = [c[0] for c in categories if c[0]]
    
    return jsonify({
        'success': True,
        'data': category_list
    })


@devices_bp.route('/nearby', methods=['GET'])
def nearby_devices():
    """
    查找附近的设备
    根据经纬度计算距离
    """
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', 5000, type=float)  # 默认5公里
    limit = min(request.args.get('limit', 20, type=int), 50)
    
    if lat is None or lng is None:
        return jsonify({'success': False, 'message': '请提供经纬度参数'}), 400
    
    # 简化的距离计算（使用Haversine公式近似）
    # 这里仅作为演示，实际可以使用PostGIS或其他空间数据库
    devices = Device.query.filter(
        Device.status == 'available',
        Device.latitude.isnot(None),
        Device.longitude.isnot(None)
    ).all()
    
    # 计算距离并排序
    import math
    
    def calculate_distance(lat1, lng1, lat2, lng2):
        """计算两点之间的距离（米）"""
        R = 6371000  # 地球半径（米）
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    nearby = []
    for device in devices:
        distance = calculate_distance(lat, lng, device.latitude, device.longitude)
        if distance <= radius:
            device_dict = device.to_dict()
            device_dict['distance'] = round(distance, 2)
            nearby.append(device_dict)
    
    # 按距离排序
    nearby.sort(key=lambda x: x['distance'])
    
    return jsonify({
        'success': True,
        'data': nearby[:limit]
    })


# ==================== 管理员接口（可选） ====================

@devices_bp.route('/', methods=['POST'])
@login_required
def create_device():
    """创建设备（管理员功能）"""
    data = request.get_json()
    
    # 验证必填字段
    required_fields = ['device_no', 'name', 'daily_price', 'deposit_amount']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'缺少必填字段: {field}'}), 400
    
    # 检查设备编号是否已存在
    if Device.query.filter_by(device_no=data['device_no']).first():
        return jsonify({'success': False, 'message': '设备编号已存在'}), 400
    
    try:
        device = Device(
            device_no=data['device_no'],
            name=data['name'],
            model=data.get('model'),
            category=data.get('category'),
            brand=data.get('brand'),
            images=json.dumps(data.get('images', [])) if data.get('images') else None,
            location=data.get('location'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            daily_price=data['daily_price'],
            deposit_amount=data['deposit_amount'],
            status=data.get('status', 'available'),
            description=data.get('description'),
            specs=json.dumps(data.get('specs', {})) if data.get('specs') else None
        )
        
        db.session.add(device)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '设备创建成功',
            'data': device.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'创建失败: {str(e)}'}), 500


@devices_bp.route('/<int:device_id>', methods=['PUT'])
@login_required
def update_device(device_id):
    """更新设备信息（管理员功能）"""
    device = Device.query.get(device_id)
    
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    
    data = request.get_json()
    
    # 更新字段
    updateable_fields = ['name', 'model', 'category', 'brand', 'location', 
                         'latitude', 'longitude', 'daily_price', 'deposit_amount',
                         'status', 'description']
    
    for field in updateable_fields:
        if field in data:
            setattr(device, field, data[field])
    
    # 特殊处理JSON字段
    if 'images' in data:
        device.images = json.dumps(data['images'])
    if 'specs' in data:
        device.specs = json.dumps(data['specs'])
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '设备更新成功',
            'data': device.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500


@devices_bp.route('/<int:device_id>', methods=['DELETE'])
@login_required
def delete_device(device_id):
    """删除设备（管理员功能）"""
    device = Device.query.get(device_id)
    
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    
    # 检查是否有进行中的订单
    active_orders = device.orders.filter(
        Device.status.in_(['pending_payment', 'paid'])
    ).count()
    
    if active_orders > 0:
        return jsonify({
            'success': False, 
            'message': '该设备有进行中的订单，无法删除'
        }), 400
    
    try:
        db.session.delete(device)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '设备删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500
