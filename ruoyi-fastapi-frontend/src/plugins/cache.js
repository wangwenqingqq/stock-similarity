const sessionCache = {
   // 设置会话存储中的键值对
  set (key, value) {
     // 检查浏览器是否支持 sessionStorage
    if (!sessionStorage) {
      return
    }
    if (key != null && value != null) {
      // 将键值对存储到 sessionStorage 中
      sessionStorage.setItem(key, value)
    }
  },
   // 获取会话存储中指定键的值
  get (key) {
    if (!sessionStorage) {
      return null
    }
    if (key == null) {
      return null
    }
    // 从 sessionStorage 中获取指定键的值
    return sessionStorage.getItem(key)
  },
  setJSON (key, jsonValue) {
    if (jsonValue != null) {
      // 将 JSON 对象转换为字符串后调用 set 方法存储
      this.set(key, JSON.stringify(jsonValue))
    }
  },
  // 获取会话存储中指定键的 JSON 对象
  getJSON (key) {
    const value = this.get(key)
    if (value != null) {
      return JSON.parse(value)
    }
    return null
  },
  // 从会话存储中移除指定键的值
  remove (key) {
    sessionStorage.removeItem(key);
  }
}
const localCache = {
  set (key, value) {
    if (!localStorage) {
      return
    }
    if (key != null && value != null) {
      localStorage.setItem(key, value)
    }
  },
  get (key) {
    if (!localStorage) {
      return null
    }
    if (key == null) {
      return null
    }
    return localStorage.getItem(key)
  },
  setJSON (key, jsonValue) {
    if (jsonValue != null) {
      this.set(key, JSON.stringify(jsonValue))
    }
  },
  getJSON (key) {
    const value = this.get(key)
    if (value != null) {
      return JSON.parse(value)
    }
    return null
  },
  remove (key) {
    localStorage.removeItem(key);
  }
}

export default {
  /**
   * 会话级缓存
   */
  session: sessionCache,
  /**
   * 本地缓存
   */
  local: localCache
}
