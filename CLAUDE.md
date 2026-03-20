# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在操作此代码库时提供指引。

## 项目概述

这是一个支付宝小程序租赁系统，包含两个模块：
- **`alipay-miniprogram/`** — 前端：支付宝小程序（JavaScript/AXML）
- **`alipay-miniprogram-server/`** — 后端：Flask REST API（Python）

## 后端开发命令

所有命令在 `alipay-miniprogram-server/` 目录下执行：

```bash
# 环境初始化
python -m venv venv
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows
pip install -r requirements-dev.txt

# 复制并配置环境变量
cp .env.example .env

# 启动开发服务器（端口 5001）
python app.py
# 或
bash start.sh

# 启动生产服务器
FLASK_ENV=production bash start.sh  # 使用 Gunicorn，4个 worker

# 运行全部测试
pytest

# 运行单个测试文件
pytest tests/test_auth.py

# 运行单个测试用例
pytest tests/test_auth.py::test_login
```

## 环境变量配置

将 `.env.example` 复制为 `.env`，关键变量说明：
- `FLASK_ENV` — `development`（使用 SQLite）或 `production`（使用 PostgreSQL）
- `ALIPAY_APP_ID`、`ALIPAY_PRIVATE_KEY`、`ALIPAY_PUBLIC_KEY` — 支付宝应用凭证
- `MINIPROGRAM_APP_ID`、`MINIPROGRAM_APP_SECRET` — 小程序 OAuth 凭证
- `DATABASE_URL` — 生产环境 PostgreSQL 连接 URL；开发环境自动使用 SQLite
- `NOTIFY_URL` — 支付宝支付回调的公网 HTTPS 地址
- `ZHIMA_SERVICE_ID` — 芝麻信用服务ID（开放平台 → 我的服务 → 芝麻信用 → 租赁服务获取）
- `ZHIMA_CATEGORY` — 业务类目编码
- `DEPOSIT_PRODUCT_MODE` — 免押模式：`DEPOSIT_ONLY` / `POSTPAY` / `POSTPAY_UNCERTAIN`

## 架构说明

### 后端（Flask）

- **`app.py`** — 应用工厂（`create_app()`），注册蓝图、初始化数据库、全局错误处理
- **`config.py`** — 通过 `FLASK_ENV` 选择 `DevelopmentConfig`/`ProductionConfig`/`TestingConfig`
- **`models.py`** — SQLAlchemy 模型：`Customer`（用户）、`Device`（设备）、`Order`（订单）；Order 含芝麻免押字段：`zhima_order_no`、`complete_status`、`complete_time`、`actual_pay_amount`
- **`alipay_sdk.py`** — 自定义支付宝 SDK：RSA2 签名、OAuth 换取 token、芝麻信用分查询
- **`routes/auth.py`** — `/api/auth/` — 支付宝 OAuth 登录、JWT 签发、个人信息、信用查询
- **`routes/devices.py`** — `/api/devices/` — 设备增删改查、分类列表、基于 Haversine 公式的附近搜索
- **`routes/orders.py`** — `/api/orders/` — 订单生命周期、发起支付、免押授权（`deposit-free-auth`）、订单完结（`complete`）、取消、支付宝异步回调处理
- **`utils/sync_devices.py`** — 设备数据同步独立脚本

### 前端（支付宝小程序）

- **`utils/api.js`** — HTTP 客户端，自动注入 JWT；所有 API 方法定义均在此文件
- **`utils/auth.js`** — 登录状态管理：`my.getAuthCode()` → 后端登录 → token 存储（7天有效期）
- 页面：`index`（设备列表）、`device`（设备详情）、`order/create`（创建订单）、`order/list`（订单列表）、`order/result`（支付结果）

### 核心业务流程

**登录流程：** 前端调用 `my.getAuthCode()` → 将 `auth_code` 发送至 `/api/auth/login` → 后端与支付宝换取用户信息 → 返回 JWT。

**普通租赁：** 创建订单 → `/api/orders/<id>/pay` → 支付宝支付 → 异步回调 `/api/orders/notify/pay` 更新订单状态。

**免押金（芝麻信用）：** 创建订单时传入 `deposit_free=true` → `POST /api/orders/<id>/deposit-free-auth` 创建芝麻借还订单并冻结押金，返回 `orderStr` → 前端用 `my.tradePay({ orderStr })` 唤起受理台 → 支付宝回调 `/api/orders/notify/auth` 写入 `auth_no`，订���状态变为 `active` → 用户归还后调用 `POST /api/orders/<id>/complete` 触发代扣+芝麻信用闭环。

### 数据库

- 开发环境：SQLite，首次运行自动创建
- 生产环境：通过 `DATABASE_URL` 使用 PostgreSQL
- 表结构由应用工厂中的 `db.create_all()` 创建，未使用迁移框架

### 支付宝对接注意事项

- 所有发往支付宝的请求均使用 `ALIPAY_PRIVATE_KEY` 进行 RSA2 签名
- 所有来自支付宝的回调均须使用 `ALIPAY_PUBLIC_KEY` 验签
- 沙箱环境与生产环境通过 `config.py` 中的 `FLASK_ENV` 切换（网关 URL 不同）
- 支付回调需要可公网访问的 `NOTIFY_URL`（开发时可使用 ngrok）
