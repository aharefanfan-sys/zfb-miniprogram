/**
 * 授权工具
 * 处理用户登录、授权、信息获取等功能
 */

// 登录状态key
const TOKEN_KEY = 'token';
const USER_INFO_KEY = 'userInfo';
const LOGIN_TIME_KEY = 'loginTime';

// token有效期（7天）
const TOKEN_EXPIRE = 7 * 24 * 60 * 60 * 1000;

/**
 * 检查登录状态
 * @returns {Promise<boolean>}
 */
const checkLogin = () => {
  return new Promise((resolve) => {
    const token = my.getStorageSync({ key: TOKEN_KEY }).data;
    const loginTime = my.getStorageSync({ key: LOGIN_TIME_KEY }).data;
    
    if (!token || !loginTime) {
      resolve(false);
      return;
    }
    
    // 检查token是否过期
    const now = Date.now();
    if (now - loginTime > TOKEN_EXPIRE) {
      // token过期，清除登录信息
      clearLoginInfo();
      resolve(false);
      return;
    }
    
    resolve(true);
  });
};

/**
 * 同步检查登录状态
 * @returns {boolean}
 */
const checkLoginSync = () => {
  const token = my.getStorageSync({ key: TOKEN_KEY }).data;
  const loginTime = my.getStorageSync({ key: LOGIN_TIME_KEY }).data;
  
  if (!token || !loginTime) {
    return false;
  }
  
  const now = Date.now();
  if (now - loginTime > TOKEN_EXPIRE) {
    clearLoginInfo();
    return false;
  }
  
  return true;
};

/**
 * 用户登录
 * @returns {Promise<Object>}
 */
const login = () => {
  return new Promise((resolve, reject) => {
    my.getAuthCode({
      scopes: ['auth_user', 'auth_base'],
      success: (res) => {
        if (res.authCode) {
          // 调用后端登录接口
          handleLogin(res.authCode)
            .then(resolve)
            .catch(reject);
        } else {
          reject(new Error('获取授权码失败'));
        }
      },
      fail: (err) => {
        console.error('登录失败:', err);
        
        // 模拟登录成功（开发测试使用）
        const mockUserInfo = {
          userId: 'USER' + Date.now(),
          nickName: '支付宝用户',
          avatar: 'https://example.com/avatar.jpg',
          phone: '138****8888',
          zmxyScore: 720,
          zmxyAuthorized: true
        };
        
        // 保存登录信息
        saveLoginInfo('MOCK_TOKEN_' + Date.now(), mockUserInfo);
        
        resolve(mockUserInfo);
      }
    });
  });
};

/**
 * 处理登录
 * @param {string} authCode 
 * @returns {Promise<Object>}
 */
const handleLogin = (authCode) => {
  return new Promise((resolve, reject) => {
    // 这里调用后端登录接口
    my.request({
      url: 'https://api.example.com/api/v1/user/login',
      method: 'POST',
      data: { code: authCode },
      success: (res) => {
        if (res.data.code === 200) {
          const { token, userInfo } = res.data.data;
          saveLoginInfo(token, userInfo);
          resolve(userInfo);
        } else {
          reject(new Error(res.data.message || '登录失败'));
        }
      },
      fail: (err) => {
        reject(new Error('网络请求失败'));
      }
    });
  });
};

/**
 * 保存登录信息
 * @param {string} token 
 * @param {Object} userInfo 
 */
const saveLoginInfo = (token, userInfo) => {
  my.setStorageSync({
    key: TOKEN_KEY,
    data: token
  });
  
  my.setStorageSync({
    key: USER_INFO_KEY,
    data: userInfo
  });
  
  my.setStorageSync({
    key: LOGIN_TIME_KEY,
    data: Date.now()
  });
};

/**
 * 清除登录信息
 */
const clearLoginInfo = () => {
  my.removeStorageSync({ key: TOKEN_KEY });
  my.removeStorageSync({ key: USER_INFO_KEY });
  my.removeStorageSync({ key: LOGIN_TIME_KEY });
};

/**
 * 退出登录
 */
const logout = () => {
  clearLoginInfo();
  
  my.showToast({
    content: '已退出登录',
    type: 'success'
  });
};

/**
 * 获取用户信息
 * @returns {Object|null}
 */
const getUserInfo = () => {
  return my.getStorageSync({ key: USER_INFO_KEY }).data;
};

/**
 * 获取Token
 * @returns {string|null}
 */
const getToken = () => {
  return my.getStorageSync({ key: TOKEN_KEY }).data;
};

/**
 * 获取用户手机号
 * @returns {Promise<string>}
 */
const getPhoneNumber = () => {
  return new Promise((resolve, reject) => {
    my.getPhoneNumber({
      success: (res) => {
        if (res.response) {
          // 解密手机号
          resolve(res.response);
        } else {
          reject(new Error('获取手机号失败'));
        }
      },
      fail: (err) => {
        reject(err);
      }
    });
  });
};

/**
 * 更新用户信息
 * @param {Object} userInfo 
 */
const updateUserInfo = (userInfo) => {
  const currentInfo = getUserInfo() || {};
  const newInfo = { ...currentInfo, ...userInfo };
  
  my.setStorageSync({
    key: USER_INFO_KEY,
    data: newInfo
  });
  
  return newInfo;
};

/**
 * 芝麻信用授权
 * @returns {Promise<Object>}
 */
const zmxyAuth = () => {
  return new Promise((resolve, reject) => {
    // 调用芝麻信用授权接口
    my.request({
      url: 'https://api.example.com/api/v1/zmxy/auth',
      method: 'POST',
      header: {
        'Authorization': `Bearer ${getToken()}`
      },
      success: (res) => {
        if (res.data.code === 200) {
          // 更新用户信息的芝麻信用状态
          updateUserInfo({
            zmxyAuthorized: true,
            zmxyScore: res.data.data.score
          });
          resolve(res.data);
        } else {
          reject(new Error(res.data.message || '授权失败'));
        }
      },
      fail: reject
    });
  });
};

/**
 * 检查芝麻信用授权状态
 * @returns {Promise<boolean>}
 */
const checkZmxyAuth = () => {
  return new Promise((resolve) => {
    const userInfo = getUserInfo();
    resolve(userInfo && userInfo.zmxyAuthorized === true);
  });
};

// 导出
module.exports = {
  checkLogin,
  checkLoginSync,
  login,
  logout,
  getUserInfo,
  getToken,
  getPhoneNumber,
  updateUserInfo,
  clearLoginInfo,
  zmxyAuth,
  checkZmxyAuth,
  saveLoginInfo
};
