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