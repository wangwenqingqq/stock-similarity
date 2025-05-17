import request from '@/utils/request'

// 获取股票列表
export function fetchStockList(params) {
  console.log('获取股票列表请求参数:', params);
  return request({
    url: '/system/return/list',
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

// 加载K线图数据
export function loadKlineData( stockCode, params) {
  console.log('加载K线图数据请求参数:', {  params });
  return request({
    url: `/system/return/kline/${stockCode}`,
    method: 'get',
    params: params
  }).then(res => {
    console.log('加载K线图数据API响应:', res);
    return res;
  }).catch(err => {
    console.error('加载K线图数据API请求失败:', err);
    throw err;
  });
}

// 查找相似股票
export function findSimilarStocks(stockCode) {
  console.log('查找相似股票请求参数:', { stockCode });
  return request({
    url: `/system/return/similar/${stockCode}`,
    method: 'get'
  }).then(res => {
    console.log('查找相似股票API响应:', res);
    return res;
  }).catch(err => {
    console.error('查找相似股票API请求失败:', err);
    throw err;
  });
}