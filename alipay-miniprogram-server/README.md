# 支付宝小程序后端服务

独立的支付宝小程序后端项目，与 rental-system 完全分离。支持用户授权、设备管理、免押租赁、订单支付等功能。

## 技术栈

- **Web框架**: Flask 3.0
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **ORM**: Flask-SQLAlchemy
- **支付宝SDK**: 自定义封装（支持RSA2签名）
- **认证**: JWT Token
- **部署**: Gunicorn

## 项目结构

```
alipay-miniprogram-server/
├── app.py                 # Flask应用主文件
├── config.py              # 配置文件
├── requirements.txt       # 依赖列表
├── models.py              # 数据库模型
├── alipay_sdk.py          # 支付宝SDK封装
├── routes/                # 路由模块
│   ├── auth.py            # 用户授权登录
│   ├── devices.py         # 设备管理API
│   └── orders.py          # 订单和免押API
├── utils/                 # 工具模块
│   ├── helpers.py         # 通用工具函数
│   └── sync_devices.py    # 设备数据同步脚本
└── README.md              # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件或在启动前设置环境变量：

```bash
# 应用配置
export FLASK_ENV=development  # development/production/testing
export SECRET_KEY=your-secret-key-here
export JWT_SECRET_KEY=your-jwt-secret-key-here
export PORT=5001

# 数据库配置
export DATABASE_URL=sqlite:///alipay_miniprogram.db
# 生产环境使用 PostgreSQL:
# export DATABASE_URL=postgresql://user:password@localhost/alipay_miniprogram

# 支付宝配置（沙箱环境）
export ALIPAY_APP_ID=your-sandbox-app-id
export ALIPAY_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
export ALIPAY_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
export ALIPAY_SERVER_URL=https://openapi-sandbox.dl.alipaydev.com/gateway.do

# 支付宝配置（生产环境）
# export ALIPAY_APP_ID=your-production-app-id
# export ALIPAY_SERVER_URL=https://openapi.alipay.com/gateway.do

# 小程序配置
export MINIPROGRAM_APP_ID=your-miniprogram-app-id
export MINIPROGRAM_APP_SECRET=your-miniprogram-secret

# 回调通知URL（需改为你的实际域名）
export NOTIFY_URL=https://your-domain.com/api/orders/notify
export RETURN_URL=https://your-domain.com/pay/return
```

### 3. 初始化数据库

```bash
# 方法一：自动初始化（启动时自动创建表）
python app.py

# 方法二：手动调用API初始化
python app.py &
curl -X POST http://localhost:5001/api/init-db
```

### 4. 启动服务

```bash
# 开发模式
python app.py

# 生产模式（使用Gunicorn）
gunicorn -w 4 -b 0.0.0.0:5001 app:create_app()
```

### 5. 初始化示例设备数据

```bash
# 添加示例设备数据（用于测试）
python utils/sync_devices.py --source sample
```

## 数据同步

### 从API同步设备数据

```bash
python utils/sync_devices.py --source api --url https://rental-system.example.com/api/devices --api-key your-api-key
```

### 从CSV文件同步

CSV格式：
```csv
device_no,name,model,category,daily_price,deposit_amount,status
DEV001,iPhone 15,iPhone15,手机,50,5000,available
DEV002,华为Mate60,Mate60,手机,60,6000,available
```

```bash
python utils/sync_devices.py --source csv --file devices.csv
```

### 从JSON文件同步

JSON格式：
```json
[
  {
    "device_no": "DEV001",
    "name": "iPhone 15",
    "category": "手机",
    "daily_price": 50,
    "deposit_amount": 5000,
    "status": "available"
  }
]
```

```bash
python utils/sync_devices.py --source json --file devices.json
```

## API接口说明

### 认证相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 支付宝登录 |
| `/api/auth/profile` | GET | 获取用户信息 |
| `/api/auth/profile` | PUT | 更新用户信息 |
| `/api/auth/refresh-token` | POST | 刷新Token |
| `/api/auth/check-credit` | GET | 查询芝麻信用分 |

### 设备相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/devices/` | GET | 设备列表（支持筛选分页） |
| `/api/devices/<id>` | GET | 设备详情 |
| `/api/devices/<device_no>` | GET | 通过编号获取设备 |
| `/api/devices/categories` | GET | 设备分类列表 |
| `/api/devices/nearby` | GET | 附近设备 |

### 订单相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/orders/` | GET | 订单列表 |
| `/api/orders/<id>` | GET | 订单详情 |
| `/api/orders/create` | POST | 创建订单 |
| `/api/orders/<id>/pay` | POST | 发起支付 |
| `/api/orders/<id>/deposit-free-auth` | POST | 免押授权 |
| `/api/orders/<id>/unfreeze` | POST | 解冻押金 |
| `/api/orders/<id>/cancel` | POST | 取消订单 |

### 支付宝回调

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/orders/notify/pay` | POST | 支付结果通知 |
| `/api/orders/notify/auth` | POST | 授权结果通知 |
| `/api/orders/notify/unfreeze` | POST | 解冻结果通知 |

## 核心流程说明

### 1. 用户登录流程

```
小程序前端 -> my.getAuthCode -> 获取 auth_code
              |
              v
后端 /api/auth/login <- 用auth_code换取access_token
              |
              v
获取支付宝用户信息 -> 创建/更新用户 -> 返回JWT Token
```

### 2. 免押租赁流程

```
1. 用户选择设备 -> 创建订单（deposit_free=true）
2. 调用 /api/orders/<id>/deposit-free-auth -> 发起免押授权
3. 用户确认授权 -> 支付宝冻结押金（不扣款）
4. 用户支付租金 -> 调用 /api/orders/<id>/pay
5. 支付宝回调通知 -> 更新订单状态
6. 租赁结束 -> 调用 /api/orders/<id>/unfreeze -> 解冻押金
```

### 3. 普通租赁流程（需押金）

```
1. 用户选择设备 -> 创建订单（deposit_free=false）
2. 订单总金额 = 租金 + 押金
3. 调用 /api/orders/<id>/pay -> 支付总金额
4. 支付宝回调通知 -> 更新订单状态
5. 租赁结束 -> 退还押金（需额外处理）
```

## 数据库模型

### Customer（客户）
- `alipay_user_id` - 支付宝用户ID
- `phone` - 手机号
- `credit_score` - 芝麻信用分
- `deposit_free_eligible` - 免押资格

### Device（设备）
- `device_no` - 设备编号（唯一）
- `name` - 设备名称
- `daily_price` - 日租金
- `deposit_amount` - 押金金额
- `status` - 状态（available/rented/maintenance/offline）

### Order（订单）
- `order_no` - 订单编号（唯一）
- `customer_id` - 客户ID
- `device_id` - 设备ID
- `start_date/end_date` - 租赁起止日期
- `rental_amount` - 租金总额
- `deposit_amount` - 押金金额
- `deposit_free` - 是否免押
- `auth_no` - 支付宝授权单号
- `status` - 订单状态

## 环境配置说明

### 开发环境
- 使用支付宝沙箱环境
- 数据库使用SQLite
- 开启Debug模式

### 生产环境
- 使用支付宝正式环境
- 数据库使用PostgreSQL
- 关闭Debug模式
- 配置HTTPS
- 设置强密钥

## 注意事项

1. **密钥安全**: 生产环境务必将密钥配置在环境变量中，不要提交到代码仓库
2. **回调地址**: 确保回调地址可从公网访问，且配置了HTTPS
3. **签名验证**: 所有支付宝回调必须验证签名
4. **幂等处理**: 订单创建、支付等操作需做好幂等性处理
5. **事务管理**: 涉及资金的操作使用数据库事务

## 调试工具

```bash
# 健康检查
curl http://localhost:5001/health

# 测试登录（需先获取auth_code）
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"auth_code": "your-auth-code"}'

# 获取设备列表
curl http://localhost:5001/api/devices/

# 测试创建订单（需登录Token）
curl -X POST http://localhost:5001/api/orders/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "device_id": 1,
    "start_date": "2024-01-15",
    "end_date": "2024-01-20",
    "deposit_free": true
  }'
```

## 许可证

MIT License
