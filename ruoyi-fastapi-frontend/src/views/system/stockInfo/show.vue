<template>
    <div>
      <table>
        <thead>
          <tr>
            <th>股票代码</th>
            <th>开盘价</th>
            <th>收盘价</th>
            <th>最高价</th>
            <th>最低价</th>
            <th>昨日收盘价</th>
            <th>成交量</th>
            <th>时间戳</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stock in stockList" :key="stock.code">
            <td>{{ stock.code }}</td>
            <td>{{ stock.open }}</td>
            <td>{{ stock.close }}</td>
            <td>{{ stock.high }}</td>
            <td>{{ stock.low }}</td>
            <td>{{ stock.ycp }}</td>
            <td>{{ stock.vol }}</td>
            <td>{{ stock.timestamps }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
  
  <script>
  import axios from 'axios';
  import {listStockInfo} from '@/api/system/stockInfo'; 
  export default {
    data() {
      return {
        stockList: []
      };
    },
    mounted() {
      this.getStockInfo();
    },
    methods: {
      async getStockInfo() {
        this.loading = true;
        this.error = null;
        
        try {
          const response = await listStockInfo({});
          console.log('完整响应:', response);
          
          if (response && response.data) {
            this.stockList = response.data || [];
            
            if (this.stockList.length === 0) {
              console.log('返回的数据为空');
            }
          } else {
            this.error = '响应格式异常';
            console.error(this.error, response);
          }
        } catch (error) {
          this.error = '获取股票信息失败';
          console.error(this.error, error);
        } finally {
          this.loading = false;
        }
      }
    }
  };
  </script>
  <style>
  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
  }
  
  th, td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
  }
  
  th {
    background-color: #f2f2f2;
  }
  </style>