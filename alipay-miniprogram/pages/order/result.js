// pages/order/result.js
Page({
  data: {
    orderId: '',
    status: '', // success: 成功, fail: 失败, cancel: 取消
    orderInfo: null,
    loading: true
  },

  onLoad(options) {
    const { orderId, status } = options;
    
    this.setData({
      orderId: orderId || '',
      status: status || 'success'
    });
    
    if (orderId) {
      this.loadOrderInfo(orderId);
    } else {
      this.setData({ loading: false });
    }
  },

  onShow() {
    // 页面显示
  },

  // 加载订单信息
  async loadOrderInfo(orderId) {
    this.setData({ loading: true });
    
    try {
      // 实际项目中这里应该调用API获取订单详情
      // const res = await api.getOrderDetail(orderId);
      
      // 模拟数据
      setTimeout(() => {
        const mockOrder = {
          id: orderId,
          deviceName: '索尼 A7M4 全画幅微单',
          deviceImage: 'https://example.com/a7m4.jpg',
          startDate: '2024-01-15',
          endDate: '2024-01-18',
          rentalDays: 3,
          rentalFee: 840,
          deposit: 0,
          totalAmount: 840,
          status: this.data.status === 'success' ? 'paid' : 'pending',
          createTime: '2024-01-15 10:30:00',
          address: '北京市朝阳区某某街道123号'
        };
        
        this.setData({
          orderInfo: mockOrder,
          loading: false
        });
      }, 500);
    } catch (error) {
      console.error('加载订单失败:', error);
      this.setData({ loading: false });
    }
  },

  // 查看订单详情
  onViewOrder() {
    const { orderId } = this.data;
    my.redirectTo({
      url: `/pages/order/list`
    });
  },

  // 返回首页
  onBackHome() {
    my.switchTab({
      url: '/pages/index/index'
    });
  },

  // 重新支付
  onRepay() {
    const { orderId, orderInfo } = this.data;
    
    if (!orderInfo) return;
    
    my.tradePay({
      tradeNO: orderInfo.tradeNo || 'TEST' + Date.now(),
      success: (res) => {
        if (res.resultCode === '9000') {
          this.setData({
            status: 'success'
          });
          this.loadOrderInfo(orderId);
        }
      },
      fail: (err) => {
        console.error('支付失败:', err);
        my.showToast({
          content: '支付失败',
          type: 'fail'
        });
      }
    });
  },

  // 取消订单
  onCancelOrder() {
    my.confirm({
      title: '提示',
      content: '确定要取消该订单吗？',
      success: (res) => {
        if (res.confirm) {
          // 调用取消订单API
          my.showToast({
            content: '订单已取消',
            type: 'success'
          });
          setTimeout(() => {
            my.switchTab({
              url: '/pages/order/list'
            });
          }, 1500);
        }
      }
    });
  },

  // 联系客服
  onContactService() {
    my.makePhoneCall({
      number: '400-123-4567'
    });
  }
});
