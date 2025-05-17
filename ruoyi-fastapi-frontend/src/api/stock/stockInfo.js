import request from '@/utils/request'

/**
 * 获取股票列表
 * @param {Object} params - 查询参数
 * @returns {Promise} 返回Promise对象
 */
export function getStockList(params) {
  console.log('获取股票列表请求参数:', params);
  return request({
    url: '/system/show/list',
    method: 'get',
    params: params
  }).then(res => {
    console.log('获取股票列表API响应:', res);
    return res;
  }).catch(err => {
    console.error('获取股票列表API请求失败:', err);
    throw err;
  });
}

/**
 * 搜索股票
 * @param {string} keyword - 关键字（股票代码或名称）
 * @returns {Promise} 返回Promise对象
 */
export function searchStocks(keyword) {
  console.log('搜索股票请求参数:', keyword);
  return request({
    url: '/system/show/search',
    method: 'get',
    params: { keyword: keyword }
  }).then(res => {
    console.log('搜索股票API响应:', res);
    return res;
  }).catch(err => {
    console.error('搜索股票API请求失败:', err);
    throw err;
  });
}

/**
 * 获取股票详情
 * @param {string} code - 股票代码
 * @returns {Promise} 返回Promise对象
 */
export function getStockDetail(code) {
  console.log('获取股票详情请求参数:', code);
  return request({
    url: `/system/show/${code}`,
    method: 'get'
  }).then(res => {
    console.log('获取股票详情API响应:', res);
    return res;
  }).catch(err => {
    console.error('获取股票详情API请求失败:', err);
    throw err;
  });
}

/**
 * 获取用户关注的股票列表
 * @returns {Promise} 返回Promise对象
 */
export function getWatchlist() {
  console.log('获取关注列表请求');
  return request({
    url: '/system/show/watchlist',
    method: 'get'
  }).then(res => {
    console.log('获取关注列表API响应:', res);
    return res;
  }).catch(err => {
    console.error('获取关注列表API请求失败:', err);
    throw err;
  });
}

/**
 * 添加股票到关注列表
 * @param {string} stockCode - 股票代码
 * @returns {Promise} 返回Promise对象
 */
export function addToWatchlist(stockCode) {
  console.log('添加关注股票请求参数:', stockCode);
  return request({
    url: '/system/show/watchlist',
    method: 'post',
    data: { stockCode: stockCode }
  }).then(res => {
    console.log('添加关注股票API响应:', res);
    return res;
  }).catch(err => {
    console.error('添加关注股票API请求失败:', err);
    throw err;
  });
}

/**
 * 从关注列表中删除股票
 * @param {string} stockCode - 股票代码
 * @returns {Promise} 返回Promise对象
 */
export function removeFromWatchlist(stockCode) {
  console.log('删除关注股票请求参数:', stockCode);
  return request({
    url: `/system/show/watchlist/${stockCode}`,
    method: 'delete'
  }).then(res => {
    console.log('删除关注股票API响应:', res);
    return res;
  }).catch(err => {
    console.error('删除关注股票API请求失败:', err);
    throw err;
  });
}

/**
 * 清空关注列表
 * @returns {Promise} 返回Promise对象
 */
export function clearWatchlist() {
  console.log('清空关注列表请求');
  return request({
    url: '/system/show/watchlist',  
    method: 'delete'
  }).then(res => {
    console.log('清空关注列表API响应:', res);
    return res;
  }).catch(err => {
    console.error('清空关注列表API请求失败:', err);
    throw err;
  });
}