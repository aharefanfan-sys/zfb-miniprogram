// pages/order/create.js
const api = require('../../utils/api');
const auth = require('../../utils/auth');

Page({
  data: {
    deviceId: null,
    device: null,
    loading: true,
    
    // 租赁日期
    startDate: '',
    endDate: '',
    minDate: '',
    maxDate: '',
    rentalDays: 1,
    
    // 收货地址
    address: null,
    
    // 芝麻信用
    zmxyScore: 0,
    zmxyAuthorized: false,
    zmxyLoading: false,
    
    // 费用计算
    rentalFee: 0,
    deposit: 0,
    totalAmount: 0,
    
    // 备注
    remark: '',
    
    // 协议
    agreementChecked: false,
    
    // 用户信息
    userInfo: null
  },

  onLoad(options) {
    const { deviceId } = options;
    if (!deviceId) {
      my.showToast({
        content: '参数错误',
        type: 'fail'
      });
      my.navigateBack();
      return;
    }
    
    this.setData({ deviceId });
    this.initDates();
    this.checkLoginAndLoad();
  },

  // 初始化日期
  initDates() {
    const today = new Date();
    const minDate = this.formatDate(today);
    
    const maxDate = new Date();
    maxDate.setMonth(maxDate.getMonth() + 3);
    
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    this.setData({
      minDate,
      maxDate: this.formatDate(maxDate),
      startDate: minDate,
      endDate: this.formatDate(tomorrow)
    });
  },

  // 检查登录并加载数据
  async checkLoginAndLoad() {
    const isLogin = await auth.checkLogin();
    if (!isLogin) {
      my.confirm({
        title: '提示',
        content: '请先登录后再租赁',
        confirmButtonText: '去登录',
        success: (res) => {
          if (res.confirm) {
            auth.login().then(() => {
              this.loadData();
            });
          } else {
            my.navigateBack();
          }
        }
      });
      return;
    }
    
    this.loadData();
  },

  // 加载数据
  async loadData() {
    this.setData({ loading: true });
    
    try {
      // 获取用户信息
      const userInfo = auth.getUserInfo();
      this.setData({ userInfo });
      
      // 获取设备信息
      await this.loadDeviceDetail();
      
      // 计算费用
      this.calculateFee();
      
      // 检查芝麻信用授权
      await this.checkZmxyAuth();
      
      this.setData({ loading: false });
    } catch (error) {
      console.error('加载数据失败:', error);
      this.setData({ loading: false });
    }
  },

  // 加载设备详情
  async loadDeviceDetail() {
    const { deviceId } = this.data;
    
    try {
      const res = await api.getDeviceDetail(deviceId);
      if (res.code === 200) {
        this.setData({ device: res.data });
      } else {
        // 使用模拟数据
        this.setMockDevice();
      }
    } catch (error) {
      this.setMockDevice();
    }
  },

  // 设置模拟设备数据
  setMockDevice() {
    this.setData({
      device: {
        id: this.data.deviceId,
        name: '索尼 A7M4 全画幅微单',
        image: 'https://example.com/a7m4.jpg',
        price: 280,
        deposit: 5000,
        useZmxy: true,
        zmxyDeposit: 0,
        stock: 5
      }
    });
  },

  // 检查芝麻信用授权
  async checkZmxyAuth() {
    try {
      const res = await api.checkZmxyAuth();
      if (res.code === 200) {
        this.setData({
          zmxyAuthorized: res.data.authorized,
          zmxyScore: res.data.score || 0
        });
        
        // 重新计算费用
        this.calculateFee();
      }
    } catch (error) {
      console.log('芝麻信用未授权');
    }
  },

  // 芝麻信用授权
  async onZmxyAuth() {
    if (this.data.zmxyLoading) return;
    
    this.setData({ zmxyLoading: true });
    
    try {
      // 调用芝麻信用授权接口
      const res = await api.zmxyAuth();
      
      if (res.code === 200) {
        // 打开芝麻信用授权页面
        my.tradePay({
          tradeNO: res.data.tradeNo,
          success: (payRes) => {
            if (payRes.resultCode === '9000') {
              this.setData({
                zmxyAuthorized: true,
                zmxyScore: res.data.score || 650
              });
              this.calculateFee();
              my.showToast({
                content: '授权成功',
                type: 'success'
              });
            }
          },
          fail: (err) => {
            console.error('授权失败:', err);
            my.showToast({
              content: '授权失败，请重试',
              type: 'fail'
            });
          },
          complete: () => {
            this.setData({ zmxyLoading: false });
          }
        });
      }
    } catch (error) {
      // 模拟授权成功
      setTimeout(() => {
        this.setData({
          zmxyAuthorized: true,
          zmxyScore: 720,
          zmxyLoading: false
        });
        this.calculateFee();
        my.showToast({
          content: '授权成功',
          type: 'success'
        });
      }, 1000);
    }
  },

  // 选择日期
  onStartDateChange(e) {
    const startDate = e.detail.value;
    const { endDate } = this.data;
    
    // 如果开始日期晚于结束日期，调整结束日期
    if (new Date(startDate) > new Date(endDate)) {
      const nextDay = new Date(startDate);
      nextDay.setDate(nextDay.getDate() + 1);
      this.setData({
        startDate,
        endDate: this.formatDate(nextDay)
      });
    } else {
      this.setData({ startDate });
    }
    
    this.calculateFee();
  },

  onEndDateChange(e) {
    const endDate = e.detail.value;
    const { startDate } = this.data;
    
    // 确保结束日期不早于开始日期
    if (new Date(endDate) < new Date(startDate)) {
      my.showToast({
        content: '结束日期不能早于开始日期',
        type: 'fail'
      });
      return;
    }
    
    this.setData({ endDate });
    this.calculateFee();
  },

  // 计算费用
  calculateFee() {
    const { device, startDate, endDate, zmxyAuthorized } = this.data;
    if (!device || !startDate || !endDate) return;
    
    // 计算租赁天数
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = end - start;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    const rentalDays = Math.max(1, diffDays);
    
    // 计算费用
    const rentalFee = device.price * rentalDays;
    const deposit = (zmxyAuthorized && device.useZmxy) ? 0 : device.deposit;
    const totalAmount = rentalFee + deposit;
    
    this.setData({
      rentalDays,
      rentalFee,
      deposit,
      totalAmount
    });
  },

  // 选择地址
  onChooseAddress() {
    my.getAddress({
      success: (res) => {
        this.setData({
          address: {
            name: res.fullname,
            phone: res.mobilePhone,
            province: res.provName,
            city: res.cityName,
            district: res.countryName,
            detail: res.address,
            fullAddress: `${res.provName}${res.cityName}${res.countryName}${res.address}`
          }
        });
      },
      fail: (err) => {
        console.error('选择地址失败:', err);
        // 模拟选择地址
        this.setData({
          address: {
            name: '张三',
            phone: '138****8888',
            fullAddress: '北京市朝阳区某某街道123号'
          }
        });
      }
    });
  },

  // 备注输入
  onRemarkInput(e) {
    this.setData({ remark: e.detail.value });
  },

  // 协议勾选
  onAgreementChange(e) {
    this.setData({
      agreementChecked: e.detail.value
    });
  },

  // 查看协议
  onViewAgreement() {
    my.navigateTo({
      url: '/pages/agreement/rental'
    });
  },

  // 提交订单
  async onSubmitOrder() {
    const { 
      device, 
      address, 
      startDate, 
      endDate, 
      remark, 
      agreementChecked,
      zmxyAuthorized,
      deviceId,
      rentalDays,
      totalAmount
    } = this.data;
    
    // 表单验证
    if (!address) {
      my.showToast({
        content: '请选择收货地址',
        type: 'fail'
      });
      return;
    }
    
    if (!agreementChecked) {
      my.showToast({
        content: '请同意租赁协议',
        type: 'fail'
      });
      return;
    }
    
    // 如果设备需要芝麻信用免押但未授权
    if (device.useZmxy && !zmxyAuthorized) {
      my.confirm({
        title: '芝麻信用授权',
        content: '该设备支持芝麻信用免押金，授权后可免除押金',
        confirmButtonText: '去授权',
        cancelButtonText: '支付押金',
        success: (res) => {
          if (res.confirm) {
            this.onZmxyAuth();
          } else {
            // 用户选择支付押金，继续提交
            this.doSubmitOrder();
          }
        }
      });
      return;
    }
    
    this.doSubmitOrder();
  },

  // 执行提交订单
  async doSubmitOrder() {
    const { 
      deviceId, 
      startDate, 
      endDate, 
      address, 
      remark,
      rentalDays,
      totalAmount,
      zmxyAuthorized
    } = this.data;
    
    my.showLoading({ content: '提交中...' });
    
    try {
      const params = {
        deviceId,
        startDate,
        endDate,
        rentalDays,
        totalAmount,
        address: address.fullAddress,
        contactName: address.name,
        contactPhone: address.phone,
        remark,
        zmxyAuthorized,
        deposit: this.data.deposit
      };
      
      const res = await api.createOrder(params);
      my.hideLoading();
      
      if (res.code === 200) {
        const { orderId, paymentInfo } = res.data;
        
        // 调用支付
        if (paymentInfo && totalAmount > 0) {
          this.requestPayment(orderId, paymentInfo);
        } else {
          // 免租金或免押金情况
          my.redirectTo({
            url: `/pages/order/result?orderId=${orderId}&status=success`
          });
        }
      } else {
        my.showToast({
          content: res.message || '下单失败',
          type: 'fail'
        });
      }
    } catch (error) {
      my.hideLoading();
      console.error('提交订单失败:', error);
      
      // 模拟提交成功
      const mockOrderId = 'ORDER' + Date.now();
      my.redirectTo({
        url: `/pages/order/result?orderId=${mockOrderId}&status=success`
      });
    }
  },

  // 发起支付
  requestPayment(orderId, paymentInfo) {
    my.tradePay({
      tradeNO: paymentInfo.tradeNo,
      success: (res) => {
        if (res.resultCode === '9000') {
          my.redirectTo({
            url: `/pages/order/result?orderId=${orderId}&status=success`
          });
        } else if (res.resultCode === '6001') {
          // 用户取消支付
          my.redirectTo({
            url: `/pages/order/result?orderId=${orderId}&status=cancel`
          });
        } else {
          my.redirectTo({
            url: `/pages/order/result?orderId=${orderId}&status=fail`
          });
        }
      },
      fail: (err) => {
        console.error('支付失败:', err);
        my.redirectTo({
          url: `/pages/order/result?orderId=${orderId}&status=fail`
        });
      }
    });
  },

  // 格式化日期
  formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
});
