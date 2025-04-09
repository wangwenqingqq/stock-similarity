import request from '@/utils/request'

// 查询股票信息列表
export function listStockInfo(query) {
  console.log('发送请求参数:', query);
  return request({
    url: '/system/stockInfo/list',
    method: 'get',
    params: query
  }).then(res => {
    console.log('API原始响应:', res);
    return res;
  }).catch(err => {
    console.error('API请求失败:', err);
    throw err;
  });
}

// 查询股票信息详细
export function getStockInfo(stockId) {
  return request({
    url: '/system/stockInfo/' + stockId,
    method: 'get'
  })
}
