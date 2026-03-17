// app.js - 支付宝小程序入口
App({
  onLaunch(options) {
    // 小程序启动时执行
    console.log('App Launch', options);
    
    // 检查更新
    this.checkForUpdate();
    
    // 初始化全局数据
    this.globalData.systemInfo = my.getSystemInfoSync();
  },

  onShow(options) {
    // 小程序显示时执行
    console.log('App Show', options);
  },

  onHide() {
    // 小程序隐藏时执行
    console.log('App Hide');
  },

  onError(msg) {
    // 小程序出错时执行
    console.log('App Error', msg);
    my.alert({
      title: '提示',
      content: '系统出现错误，请稍后重试'
    });
  },

  // 检查小程序更新
  checkForUpdate() {
    const updateManager = my.getUpdateManager();
    if (updateManager) {
      updateManager.onCheckForUpdate((res) => {
        console.log('是否有新版本:', res.hasUpdate);
      });
      
      updateManager.onUpdateReady(() => {
        my.confirm({
          title: '更新提示',
          content: '新版本已经准备好，是否重启应用？',
          success: (res) => {
            if (res.confirm) {
              updateManager.applyUpdate();
            }
          }
        });
      });
    }
  },

  // 全局数据
  globalData: {
    userInfo: null,
    systemInfo: null,
    baseUrl: 'https://api.example.com', // 替换为实际的API地址
    apiVersion: 'v1',
    // 芝麻信用相关配置
    zmxyConfig: {
      appId: 'your-app-id', // 芝麻信用应用ID
      merchantId: 'your-merchant-id', // 商户ID
    }
  }
});
