// api/system/stockReturn.js
import axios from 'axios';

// 获取股票列表
export const fetchStockList = (params) => {
  return axios.get('/system/stockInfo/stocks', {
    params
  });
};

// 加载K线图数据
export const loadKlineData = (code, params) => {
  return axios.get(`/system/stockInfo/stocks/${code}/kline`, {
    params
  });
};

// 查找相似股票
export const findSimilarStocks = (code) => {
  return axios.get(`/system/stockInfo/stocks/${code}/similar`);
};