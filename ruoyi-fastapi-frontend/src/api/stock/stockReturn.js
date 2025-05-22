// src/api/stock/stockReturn.js

import request from '@/utils/request'

// 处理JSON不兼容的浮点数值
function sanitizeData(data) {
  // 如果不是对象或数组，直接处理
  if (typeof data !== 'object' || data === null) {
    if (typeof data === 'number' && !isFinite(data)) {
      return null; // 将 NaN/Infinity/-Infinity 替换为 null
    }
    return data;
  }
  
  // 处理数组
  if (Array.isArray(data)) {
    return data.map(item => sanitizeData(item));
  }
  
  // 处理对象
  const result = {};
  for (const key in data) {
    if (Object.prototype.hasOwnProperty.call(data, key)) {
      result[key] = sanitizeData(data[key]);
    }
  }
  
  return result;
}

// 处理响应数据
function handleResponse(res) {
  if (res && res.data) {
    res.data = sanitizeData(res.data);
  }
  return res;
}

// 获取股票列表
export function fetchStockList(params) {
  // console.log('获取股票列表请求参数:', params);
  return request({
    url: '/system/return/list',
    method: 'get',
    params: sanitizeData(params) // 确保请求参数也是合法的
  }).then(res => {
    // console.log('获取股票列表API响应:', res);
    return handleResponse(res);
  }).catch(err => {
    console.error('获取股票列表API请求失败:', err);
    throw err;
  });
}


export function loadKlineData(stockCode, params) {
  // console.log('加载K线图数据请求参数:', { stock_code, params });
  
  return request({
    url: `/system/return/kline/${stockCode}`,
    method: 'get',
    params: sanitizeData(params) // 确保请求参数是合法的
  }).then(res => {
    // console.log('加载K线图数据API响应:', res);
    return handleResponse(res);
  }).catch(err => {
    console.error('加载K线图数据API请求失败:', err);
  });
}
  
