import request from '@/utils/request'

// 查询股票信息列表
export function listStockInfo(query) {
  return request({
    url: '/system/stockInfo/list',
    method: 'get',
    params: query
  })
}

// 查询股票信息详细
export function getStockInfo(stockId) {
  return request({
    url: '/system/stockInfo/' + stockId,
    method: 'get'
  })
}

// 新增股票信息
export function addStockInfo(data) {
  return request({
    url: '/system/stockInfo',
    method: 'post',
    data: data
  })
}

// 修改股票信息
export function updateStockInfo(data) {
  return request({
    url: '/system/stockInfo',
    method: 'put',
    data: data
  })
}

// 删除股票信息
export function delStockInfo(stockId) {
  return request({
    url: '/system/stockInfo/' + stockId,
    method: 'delete'
  })
}