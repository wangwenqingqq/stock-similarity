import request from '@/utils/request'

// 计算股票相似性
export function calculateStockSimilarity(data) {
  console.log('发送相似性计算请求参数:', data);
  return request({
    url: '/system/stockSimilarity/calculate',
    method: 'post',
    data: data,
    timeout: 60000 // 设置超时时间为1分钟
  }).then(res => {
    console.log('相似性计算API响应:', res);
    return res;
  }).catch(err => {
    console.error('相似性计算API请求失败:', err);
    throw err;
  });
}
// 获取股票列表
export function getStockList() {
  return request({
    url: '/system/stockSimilarity/list',
    method: 'get'
  }).then(res => {
    console.log('获取股票列表API响应:', res);
    return res;
  }).catch(err => {
    console.error('获取股票列表API请求失败:', err);
    throw err;
  });
}

// 获取股票历史数据
export function getStockHistory(stockCode, startDate, endDate) {
  const params = {
    stockCode: stockCode,
    startDate: startDate,
    endDate: endDate
  };
  console.log('发送获取历史数据请求参数:', params);
  return request({
    url: '/system/stockSimilarity/history',
    method: 'get',
    params: params
  }).then(res => {
    console.log('获取历史数据API响应:', res);
    return res;
  }).catch(err => {
    console.error('获取历史数据API请求失败:', err);
    throw err;
  });
}