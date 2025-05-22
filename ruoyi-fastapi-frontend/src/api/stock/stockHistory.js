import request from '@/utils/request'
import { da } from 'element-plus/es/locale/index.mjs';

// 获取相似性计算查询历史列表
export function getQueryHistoryList(params) {
  console.log('获取查询历史列表参数:', params);
  return request({
    url: '/system/history',
    method: 'get',
    params
  }).then(res => {
    console.log('查询历史列表API响应:', res);
    return res;
  }).catch(err => {
    console.error('查询历史列表API请求失败:', err);
    throw err;
  });
}

export function addQueryHistoryList(data) {
  console.log('获取查询历史列表参数:', data);
  return request({
    url: '/system/history',
    method: 'post',
    data: data
  }).then(res => {
    console.log('新增查询历史响应:', res);
    return res;
  }).catch(err => {
    console.error('新增查询历史求失败:', err);
    throw err;
  });
}

// 获取单个查询历史详情
export function getQueryHistoryDetail(historyId) {
  console.log('获取查询历史详情ID:', historyId);
  return request({
    url: `/system/history/${historyId}`,
    method: 'get'
  }).then(res => {
    console.log('查询历史详情API响应:', res);
    return res;
  }).catch(err => {
    console.error('查询历史详情API请求失败:', err);
    throw err;
  });
}

// 删除查询历史记录
export function deleteQueryHistory(historyId) {
  console.log('删除查询历史ID:', historyId);
  return request({
    url: `/system/history/${historyId}`,
    method: 'delete'
  }).then(res => {
    console.log('删除查询历史API响应:', res);
    return res;
  }).catch(err => {
    console.error('删除查询历史API请求失败:', err);
    throw err;
  });
}

// 批量删除查询历史记录
export function deleteQueryHistoryBatch(historyIds) {
  console.log('批量删除查询历史IDs:', historyIds);
  return request({
    url: '/system/history/batch',
    method: 'delete',
    data: {
      historyIds: historyIds
    }
  }).then(res => {
    console.log('批量删除查询历史API响应:', res);
    return res;
  }).catch(err => {
    console.error('批量删除查询历史API请求失败:', err);
    throw err;
  });
}

// 搜索查询历史（支持模糊搜索）
export function searchQueryHistory(keyword) {
  console.log('搜索查询历史关键词:', keyword);
  return request({
    url: '/system/history/fuzzySearch',
    method: 'get',
    params: {
      keyword: keyword
    }
  }).then(res => {
    console.log('搜索查询历史API响应:', res);
    return res;
  }).catch(err => {
    console.error('搜索查询历史API请求失败:', err);
    throw err;
  });
}

// 获取相似股票详细结果
export function getSimilarStocksDetail(historyId) {
  console.log('获取相似股票详情历史ID:', historyId);
  return request({
    url: `/system/history/result/${historyId}`,
    method: 'get'
  }).then(res => {
    console.log('相似股票详情API响应:', res);
    return res;
  }).catch(err => {
    console.error('相似股票详情API请求失败:', err);
    throw err;
  });
}

// 导出查询历史数据
export function exportQueryHistory(params) {
  console.log('导出查询历史参数:', params);
  return request({
    url: '/system/history/export',
    method: 'post',
    data: params,
    responseType: 'blob'
  }).then(res => {
    console.log('导出查询历史API响应成功');
    return res;
  }).catch(err => {
    console.error('导出查询历史API请求失败:', err);
    throw err;
  });
}

// 获取查询历史统计信息
export function getQueryHistoryStatistics(params) {
  console.log('获取查询历史统计参数:', params);
  return request({
    url: '/system/history/statistics',
    method: 'get',
    params: params
  }).then(res => {
    console.log('查询历史统计API响应:', res);
    return res;
  }).catch(err => {
    console.error('查询历史统计API请求失败:', err);
    throw err;
  });
}

// 获取最近查询记录（用于快速访问）
export function getRecentQueryHistory(limit = 10) {
  console.log('获取最近查询记录数量:', limit);
  return request({
    url: '/system/history/recent',
    method: 'get',
    params: {
      limit: limit
    }
  }).then(res => {
    console.log('最近查询记录API响应:', res);
    return res;
  }).catch(err => {
    console.error('最近查询记录API请求失败:', err);
    throw err;
  });
}

// 清空所有查询历史（需要确认）
export function clearAllQueryHistory() {
  console.log('清空所有查询历史');
  return request({
    url: '/system/history/clear',
    method: 'delete'
  }).then(res => {
    console.log('清空查询历史API响应:', res);
    return res;
  }).catch(err => {
    console.error('清空查询历史API请求失败:', err);
    throw err;
  });
}