import request from '@/utils/request'

// 计算股票相似性
export function calculateStockSimilarity(data) {
  console.log('发送相似性计算请求参数:', data);
  return request({
    url: '/system/stockSimilarity/calculate',
    method: 'post',
    data: data
  }).then(res => {
    console.log('相似性计算API响应:', res);
    return res;
  }).catch(err => {
    console.error('相似性计算API请求失败:', err);
    throw err;
  });
}

// 获取相似性计算方法
export function getSimilarityMethods() {
  return request({
    url: '/system/stockSimilarity/methods',
    method: 'get'
  }).then(res => {
    console.log('获取计算方法API响应:', res);
    return res;
  }).catch(err => {
    console.error('获取计算方法API请求失败:', err);
    throw err;
  });
}

// 获取相似性计算指标
export function getSimilarityIndicators() {
  return request({
    url: '/system/stockSimilarity/indicators',
    method: 'get'
  }).then(res => {
    console.log('获取计算指标API响应:', res);
    return res;
  }).catch(err => {
    console.error('获取计算指标API请求失败:', err);
    throw err;
  });
}

// 获取性能比较数据
export function getPerformanceComparison(params) {
  console.log('发送性能比较请求参数:', params);
  return request({
    url: '/system/stockSimilarity/performanceComparison',
    method: 'get',
    params: params
  }).then(res => {
    console.log('性能比较API响应:', res);
    return res;
  }).catch(err => {
    console.error('性能比较API请求失败:', err);
    throw err;
  });
}

// 生成LLM分析
export function generateLLMAnalysis(data) {
  console.log('发送LLM分析请求参数:', data);
  return request({
    url: '/system/stockSimilarity/llmAnalysis',
    method: 'post',
    data: data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }).then(res => {
    console.log('LLM分析API响应:', res);
    return res;
  }).catch(err => {
    console.error('LLM分析API请求失败:', err);
    throw err;
  });
}

// 获取股票列表
export function getStockList() {
  return request({
    url: '/system/stockInfo/list',
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
    url: '/system/stockInfo/history',
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