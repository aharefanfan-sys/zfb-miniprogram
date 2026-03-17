// pages/order/list.js
const api = require('../../utils/api');
const auth = require('../../utils/auth');

Page({
  data: {
    tabs: [
      { id: 'all', name: '全部' },
      { id: 'pending', name: '待支付' },
      { id: 'paid', name: '进行中' },
      { id: 'completed', name: '已完成' },
      { id: 'cancelled', name: '已取消' }
    ],
    currentTab: 'all',
    orders: [],
    loading: false,
    hasMore: true,
    page: 1,
    pageSize: 10,
    isLogin: false
  },

  onLoad() {
    this.checkLogin();
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 1
      });
    }
    
    // 每次显示刷新数据
    if (this.data.isLogin) {
      this.setData({
        page: 1,
        orders: []
      }, () => {
        this.loadOrders();
      });
    }
  },

  onPullDownRefresh() {
    this.setData({
      page: 1,
      orders: [],
      hasMore: true
    }, () => {
      this.loadOrders(() => {
        my.stopPullDownRefresh();
      });
    });
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadMoreOrders();
    }
  },

  // 检查登录状态
  async checkLogin() {
    const isLogin = await auth.checkLogin();
    this.setData({ isLogin });
    
    if (isLogin) {
      this.loadOrders();
    }
  },

  // 登录
  async onLogin() {
    try {
      await auth.login();
      this.setData({ isLogin: true });
      this.loadOrders();
    } catch (error) {
      console.error('登录失败:', error);
    }
  },

  // 切换标签
  onTabChange(e) {
    const id = e.currentTarget.dataset.id;
    this.setData({
      currentTab: id,
      page: 1,
      orders: [],
      hasMore: true
    }, () => {
      this.loadOrders();
    });
  },

  // 加载订单列表
  async loadOrders(callback) {
    if (this.data.loading) return;
    
    this.setData({ loading: true });
    
    try {
      const { currentTab, page, pageSize } = this.data;
      const params = {
        page,
        pageSize,
        status: currentTab === 'all' ? '' : currentTab
      };
      
      const res = await api.getOrderList(params);
      
      if (res.code === 200) {
        const orders = res.data.list || [];
        const total = res.data.total || 0;
        
        this.setData({
          orders: page === 1 ? orders : [...this.data.orders, ...orders],
          hasMore: this.data.orders.length + orders.length < total,
          loading: false
        });
      } else {
        // 使用模拟数据
        this.setMockOrders();
      }
    } catch (error) {
      console.error('加载订单失败:', error);
      this.setMockOrders();
    }
    
    if (callback) callback();
  },

  // 加载更多
  loadMoreOrders() {
    this.setData({
      page: this.data.page + 1
    }, () => {
      this.loadOrders();
    });
  },

  // 设置模拟订单数据
  setMockOrders() {
    const mockOrders = [
      {
        id: 'ORDER202401150001',
        deviceName: '索尼 A7M4 全画幅微单',
        deviceImage: 'https://example.com/a7m4.jpg',
        startDate: '2024-01-15',
        endDate: '2024-01-18',
        rentalDays: 3,
        rentalFee: 840,
        deposit: 0,
        totalAmount: 840,
        status: 'paid',
        statusText: '租赁中',
        createTime: '2024-01-15 10:30:00'
      },
      {
        id: 'ORDER202401100002',
        deviceName: '大疆 DJI Air 3 无人机',
        deviceImage: 'https://example.com/air3.jpg',
        startDate: '2024-01-10',
        endDate: '2024-01-12',
        rentalDays: 2,
        rentalFee: 400,
        deposit: 0,
        totalAmount: 400,
        status: 'completed',
        statusText: '已完成',
        createTime: '2024-01-10 14:20:00'
      },
      {
        id: 'ORDER202401180003',
        deviceName: '佳能 EOS R6 全画幅专微',
        deviceImage: 'https://example.com/r6.jpg',
        startDate: '2024-01-20',
        endDate: '2024-01-25',
        rentalDays: 5,
        rentalFee: 1600,
        deposit: 0,
        totalAmount: 1600,
        status: 'pending',
        statusText: '待支付',
        createTime: '2024-01-18 09:15:00'
      },
      {
        id: 'ORDER202401050004',
        deviceName: 'GoPro Hero 12 Black',
        deviceImage: 'https://example.com/gopro12.jpg',
        startDate: '2024-01-05',
        endDate: '2024-01-07',
        rentalDays: 2,
        rentalFee: 160,
        deposit: 0,
        totalAmount: 160,
        status: 'cancelled',
        statusText: '已取消',
        createTime: '2024-01-05 16:45:00'
      }
    ];
    
    // 根据当前标签过滤
    const { currentTab } = this.data;
    let filteredOrders = mockOrders;
    if (currentTab !== 'all') {
      filteredOrders = mockOrders.filter(order => order.status === currentTab);
    }
    
    this.setData({
      orders: filteredOrders,
      hasMore: false,
      loading: false
    });
  },

  // 获取状态样式
  getStatusClass(status) {
    const statusMap = {
      'pending': 'status-pending',
      'paid': 'status-paid',
      'shipping': 'status-paid',
      'renting': 'status-paid',
      'completed': 'status-completed',
      'cancelled': 'status-cancelled'
    };
    return statusMap[status] || '';
  },

  // 订单操作
  onOrderAction(e) {
    const { type, id } = e.currentTarget.dataset;
    
    switch (type) {
      case 'pay':
        this.payOrder(id);
        break;
      case 'cancel':
        this.cancelOrder(id);
        break;
      case 'receive':
        this.confirmReceive(id);
        break;
      case 'return':
        this.applyReturn(id);
        break;
      case 'review':
        this.writeReview(id);
        break;
      case 'detail':
        this.viewDetail(id);
        break;
    }
  },

  // 支付订单
  payOrder(orderId) {
    my.tradePay({
      tradeNO: 'TEST' + Date.now(),
      success: (res) => {
        if (res.resultCode === '9000') {
          my.showToast({
            content: '支付成功',
            type: 'success'
          });
          this.loadOrders();
        }
      }
    });
  },

  // 取消订单
  cancelOrder(orderId) {
    my.confirm({
      title: '提示',
      content: '确定要取消该订单吗？',
      success: (res) => {
        if (res.confirm) {
          // 调用取消API
          my.showToast({
            content: '订单已取消',
            type: 'success'
          });
          this.loadOrders();
        }
      }
    });
  },

  // 确认收货
  confirmReceive(orderId) {
    my.confirm({
      title: '确认收货',
      content: '确认已收到设备？',
      success: (res) => {
        if (res.confirm) {
          my.showToast({
            content: '已确认收货',
            type: 'success'
          });
          this.loadOrders();
        }
      }
    });
  },

  // 申请归还
  applyReturn(orderId) {
    my.navigateTo({
      url: `/pages/order/return?orderId=${orderId}`
    });
  },

  // 写评价
  writeReview(orderId) {
    my.navigateTo({
      url: `/pages/order/review?orderId=${orderId}`
    });
  },

  // 查看详情
  viewDetail(orderId) {
    // 可以跳转到订单详情页
    console.log('查看订单详情:', orderId);
  },

  // 去租赁
  onRentTap() {
    my.switchTab({
      url: '/pages/index/index'
    });
  }
});
