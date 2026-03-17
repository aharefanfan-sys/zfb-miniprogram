# -*- coding: utf-8 -*-
"""
设备数据同步脚本
用于从其他数据源（如rental-system）同步设备数据
"""

import os
import sys
import json
import requests
from datetime import datetime

# 添加项目目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models import Device


def sync_from_api(api_url, api_key=None):
    """
    从API同步设备数据
    
    :param api_url: 设备数据源API地址
    :param api_key: API密钥（如果需要）
    """
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    
    try:
        print(f"Fetching devices from {api_url}...")
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        devices = data.get('data', {}).get('list', []) if isinstance(data, dict) else data
        
        print(f"Found {len(devices)} devices")
        
        sync_count = 0
        update_count = 0
        
        for device_data in devices:
            device_no = device_data.get('device_no') or device_data.get('id')
            
            if not device_no:
                print(f"Skipping device without device_no: {device_data}")
                continue
            
            # 检查设备是否已存在
            existing = Device.query.filter_by(device_no=str(device_no)).first()
            
            if existing:
                # 更新现有设备
                existing.name = device_data.get('name', existing.name)
                existing.model = device_data.get('model', existing.model)
                existing.category = device_data.get('category', existing.category)
                existing.brand = device_data.get('brand', existing.brand)
                existing.location = device_data.get('location', existing.location)
                existing.latitude = device_data.get('latitude', existing.latitude)
                existing.longitude = device_data.get('longitude', existing.longitude)
                existing.daily_price = device_data.get('daily_price', existing.daily_price)
                existing.deposit_amount = device_data.get('deposit_amount', existing.deposit_amount)
                existing.status = device_data.get('status', existing.status)
                existing.description = device_data.get('description', existing.description)
                
                if 'images' in device_data:
                    existing.images = json.dumps(device_data['images'])
                if 'specs' in device_data:
                    existing.specs = json.dumps(device_data['specs'])
                
                update_count += 1
                print(f"Updated device: {device_no}")
            else:
                # 创建新设备
                new_device = Device(
                    device_no=str(device_no),
                    name=device_data.get('name', '未命名设备'),
                    model=device_data.get('model'),
                    category=device_data.get('category'),
                    brand=device_data.get('brand'),
                    images=json.dumps(device_data.get('images', [])) if device_data.get('images') else None,
                    location=device_data.get('location'),
                    latitude=device_data.get('latitude'),
                    longitude=device_data.get('longitude'),
                    daily_price=device_data.get('daily_price', 0),
                    deposit_amount=device_data.get('deposit_amount', 0),
                    status=device_data.get('status', 'available'),
                    description=device_data.get('description'),
                    specs=json.dumps(device_data.get('specs', {})) if device_data.get('specs') else None
                )
                db.session.add(new_device)
                sync_count += 1
                print(f"Created device: {device_no}")
        
        db.session.commit()
        print(f"\nSync completed:")
        print(f"  - Created: {sync_count}")
        print(f"  - Updated: {update_count}")
        print(f"  - Total: {sync_count + update_count}")
        
    except requests.RequestException as e:
        print(f"API request failed: {e}")
        db.session.rollback()
    except Exception as e:
        print(f"Sync failed: {e}")
        db.session.rollback()


def sync_from_csv(csv_file_path):
    """
    从CSV文件同步设备数据
    
    CSV格式示例：
    device_no,name,model,category,daily_price,deposit_amount,status
    DEV001,iPhone 15,iPhone15,手机,50,5000,available
    """
    import csv
    
    try:
        print(f"Reading devices from {csv_file_path}...")
        
        sync_count = 0
        update_count = 0
        
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                device_no = row.get('device_no')
                
                if not device_no:
                    continue
                
                existing = Device.query.filter_by(device_no=device_no).first()
                
                if existing:
                    # 更新
                    existing.name = row.get('name', existing.name)
                    existing.model = row.get('model', existing.model)
                    existing.category = row.get('category', existing.category)
                    existing.brand = row.get('brand', existing.brand)
                    existing.location = row.get('location', existing.location)
                    existing.daily_price = row.get('daily_price', existing.daily_price)
                    existing.deposit_amount = row.get('deposit_amount', existing.deposit_amount)
                    existing.status = row.get('status', existing.status)
                    update_count += 1
                else:
                    # 创建
                    new_device = Device(
                        device_no=device_no,
                        name=row.get('name', '未命名设备'),
                        model=row.get('model'),
                        category=row.get('category'),
                        brand=row.get('brand'),
                        location=row.get('location'),
                        daily_price=float(row.get('daily_price', 0)),
                        deposit_amount=float(row.get('deposit_amount', 0)),
                        status=row.get('status', 'available')
                    )
                    db.session.add(new_device)
                    sync_count += 1
        
        db.session.commit()
        print(f"\nSync completed:")
        print(f"  - Created: {sync_count}")
        print(f"  - Updated: {update_count}")
        
    except FileNotFoundError:
        print(f"File not found: {csv_file_path}")
    except Exception as e:
        print(f"Sync failed: {e}")
        db.session.rollback()


def sync_from_json(json_file_path):
    """
    从JSON文件同步设备数据
    
    JSON格式示例：
    [
        {
            "device_no": "DEV001",
            "name": "iPhone 15",
            "model": "iPhone15",
            "category": "手机",
            "daily_price": 50,
            "deposit_amount": 5000,
            "status": "available"
        }
    ]
    """
    try:
        print(f"Reading devices from {json_file_path}...")
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            devices = json.load(f)
        
        if not isinstance(devices, list):
            devices = [devices]
        
        sync_count = 0
        update_count = 0
        
        for device_data in devices:
            device_no = device_data.get('device_no')
            
            if not device_no:
                continue
            
            existing = Device.query.filter_by(device_no=str(device_no)).first()
            
            if existing:
                # 更新
                for key, value in device_data.items():
                    if hasattr(existing, key) and key != 'device_no':
                        if key in ['images', 'specs'] and isinstance(value, (list, dict)):
                            setattr(existing, key, json.dumps(value))
                        else:
                            setattr(existing, key, value)
                update_count += 1
            else:
                # 创建
                new_device = Device(
                    device_no=str(device_no),
                    name=device_data.get('name', '未命名设备'),
                    model=device_data.get('model'),
                    category=device_data.get('category'),
                    brand=device_data.get('brand'),
                    images=json.dumps(device_data.get('images', [])) if device_data.get('images') else None,
                    location=device_data.get('location'),
                    latitude=device_data.get('latitude'),
                    longitude=device_data.get('longitude'),
                    daily_price=device_data.get('daily_price', 0),
                    deposit_amount=device_data.get('deposit_amount', 0),
                    status=device_data.get('status', 'available'),
                    description=device_data.get('description'),
                    specs=json.dumps(device_data.get('specs', {})) if device_data.get('specs') else None
                )
                db.session.add(new_device)
                sync_count += 1
        
        db.session.commit()
        print(f"\nSync completed:")
        print(f"  - Created: {sync_count}")
        print(f"  - Updated: {update_count}")
        
    except FileNotFoundError:
        print(f"File not found: {json_file_path}")
    except json.JSONDecodeError:
        print(f"Invalid JSON format in: {json_file_path}")
    except Exception as e:
        print(f"Sync failed: {e}")
        db.session.rollback()


def init_sample_data():
    """初始化示例设备数据（用于测试）"""
    sample_devices = [
        {
            'device_no': 'DEV001',
            'name': 'iPhone 15 Pro Max',
            'model': 'A3108',
            'category': '手机',
            'brand': 'Apple',
            'daily_price': 80.00,
            'deposit_amount': 8000.00,
            'location': '北京市朝阳区',
            'description': '256GB 深空黑色，含充电器',
            'images': ['https://example.com/iphone15-1.jpg', 'https://example.com/iphone15-2.jpg'],
            'specs': {'color': '深空黑色', 'storage': '256GB', 'network': '5G'}
        },
        {
            'device_no': 'DEV002',
            'name': '华为 Mate 60 Pro',
            'model': 'ALN-AL00',
            'category': '手机',
            'brand': '华为',
            'daily_price': 60.00,
            'deposit_amount': 6000.00,
            'location': '上海市浦东新区',
            'description': '12GB+512GB 雅川青',
            'images': ['https://example.com/mate60-1.jpg'],
            'specs': {'color': '雅川青', 'storage': '512GB', 'network': '5G'}
        },
        {
            'device_no': 'DEV003',
            'name': '佳能 EOS R5',
            'model': 'R5',
            'category': '相机',
            'brand': 'Canon',
            'daily_price': 150.00,
            'deposit_amount': 20000.00,
            'location': '广州市天河区',
            'description': '全画幅微单，含RF 24-70mm镜头',
            'images': ['https://example.com/r5-1.jpg', 'https://example.com/r5-2.jpg'],
            'specs': {'sensor': '全画幅', 'megapixels': '4500万', 'video': '8K'}
        },
        {
            'device_no': 'DEV004',
            'name': '索尼 A7M4',
            'model': 'ILCE-7M4',
            'category': '相机',
            'brand': 'Sony',
            'daily_price': 120.00,
            'deposit_amount': 15000.00,
            'location': '深圳市南山区',
            'description': '全画幅微单，含FE 28-70mm镜头',
            'images': ['https://example.com/a7m4-1.jpg'],
            'specs': {'sensor': '全画幅', 'megapixels': '3300万', 'video': '4K 60p'}
        },
        {
            'device_no': 'DEV005',
            'name': '大疆 DJI Mini 4 Pro',
            'model': 'Mini 4 Pro',
            'category': '无人机',
            'brand': 'DJI',
            'daily_price': 100.00,
            'deposit_amount': 5000.00,
            'location': '杭州市西湖区',
            'description': '带屏遥控器版，三电池套装',
            'images': ['https://example.com/mini4-1.jpg'],
            'specs': {'weight': '<249g', 'video': '4K/60fps', 'flight_time': '34分钟'}
        }
    ]
    
    sync_count = 0
    
    for device_data in sample_devices:
        if not Device.query.filter_by(device_no=device_data['device_no']).first():
            device = Device(
                device_no=device_data['device_no'],
                name=device_data['name'],
                model=device_data['model'],
                category=device_data['category'],
                brand=device_data['brand'],
                images=json.dumps(device_data.get('images', [])),
                location=device_data.get('location'),
                daily_price=device_data['daily_price'],
                deposit_amount=device_data['deposit_amount'],
                status='available',
                description=device_data.get('description'),
                specs=json.dumps(device_data.get('specs', {}))
            )
            db.session.add(device)
            sync_count += 1
            print(f"Created sample device: {device_data['device_no']}")
    
    db.session.commit()
    print(f"\nSample data initialization completed: {sync_count} devices created")


if __name__ == '__main__':
    # 创建应用上下文
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        # 确保表已创建
        db.create_all()
        
        import argparse
        
        parser = argparse.ArgumentParser(description='Device data synchronization tool')
        parser.add_argument('--source', choices=['api', 'csv', 'json', 'sample'], 
                          required=True, help='Data source type')
        parser.add_argument('--url', help='API URL (for api source)')
        parser.add_argument('--api-key', help='API key (for api source)')
        parser.add_argument('--file', help='File path (for csv/json source)')
        
        args = parser.parse_args()
        
        if args.source == 'api':
            if not args.url:
                print("Error: --url is required for api source")
                sys.exit(1)
            sync_from_api(args.url, args.api_key)
        
        elif args.source == 'csv':
            if not args.file:
                print("Error: --file is required for csv source")
                sys.exit(1)
            sync_from_csv(args.file)
        
        elif args.source == 'json':
            if not args.file:
                print("Error: --file is required for json source")
                sys.exit(1)
            sync_from_json(args.file)
        
        elif args.source == 'sample':
            init_sample_data()
