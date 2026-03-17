/**
 * API 请求封装
 * 统一处理请求、响应、错误等
 */

// 基础配置
const BASE_URL = 'https://api.example.com'; // 替换为实际API地址
const API_VERSION = 'v1';
const TIMEOUT = 30000;

// 请求拦截器
const requestInterceptor = (options) => {
  // 添加通用请求头
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  
  // 添加授权token
  const token = my.getStorageSync({ key: 'token' }).data;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return { ...options, headers };
};

// 响应拦截器
const responseInterceptor = (res) => {
  // 统一处理响应
  if (res.status >= 200 && res.status < 300) {
    return res.data;
  }
  
  // 处理错误
  const error = new Error(res.data?.message || '请求失败');
  error.code = res.status;
  error.data = res.data;
  throw error;
};

// 统一请求方法
const request = (options) => {
  return new Promise((resolve, reject) => {
    // 应用请求拦截器
    const config = requestInterceptor(options);
    
    my.request({
      url: config.url,
      method: config.method || 'GET',
      data: config.data,
      headers: config.headers,
      timeout: config.timeout || TIMEOUT,
      success: (res) => {
        try {
          const data = responseInterceptor(res);
          resolve(data);
        } catch (error) {
          reject(error);
        }
      },
      fail: (err) => {
        console.error('请求失败:', err);
        reject(new Error('网络请求失败，请检查网络'));
      }
    });
  });
};

// GET 请求
const get = (url, params = {}, options = {}) => {
  const queryString = Object.keys(params)
    .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');
  
  const fullUrl = queryString 
    ? `${BASE_URL}/api/${API_VERSION}${url}?${queryString}`
    : `${BASE_URL}/api/${API_VERSION}${url}`;
  
  return request({
    url: fullUrl,
    method: 'GET',
    ...options
  });
};

// POST 请求
const post = (url, data = {}, options = {}) => {
  return request({
    url: `${BASE_URL}/api/${API_VERSION}${url}`,
    method: 'POST',
    data,
    ...options
  });
};

// PUT 请求
const put = (url, data = {}, options = {}) => {
  return request({
    url: `${BASE_URL}/api/${API_VERSION}${url}`,
    method: 'PUT',
    data,
    ...options
  });
};

// DELETE 请求
const del = (url, options = {}) => {
  return request({
    url: `${BASE_URL}/api/${API_VERSION}${url}`,
    method: 'DELETE',
    ...options
  });
};

// ==================== API 接口定义 ====================

// 用户相关
const userApi = {
  // 登录
  login: (code) => post('/user/login', { code }),
  
  // 获取用户信息
  getUserInfo: () => get('/user/info'),
  
  // 更新用户信息
  updateUserInfo: (data) => put('/user/info', data)
};

// 设备相关
const deviceApi = {
  // 获取设备列表
  getDeviceList: (params) => get('/devices', params),
  
  // 获取设备详情
  getDeviceDetail: (id) => get(`/devices/${id}`),
  
  // 搜索设备
  searchDevices: (keyword) => get('/devices/search', { keyword })
};

// 订单相关
const orderApi = {
  // 获取订单列表
  getOrderList: (params) => get('/orders', params),
  
  // 获取订单详情
  getOrderDetail: (id) => get(`/orders/${id}`),
  
  // 创建订单
  createOrder: (data) => post('/orders', data),
  
  // 取消订单
  cancelOrder: (id) => put(`/orders/${id}/cancel`),
  
  // 支付订单
  payOrder: (id) => post(`/orders/${id}/pay`),
  
  // 确认收货
  confirmReceive: (id) => put(`/orders/${id}/receive`),
  
  // 申请归还
  applyReturn: (id, data) => post(`/orders/${id}/return`, data),
  
  // 评价订单
  reviewOrder: (id, data) => post(`/orders/${id}/review`, data)
};

// 芝麻信用相关
const zmxyApi = {
  // 检查芝麻信用授权状态
  checkZmxyAuth: () => get('/zmxy/status'),
  
  // 发起芝麻信用授权
  zmxyAuth: () => post('/zmxy/auth'),
  
  // 查询芝麻信用分
  getZmxyScore: () => get('/zmxy/score')
};

// 上传相关
const uploadApi = {
  // 上传文件
  uploadFile: (filePath) => {
    return new Promise((resolve, reject) => {
      const token = my.getStorageSync({ key: 'token' }).data;
      
      my.uploadFile({
        url: `${BASE_URL}/api/${API_VERSION}/upload`,
        filePath: filePath,
        fileName: 'file',
        fileType: 'image',
        header: {
          'Authorization': token ? `Bearer ${token}` : ''
        },
        success: (res) => {
          const data = JSON.parse(res.data);
          resolve(data);
        },
        fail: reject
      });
    });
  }
};

// 导出
module.exports = {
  // 基础方法
  request,
  get,
  post,
  put,
  del,
  
  // API 接口
  ...userApi,
  ...deviceApi,
  ...orderApi,
  ...zmxyApi,
  ...uploadApi,
  
  // 配置
  BASE_URL,
  API_VERSION
};
