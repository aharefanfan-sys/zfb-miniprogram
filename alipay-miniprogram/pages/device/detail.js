// pages/device/detail.js
const api = require('../../utils/api');
const auth = require('../../utils/auth');

Page({
  data: {
    deviceId: null,
    device: null,
    loading: true,
    specifications: [],
    currentImageIndex: 0,
    isFavorite: false
  },

  onLoad(options) {
    const { id } = options;
    if (!id) {
      my.showToast({
        content: '参数错误',
        type: 'fail'
      });
      my.navigateBack();
      return;
    }
    
    this.setData({ deviceId: id });
    this.loadDeviceDetail(id);
    this.checkFavorite(id);
  },

  onShow() {
    // 页面显示
  },

  onShareAppMessage() {
    const { device } = this.data;
    return {
      title: `${device.name} - 芝麻信用免押租赁`,
      desc: device.description,
      path: `/pages/device/detail?id=${device.id}`
    };
  },

  // 加载设备详情
  async loadDeviceDetail(id) {
    this.setData({ loading: true });
    
    try {
      const res = await api.getDeviceDetail(id);
      
      if (res.code === 200) {
        const device = res.data;
        this.setData({
          device,
          specifications: device.specifications || [],
          loading: false
        });
      } else {
        // 使用模拟数据
        this.setMockData(id);
      }
    } catch (error) {
      console.error('加载设备详情失败:', error);
      this.setMockData(id);
    }
  },

  // 设置模拟数据
  setMockData(id) {
    const mockDevice = {
      id: parseInt(id),
      name: '索尼 A7M4 全画幅微单',
      category: 'camera',
      brand: 'Sony',
      model: 'A7M4',
      images: [
        'https://example.com/a7m4-1.jpg',
        'https://example.com/a7m4-2.jpg',
        'https://example.com/a7m4-3.jpg'
      ],
      price: 280,
      deposit: 5000,
      useZmxy: true,
      zmxyDeposit: 0,
      stock: 5,
      description: '索尼 A7M4 是一款专业的全画幅微单相机，配备3300万像素全画幅传感器，支持4K 60P视频录制，具备出色的自动对焦性能和丰富的视频功能。',
      tags: ['免押金', '热门'],
      specifications: [
        { name: '传感器', value: '3300万像素全画幅CMOS' },
        { name: '处理器', value: 'BIONZ XR' },
        { name: '对焦系统', value: '759个相位检测对焦点' },
        { name: '视频规格', value: '4K 60P 10bit 4:2:2' },
        { name: '防抖', value: '5轴机身防抖' },
        { name: '重量', value: '约658g（含电池）' },
        { name: '接口', value: '全尺寸HDMI、USB-C' }
      ],
      rentalRules: [
        '芝麻信用分 ≥ 650 可享受免押金服务',
        '租期最短1天，最长30天',
        '提前归还按实际租期计算费用',
        '逾期归还将收取滞纳金',
        '设备损坏需按维修费用赔偿'
      ],
      accessories: [
        '相机机身 x1',
        '原装电池 x2',
        '充电器 x1',
        '64GB SD卡 x1',
        '相机肩带 x1',
        '相机包 x1'
      ]
    };
    
    this.setData({
      device: mockDevice,
      specifications: mockDevice.specifications,
      loading: false
    });
  },

  // 检查是否已收藏
  checkFavorite(id) {
    // 从本地存储获取收藏状态
    const favorites = my.getStorageSync({ key: 'favorites' }).data || [];
    this.setData({
      isFavorite: favorites.includes(parseInt(id))
    });
  },

  // 收藏/取消收藏
  onFavoriteTap() {
    const { deviceId, isFavorite } = this.data;
    let favorites = my.getStorageSync({ key: 'favorites' }).data || [];
    
    if (isFavorite) {
      favorites = favorites.filter(id => id !== parseInt(deviceId));
      my.showToast({ content: '已取消收藏' });
    } else {
      favorites.push(parseInt(deviceId));
      my.showToast({ content: '已收藏' });
    }
    
    my.setStorageSync({
      key: 'favorites',
      data: favorites
    });
    
    this.setData({ isFavorite: !isFavorite });
  },

  // 图片切换
  onImageChange(e) {
    this.setData({
      currentImageIndex: e.detail.current
    });
  },

  // 预览图片
  onImagePreview(e) {
    const { device, currentImageIndex } = this.data;
    my.previewImage({
      urls: device.images,
      current: device.images[currentImageIndex]
    });
  },

  // 立即租赁
  onRentTap() {
    const { device } = this.data;
    if (device.stock === 0) {
      my.showToast({
        content: '该设备暂时缺货',
        type: 'fail'
      });
      return;
    }
    
    // 检查登录状态
    const isLogin = auth.checkLoginSync();
    if (!isLogin) {
      my.confirm({
        title: '提示',
        content: '请先登录后再租赁',
        confirmButtonText: '去登录',
        success: (res) => {
          if (res.confirm) {
            auth.login().then(() => {
              my.navigateTo({
                url: `/pages/order/create?deviceId=${device.id}`
              });
            });
          }
        }
      });
      return;
    }
    
    my.navigateTo({
      url: `/pages/order/create?deviceId=${device.id}`
    });
  },

  // 联系客服
  onContactTap() {
    my.makePhoneCall({
      number: '400-123-4567'
    });
  },

  // 返回首页
  onHomeTap() {
    my.switchTab({
      url: '/pages/index/index'
    });
  },

  // 页面滚动
  onPageScroll(e) {
    // 可以实现导航栏效果变化
  }
});
