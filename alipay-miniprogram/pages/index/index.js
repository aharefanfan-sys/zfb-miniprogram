// pages/index/index.js
const api = require('../../utils/api');
const auth = require('../../utils/auth');

Page({
  data: {
    devices: [],
    categories: [
      { id: 'all', name: '全部' },
      { id: 'camera', name: '相机' },
      { id: 'lens', name: '镜头' },
      { id: 'drone', name: '无人机' },
      { id: 'gopro', name: '运动相机' },
    ],
    currentCategory: 'all',
    loading: false,
    hasMore: true,
    page: 1,
    pageSize: 10,
    userInfo: null,
    isLogin: false,
    bannerList: [
      { id: 1, image: 'https://example.com/banner1.jpg', url: '' },
      { id: 2, image: 'https://example.com/banner2.jpg', url: '' },
    ]
  },

  onLoad() {
    // 页面加载时执行
    this.checkLoginStatus();
    this.loadDevices();
  },

  onShow() {
    // 页面显示时执行
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 0
      });
    }
  },

  onPullDownRefresh() {
    // 下拉刷新
    this.setData({
      page: 1,
      devices: [],
      hasMore: true
    }, () => {
      this.loadDevices(() => {
        my.stopPullDownRefresh();
      });
    });
  },

  onReachBottom() {
    // 上拉加载更多
    if (this.data.hasMore && !this.data.loading) {
      this.loadMoreDevices();
    }
  },

  // 检查登录状态
  async checkLoginStatus() {
    const isLogin = await auth.checkLogin();
    this.setData({ isLogin });
    
    if (isLogin) {
      const userInfo = auth.getUserInfo();
      this.setData({ userInfo });
    }
  },

  // 加载设备列表
  async loadDevices(callback) {
    if (this.data.loading) return;
    
    this.setData({ loading: true });
    
    try {
      const { currentCategory, page, pageSize } = this.data;
      const params = {
        page,
        pageSize,
        category: currentCategory === 'all' ? '' : currentCategory
      };
      
      const res = await api.getDeviceList(params);
      
      if (res.code === 200) {
        const devices = res.data.list || [];
        const total = res.data.total || 0;
        
        this.setData({
          devices: page === 1 ? devices : [...this.data.devices, ...devices],
          hasMore: this.data.devices.length + devices.length < total,
          loading: false
        });
      } else {
        my.showToast({
          content: res.message || '加载失败',
          type: 'fail'
        });
        this.setData({ loading: false });
      }
    } catch (error) {
      console.error('加载设备列表失败:', error);
      // 使用模拟数据
      this.setMockData();
      this.setData({ loading: false });
    }
    
    if (callback) callback();
  },

  // 加载更多设备
  loadMoreDevices() {
    this.setData({
      page: this.data.page + 1
    }, () => {
      this.loadDevices();
    });
  },

  // 设置模拟数据
  setMockData() {
    const mockDevices = [
      {
        id: 1,
        name: '索尼 A7M4 全画幅微单',
        category: 'camera',
        brand: 'Sony',
        model: 'A7M4',
        image: 'https://example.com/a7m4.jpg',
        price: 280,
        deposit: 5000,
        useZmxy: true,
        zmxyDeposit: 0,
        stock: 5,
        description: '3300万像素全画幅传感器，支持4K 60P视频录制',
        tags: ['免押金', '热门']
      },
      {
        id: 2,
        name: '佳能 EOS R6 全画幅专微',
        category: 'camera',
        brand: 'Canon',
        model: 'EOS R6',
        image: 'https://example.com/r6.jpg',
        price: 320,
        deposit: 6000,
        useZmxy: true,
        zmxyDeposit: 0,
        stock: 3,
        description: '2010万像素，8级防抖，支持4K 60P',
        tags: ['免押金']
      },
      {
        id: 3,
        name: '大疆 DJI Air 3 无人机',
        category: 'drone',
        brand: 'DJI',
        model: 'Air 3',
        image: 'https://example.com/air3.jpg',
        price: 200,
        deposit: 4000,
        useZmxy: true,
        zmxyDeposit: 0,
        stock: 8,
        description: '双主摄，46分钟续航，全向避障',
        tags: ['免押金', '新品']
      },
      {
        id: 4,
        name: '索尼 FE 24-70mm F2.8 GM II',
        category: 'lens',
        brand: 'Sony',
        model: '24-70GM II',
        image: 'https://example.com/2470gm2.jpg',
        price: 180,
        deposit: 3000,
        useZmxy: true,
        zmxyDeposit: 0,
        stock: 4,
        description: '二代大三元标准变焦镜头，轻量化设计',
        tags: ['免押金']
      },
      {
        id: 5,
        name: 'GoPro Hero 12 Black',
        category: 'gopro',
        brand: 'GoPro',
        model: 'Hero 12',
        image: 'https://example.com/gopro12.jpg',
        price: 80,
        deposit: 1500,
        useZmxy: true,
        zmxyDeposit: 0,
        stock: 10,
        description: '5.3K视频，HyperSmooth 6.0防抖',
        tags: ['免押金']
      }
    ];
    
    this.setData({
      devices: mockDevices,
      hasMore: false,
      loading: false
    });
  },

  // 切换分类
  onCategoryTap(e) {
    const id = e.currentTarget.dataset.id;
    this.setData({
      currentCategory: id,
      page: 1,
      devices: [],
      hasMore: true
    }, () => {
      this.loadDevices();
    });
  },

  // 跳转到设备详情
  onDeviceTap(e) {
    const id = e.currentTarget.dataset.id;
    my.navigateTo({
      url: `/pages/device/detail?id=${id}`
    });
  },

  // 立即租赁
  onRentTap(e) {
    const id = e.currentTarget.dataset.id;
    my.navigateTo({
      url: `/pages/order/create?deviceId=${id}`
    });
  },

  // 登录
  async onLoginTap() {
    try {
      const userInfo = await auth.login();
      this.setData({
        userInfo,
        isLogin: true
      });
      my.showToast({
        content: '登录成功',
        type: 'success'
      });
    } catch (error) {
      my.showToast({
        content: '登录失败',
        type: 'fail'
      });
    }
  },

  // 搜索
  onSearchInput(e) {
    const keyword = e.detail.value;
    // 实现搜索功能
    console.log('搜索:', keyword);
  }
});
