# -*- coding: utf-8 -*-
"""
支付宝SDK封装
支持：用户授权、支付、免押预授权等功能
"""

import json
import base64
import hashlib
import time
import requests
from urllib.parse import quote_plus
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AlipaySDK:
    """支付宝SDK封装"""
    
    def __init__(self, app_id, private_key, alipay_public_key, server_url=None):
        """
        初始化支付宝SDK
        
        :param app_id: 支付宝应用ID
        :param private_key: 应用私钥（RSA2格式）
        :param alipay_public_key: 支付宝公钥
        :param server_url: 支付宝网关地址
        """
        self.app_id = app_id
        self.private_key = self._load_private_key(private_key)
        self.alipay_public_key = self._load_public_key(alipay_public_key)
        self.server_url = server_url or 'https://openapi.alipay.com/gateway.do'
    
    def _load_private_key(self, key_content):
        """加载私钥"""
        if not key_content:
            return None
        
        # 处理PEM格式
        if 'BEGIN RSA PRIVATE KEY' in key_content:
            return serialization.load_pem_private_key(
                key_content.encode('utf-8'),
                password=None
            )
        elif 'BEGIN PRIVATE KEY' in key_content:
            return serialization.load_pem_private_key(
                key_content.encode('utf-8'),
                password=None
            )
        else:
            # 尝试添加PEM头
            key_content = key_content.strip()
            pem_key = f"-----BEGIN RSA PRIVATE KEY-----\n{key_content}\n-----END RSA PRIVATE KEY-----"
            return serialization.load_pem_private_key(
                pem_key.encode('utf-8'),
                password=None
            )
    
    def _load_public_key(self, key_content):
        """加载公钥"""
        if not key_content:
            return None
        
        # 处理PEM格式
        if 'BEGIN PUBLIC KEY' in key_content:
            return serialization.load_pem_public_key(
                key_content.encode('utf-8')
            )
        else:
            # 尝试添加PEM头
            key_content = key_content.strip()
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{key_content}\n-----END PUBLIC KEY-----"
            return serialization.load_pem_public_key(
                pem_key.encode('utf-8')
            )
    
    def _sign(self, params):
        """生成RSA2签名"""
        # 过滤空值和sign字段，按key排序
        filtered_params = {k: v for k, v in params.items() 
                          if v is not None and v != '' and k != 'sign'}
        sorted_params = sorted(filtered_params.items())
        
        # 构建签名字符串
        content = '&'.join([f"{k}={v}" for k, v in sorted_params])
        
        # RSA2签名
        signature = self.private_key.sign(
            content.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _verify(self, params, signature):
        """验证支付宝回调签名"""
        try:
            filtered_params = {k: v for k, v in params.items() 
                              if v is not None and v != '' and k != 'sign'}
            sorted_params = sorted(filtered_params.items())
            content = '&'.join([f"{k}={v}" for k, v in sorted_params])
            
            signature_bytes = base64.b64decode(signature)
            
            self.alipay_public_key.verify(
                signature_bytes,
                content.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    def _build_request_params(self, method, biz_content=None, **kwargs):
        """构建请求参数"""
        params = {
            'app_id': self.app_id,
            'method': method,
            'format': 'JSON',
            'charset': 'utf-8',
            'sign_type': 'RSA2',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
        }
        
        if biz_content:
            params['biz_content'] = json.dumps(biz_content, ensure_ascii=False)
        
        params.update(kwargs)
        
        # 添加签名
        params['sign'] = self._sign(params)
        
        return params
    
    def _request(self, method, biz_content=None, **kwargs):
        """发送支付宝API请求"""
        params = self._build_request_params(method, biz_content, **kwargs)
        
        try:
            response = requests.post(self.server_url, data=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # 解析响应
            response_key = method.replace('.', '_') + '_response'
            if response_key in result:
                data = result[response_key]
                if 'code' in data and data['code'] != '10000':
                    logger.error(f"Alipay API error: {data}")
                    return {
                        'success': False,
                        'code': data.get('code'),
                        'message': data.get('msg', 'Unknown error'),
                        'sub_code': data.get('sub_code'),
                        'sub_message': data.get('sub_msg')
                    }
                return {'success': True, 'data': data}
            
            return {'success': False, 'message': 'Invalid response format', 'raw': result}
        
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {'success': False, 'message': f'Request failed: {str(e)}'}
    
    # ==================== 小程序授权相关 ====================
    
    def alipay_system_oauth_token(self, grant_type, code=None, refresh_token=None):
        """
        换取授权访问令牌
        grant_type: authorization_code / refresh_token
        """
        params = {
            'grant_type': grant_type,
            'code': code,
            'refresh_token': refresh_token
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self._request('alipay.system.oauth.token', params)
    
    def alipay_user_info_share(self, auth_token):
        """获取用户信息"""
        return self._request('alipay.user.info.share', auth_token=auth_token)
    
    # ==================== 芝麻信用相关 ====================
    
    def zhima_credit_score_brief_get(self, alipay_user_id, transaction_id=None):
        """获取芝麻信用分（免押资格评估）"""
        biz_content = {
            'product_code': 'w1010100000000002858',
            'alipay_user_id': alipay_user_id
        }
        if transaction_id:
            biz_content['transaction_id'] = transaction_id
        return self._request('zhima.credit.score.brief.get', biz_content)
    
    # ==================== 支付相关 ====================
    
    def alipay_trade_create(self, out_trade_no, total_amount, subject, buyer_id=None, 
                           notify_url=None, **kwargs):
        """
        统一收单交易创建接口
        用于小程序支付下单
        """
        biz_content = {
            'out_trade_no': out_trade_no,
            'total_amount': str(total_amount),
            'subject': subject,
            'product_code': 'QUICK_MSECURITY_PAY'
        }
        if buyer_id:
            biz_content['buyer_id'] = buyer_id
        
        biz_content.update(kwargs)
        
        params = {}
        if notify_url:
            params['notify_url'] = notify_url
            
        return self._request('alipay.trade.create', biz_content, **params)
    
    def alipay_trade_query(self, out_trade_no=None, trade_no=None):
        """查询订单支付状态"""
        biz_content = {}
        if out_trade_no:
            biz_content['out_trade_no'] = out_trade_no
        if trade_no:
            biz_content['trade_no'] = trade_no
        return self._request('alipay.trade.query', biz_content)
    
    def alipay_trade_refund(self, out_trade_no=None, trade_no=None, refund_amount=None, 
                           out_request_no=None, **kwargs):
        """退款"""
        biz_content = {}
        if out_trade_no:
            biz_content['out_trade_no'] = out_trade_no
        if trade_no:
            biz_content['trade_no'] = trade_no
        if refund_amount:
            biz_content['refund_amount'] = str(refund_amount)
        if out_request_no:
            biz_content['out_request_no'] = out_request_no
            
        biz_content.update(kwargs)
        return self._request('alipay.trade.refund', biz_content)
    
    def alipay_trade_close(self, out_trade_no=None, trade_no=None):
        """关闭订单"""
        biz_content = {}
        if out_trade_no:
            biz_content['out_trade_no'] = out_trade_no
        if trade_no:
            biz_content['trade_no'] = trade_no
        return self._request('alipay.trade.close', biz_content)
    
    # ==================== 免押预授权相关 ====================
    
    def alipay_fund_auth_order_app_freeze(self, out_order_no, out_request_no, amount,
                                          order_title, deposit_product_mode,
                                          service_id, category,
                                          notify_url=None, return_url=None,
                                          payee_user_id=None, pay_timeout=None):
        """
        资金授权冻结接口（小程序免押场景）
        返回 orderStr，前端用 my.tradePay 唤起免押受理台
        """
        biz_content = {
            'out_order_no': out_order_no,
            'out_request_no': out_request_no,
            'order_title': order_title,
            'amount': str(amount),
            'product_code': 'PREAUTH_PAY',
            'deposit_product_mode': deposit_product_mode,
            'extra_param': json.dumps({'category': category, 'serviceId': service_id}, ensure_ascii=False)
        }
        if payee_user_id:
            biz_content['payee_user_id'] = payee_user_id
        if pay_timeout:
            biz_content['pay_timeout'] = pay_timeout

        params = {}
        if notify_url:
            params['notify_url'] = notify_url
        if return_url:
            params['return_url'] = return_url

        return self._request('alipay.fund.auth.order.app.freeze', biz_content, **params)
    
    def alipay_fund_auth_order_freeze(self, out_order_no, out_request_no, amount,
                                     order_title, buyer_id=None, notify_url=None,
                                     return_url=None, payee_user_id=None):
        """
        资金授权冻结接口（小程序场景）
        """
        biz_content = {
            'out_order_no': out_order_no,
            'out_request_no': out_request_no,
            'order_title': order_title,
            'amount': str(amount),
            'product_code': 'PRE_AUTH_ONLINE'
        }
        if buyer_id:
            biz_content['buyer_id'] = buyer_id
        if payee_user_id:
            biz_content['payee_user_id'] = payee_user_id
            
        params = {}
        if notify_url:
            params['notify_url'] = notify_url
        if return_url:
            params['return_url'] = return_url
            
        return self._request('alipay.fund.auth.order.freeze', biz_content, **params)
    
    def alipay_fund_auth_order_unfreeze(self, auth_no, out_request_no, amount, 
                                       remark, notify_url=None):
        """
        资金授权解冻接口
        用于归还设备后解冻押金
        """
        biz_content = {
            'auth_no': auth_no,
            'out_request_no': out_request_no,
            'amount': str(amount),
            'remark': remark
        }
        
        params = {}
        if notify_url:
            params['notify_url'] = notify_url
            
        return self._request('alipay.fund.auth.order.unfreeze', biz_content, **params)
    
    def alipay_fund_auth_operation_detail_query(self, auth_no=None, out_order_no=None,
                                                operation_id=None, out_request_no=None):
        """查询授权明细"""
        biz_content = {}
        if auth_no:
            biz_content['auth_no'] = auth_no
        if out_order_no:
            biz_content['out_order_no'] = out_order_no
        if operation_id:
            biz_content['operation_id'] = operation_id
        if out_request_no:
            biz_content['out_request_no'] = out_request_no
        return self._request('alipay.fund.auth.operation.detail.query', biz_content)
    
    def alipay_fund_auth_order_voucher_create(self, out_order_no, out_request_no, amount,
                                             order_title, notify_url=None, return_url=None,
                                             payee_user_id=None):
        """
        资金授权发码接口
        用于生成授权二维码
        """
        biz_content = {
            'out_order_no': out_order_no,
            'out_request_no': out_request_no,
            'order_title': order_title,
            'amount': str(amount),
            'product_code': 'PRE_AUTH_ONLINE'
        }
        if payee_user_id:
            biz_content['payee_user_id'] = payee_user_id
            
        params = {}
        if notify_url:
            params['notify_url'] = notify_url
        if return_url:
            params['return_url'] = return_url
            
        return self._request('alipay.fund.auth.order.voucher.create', biz_content, **params)
    
    # ==================== 芝麻信用借还订单（租赁专属）====================

    def zhima_merchant_order_rent_create(self, out_order_no, user_id, service_id,
                                         borrow_time, expiry_time, deposit_amount,
                                         rent_amount, goods_name):
        """
        创建芝麻信用借还订单（租赁必须，步骤3）
        返回 order_no（芝麻侧订单号），后续完结/取消必须使用
        """
        biz_content = {
            'out_order_no': out_order_no,
            'user_id': user_id,
            'service_id': service_id,
            'borrow_time': borrow_time,
            'expiry_time': expiry_time,
            'deposit_amount': str(deposit_amount),
            'rent_amount': str(rent_amount),
            'goods_name': goods_name
        }
        return self._request('zhima.merchant.order.rent.create', biz_content)

    def zhima_merchant_order_rent_complete(self, order_no, pay_amount,
                                           restore_time, pay_amount_type='RENT'):
        """
        订单完结接口（归还后扣款+信用闭环，一单只能调一次）
        pay_amount_type: RENT-租金, DAMAGE-赔偿金
        """
        biz_content = {
            'order_no': order_no,
            'pay_amount': str(pay_amount),
            'pay_amount_type': pay_amount_type,
            'restore_time': restore_time
        }
        return self._request('zhima.merchant.order.rent.complete', biz_content)

    def zhima_merchant_order_rent_cancel(self, order_no, out_order_no=None):
        """取消芝麻借还订单，释放信用额度"""
        biz_content = {'order_no': order_no}
        if out_order_no:
            biz_content['out_order_no'] = out_order_no
        return self._request('zhima.merchant.order.rent.cancel', biz_content)

    def zhima_merchant_single_data_upload(self, order_no, borrow_time, user_id,
                                          goods_name, status, restore_time=None,
                                          overdue_time=None, memo=None):
        """
        信用数据同步（官方强制，影响用户芝麻分）
        status: BORROW-借出, RETURN-归还, OVERDUE-逾期, SETTLE-结清, BREACH-违约
        """
        biz_content = {
            'order_no': order_no,
            'borrow_time': borrow_time,
            'user_id': user_id,
            'goods_name': goods_name,
            'status': status
        }
        if restore_time:
            biz_content['restore_time'] = restore_time
        if overdue_time:
            biz_content['overdue_time'] = overdue_time
        if memo:
            biz_content['memo'] = memo
        return self._request('zhima.merchant.single.data.upload', biz_content)

    # ==================== 回调��知验证 ====================
    
    def verify_notify(self, params):
        """验证异步通知签名"""
        if 'sign' not in params:
            return False
        
        sign = params.pop('sign')
        sign_type = params.pop('sign_type', 'RSA2')
        
        if sign_type != 'RSA2':
            logger.warning(f"Unsupported sign type: {sign_type}")
            return False
        
        return self._verify(params, sign)


# 工厂函数
def create_alipay_sdk(config):
    """从配置创建支付宝SDK实例"""
    return AlipaySDK(
        app_id=config.get('ALIPAY_APP_ID'),
        private_key=config.get('ALIPAY_PRIVATE_KEY'),
        alipay_public_key=config.get('ALIPAY_PUBLIC_KEY'),
        server_url=config.get('ALIPAY_SERVER_URL')
    )
