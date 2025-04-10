<!-- StockAnalysis.vue -->
<template>
    <div class="stock-analysis-container">
      <div class="header">
        <h1>股票相似性计算系统</h1>
        <div class="search-box">
          <el-input
            v-model="searchKeyword"
            placeholder="输入股票代码或名称"
            prefix-icon="el-icon-search"
            clearable
            @clear="handleClear"
            @keyup.enter.native="handleSearch"
          ></el-input>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>
      </div>
  
      <el-row :gutter="20">
        <!-- 左侧股票列表 -->
        <el-col :span="8">
          <div class="panel">
            <div class="panel-header">
              <h2>股票列表 (按7日收益率排序)</h2>
              <div class="panel-actions">
                <el-select v-model="sortOrder" placeholder="排序方式" size="small" @change="handleSortChange">
                  <el-option label="7日收益率 高→低" value="desc"></el-option>
                  <el-option label="7日收益率 低→高" value="asc"></el-option>
                </el-select>
              </div>
            </div>
            <el-table
              :data="sortedStockList"
              height="600"
              border
              highlight-current-row
              @current-change="handleStockSelect"
              style="width: 100%"
            >
              <el-table-column prop="code" label="代码" width="100"></el-table-column>
              <el-table-column prop="name" label="名称" width="120"></el-table-column>
              <el-table-column prop="current_price" label="当前价" width="90">
                <template slot-scope="scope">
                  <span>{{ scope.row.current_price.toFixed(2) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="change_percentage" label="涨跌幅" width="90">
                <template slot-scope="scope">
                  <span :class="scope.row.change_percentage >= 0 ? 'up-text' : 'down-text'">
                    {{ (scope.row.change_percentage >= 0 ? '+' : '') + scope.row.change_percentage.toFixed(2) + '%' }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="seven_day_return" label="7日收益率" width="110">
                <template slot-scope="scope">
                  <span :class="scope.row.seven_day_return >= 0 ? 'up-text' : 'down-text'">
                    {{ (scope.row.seven_day_return >= 0 ? '+' : '') + scope.row.seven_day_return.toFixed(2) + '%' }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination">
              <el-pagination
                @current-change="handleCurrentChange"
                :current-page.sync="currentPage"
                :page-size="pageSize"
                layout="total, prev, pager, next"
                :total="totalStocks"
              ></el-pagination>
            </div>
          </div>
        </el-col>
  
        <!-- 右侧K线图和详情 -->
        <el-col :span="16">
          <div class="panel">
            <div class="panel-header">
              <h2 v-if="selectedStock">
                {{ selectedStock.name }} ({{ selectedStock.code }})
                <span :class="selectedStock.change_percentage >= 0 ? 'up-text' : 'down-text'">
                  {{ selectedStock.current_price.toFixed(2) }}
                  {{ (selectedStock.change_percentage >= 0 ? '+' : '') + selectedStock.change_percentage.toFixed(2) + '%' }}
                </span>
              </h2>
              <h2 v-else>请选择股票查看K线图</h2>
              <div class="panel-actions" v-if="selectedStock">
                <el-radio-group v-model="timeRange" size="small" @change="handleTimeRangeChange">
                  <el-radio-button label="day">日K</el-radio-button>
                  <el-radio-button label="week">周K</el-radio-button>
                  <el-radio-button label="month">月K</el-radio-button>
                </el-radio-group>
                <el-button 
                  type="primary" 
                  size="small" 
                  icon="el-icon-refresh" 
                  @click="findSimilarStocks"
                  :disabled="!selectedStock"
                >
                  查找相似股票
                </el-button>
              </div>
            </div>
  
            <!-- K线图区域 -->
            <div class="chart-container" ref="klineChart" v-loading="chartLoading"></div>
  
            <!-- 股票详情信息 -->
            <div class="stock-details" v-if="selectedStock">
              <el-row :gutter="20">
                <el-col :span="8">
                  <div class="detail-item">
                    <div class="label">开盘价</div>
                    <div class="value">{{ selectedStock.open_price.toFixed(2) }}</div>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="detail-item">
                    <div class="label">收盘价</div>
                    <div class="value">{{ selectedStock.close_price.toFixed(2) }}</div>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="detail-item">
                    <div class="label">成交量</div>
                    <div class="value">{{ formatVolume(selectedStock.volume) }}</div>
                  </div>
                </el-col>
              </el-row>
              <el-row :gutter="20">
                <el-col :span="8">
                  <div class="detail-item">
                    <div class="label">最高价</div>
                    <div class="value">{{ selectedStock.high_price.toFixed(2) }}</div>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="detail-item">
                    <div class="label">最低价</div>
                    <div class="value">{{ selectedStock.low_price.toFixed(2) }}</div>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="detail-item">
                    <div class="label">7日收益率</div>
                    <div class="value" :class="selectedStock.seven_day_return >= 0 ? 'up-text' : 'down-text'">
                      {{ (selectedStock.seven_day_return >= 0 ? '+' : '') + selectedStock.seven_day_return.toFixed(2) + '%' }}
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>
  
            <!-- 相似股票列表 -->
            <div class="similar-stocks" v-if="similarStocks.length > 0">
              <h3>相似股票</h3>
              <el-table
                :data="similarStocks"
                border
                highlight-current-row
                @current-change="handleSimilarStockSelect"
                style="width: 100%"
              >
                <el-table-column prop="code" label="代码" width="100"></el-table-column>
                <el-table-column prop="name" label="名称" width="120"></el-table-column>
                <el-table-column prop="similarity" label="相似度" width="100">
                  <template slot-scope="scope">
                    <span>{{ (scope.row.similarity * 100).toFixed(2) + '%' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="seven_day_return" label="7日收益率" width="110">
                  <template slot-scope="scope">
                    <span :class="scope.row.seven_day_return >= 0 ? 'up-text' : 'down-text'">
                      {{ (scope.row.seven_day_return >= 0 ? '+' : '') + scope.row.seven_day_return.toFixed(2) + '%' }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="current_price" label="当前价" width="90">
                  <template slot-scope="scope">
                    <span>{{ scope.row.current_price.toFixed(2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="change_percentage" label="涨跌幅" width="90">
                  <template slot-scope="scope">
                    <span :class="scope.row.change_percentage >= 0 ? 'up-text' : 'down-text'">
                      {{ (scope.row.change_percentage >= 0 ? '+' : '') + scope.row.change_percentage.toFixed(2) + '%' }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </template>
  
  <!-- <script>
  import * as echarts from 'echarts';
  import axios from 'axios';
  
  export default {
    name: 'StockAnalysis',
    data() {
      return {
        searchKeyword: '',
        stockList: [],
        selectedStock: null,
        timeRange: 'day',
        sortOrder: 'desc',
        currentPage: 1,
        pageSize: 20,
        totalStocks: 0,
        chartLoading: false,
        klineChart: null,
        similarStocks: []
      };
    },
    computed: {
      sortedStockList() {
        if (!this.stockList.length) return [];
        
        const list = [...this.stockList];
        if (this.sortOrder === 'desc') {
          return list.sort((a, b) => b.seven_day_return - a.seven_day_return);
        } else {
          return list.sort((a, b) => a.seven_day_return - b.seven_day_return);
        }
      }
    },
    mounted() {
      this.fetchStockList();
      this.initChart();
      
      // 窗口大小变化时调整图表大小
      window.addEventListener('resize', this.resizeChart);
    },
    beforeDestroy() {
      window.removeEventListener('resize', this.resizeChart);
      if (this.klineChart) {
        this.klineChart.dispose();
      }
    },
    methods: {
      // 获取股票列表
      async fetchStockList() {
        try {
          // 这里替换为你的真实API地址
          const response = await axios.get('/api/stocks', {
            params: {
              page: this.currentPage,
              page_size: this.pageSize,
              sort_by: 'seven_day_return',
              sort_order: this.sortOrder,
              keyword: this.searchKeyword || undefined
            }
          });
          
          this.stockList = response.data.items;
          this.totalStocks = response.data.total;
          
          // 如果是第一页且未选择股票，默认选择第一个
          if (this.currentPage === 1 && !this.selectedStock && this.stockList.length > 0) {
            this.handleStockSelect(this.stockList[0]);
          }
        } catch (error) {
          this.$message.error('获取股票列表失败: ' + error.message);
          console.error('获取股票列表失败:', error);
        }
      },
      
      // 初始化图表
      initChart() {
        if (this.$refs.klineChart) {
          this.klineChart = echarts.init(this.$refs.klineChart);
          this.klineChart.setOption({
            title: {
              text: '请选择股票查看K线图',
              left: 'center'
            },
            grid: {
              left: '10%',
              right: '10%',
              bottom: '15%'
            },
            tooltip: {
              trigger: 'axis',
              axisPointer: {
                type: 'cross'
              }
            },
            xAxis: {
              type: 'category',
              data: [],
              scale: true,
              boundaryGap: false,
              axisLine: { onZero: false },
              splitLine: { show: false },
              splitNumber: 20
            },
            yAxis: {
              scale: true,
              splitArea: {
                show: true
              }
            },
            dataZoom: [
              {
                type: 'inside',
                start: 0,
                end: 100
              },
              {
                show: true,
                type: 'slider',
                top: '90%',
                start: 0,
                end: 100
              }
            ],
            series: []
          });
        }
      },
      
      // 加载K线图数据
      async loadKlineData() {
        if (!this.selectedStock) return;
        
        this.chartLoading = true;
        
        try {
          // 这里替换为你的真实API地址
          const response = await axios.get(`/api/stocks/${this.selectedStock.code}/kline`, {
            params: {
              time_range: this.timeRange
            }
          });
          
          const klineData = response.data;
          
          // 更新图表选项
          const option = {
            title: {
              text: `${this.selectedStock.name} (${this.selectedStock.code}) K线图`,
              left: 'center'
            },
            xAxis: {
              data: klineData.categories
            },
            series: [
              {
                name: this.selectedStock.name,
                type: 'candlestick',
                data: klineData.values,
                itemStyle: {
                  color: '#ec0000',
                  color0: '#00da3c',
                  borderColor: '#8A0000',
                  borderColor0: '#008F28'
                }
              },
              {
                name: 'MA5',
                type: 'line',
                data: klineData.ma5,
                smooth: true,
                lineStyle: {
                  opacity: 0.8
                }
              },
              {
                name: 'MA10',
                type: 'line',
                data: klineData.ma10,
                smooth: true,
                lineStyle: {
                  opacity: 0.8
                }
              },
              {
                name: 'MA20',
                type: 'line',
                data: klineData.ma20,
                smooth: true,
                lineStyle: {
                  opacity: 0.8
                }
              }
            ]
          };
          
          // 如果有相似股票，添加相似股票的收盘价线图
          if (this.similarStocks.length > 0) {
            // 最多显示前3个相似股票
            const topSimilarStocks = this.similarStocks.slice(0, 3);
            
            for (const stock of topSimilarStocks) {
              const similarResponse = await axios.get(`/api/stocks/${stock.code}/kline`, {
                params: {
                  time_range: this.timeRange,
                  data_type: 'close' // 只获取收盘价
                }
              });
              
              option.series.push({
                name: `${stock.name} (相似度: ${(stock.similarity * 100).toFixed(2)}%)`,
                type: 'line',
                data: similarResponse.data.close,
                smooth: true,
                symbolSize: 0,
                lineStyle: {
                  width: 1.5
                }
              });
            }
          }
          
          this.klineChart.setOption(option);
        } catch (error) {
          this.$message.error('加载K线图数据失败: ' + error.message);
          console.error('加载K线图数据失败:', error);
        } finally {
          this.chartLoading = false;
        }
      },
      
      // 搜索股票
      handleSearch() {
        this.currentPage = 1;
        this.fetchStockList();
      },
      
      // 清除搜索条件
      handleClear() {
        this.searchKeyword = '';
        this.currentPage = 1;
        this.fetchStockList();
      },
      
      // 选择股票
      handleStockSelect(stock) {
        this.selectedStock = stock;
        this.similarStocks = []; // 清空相似股票列表
        this.loadKlineData();
      },
      
      // 选择相似股票
      handleSimilarStockSelect(stock) {
        this.selectedStock = stock;
        this.loadKlineData();
      },
      
      // 改变时间范围
      handleTimeRangeChange() {
        this.loadKlineData();
      },
      
      // 改变排序方式
      handleSortChange() {
        this.fetchStockList();
      },
      
      // 改变页码
      handleCurrentChange(page) {
        this.currentPage = page;
        this.fetchStockList();
      },
      
      // 查找相似股票
      async findSimilarStocks() {
        if (!this.selectedStock) return;
        
        try {
          // 这里替换为你的真实API地址
          const response = await axios.get(`/api/stocks/${this.selectedStock.code}/similar`);
          this.similarStocks = response.data;
          
          // 更新K线图，包含相似股票的数据
          this.loadKlineData();
          
          this.$message.success('已找到' + this.similarStocks.length + '支相似股票');
        } catch (error) {
          this.$message.error('查找相似股票失败: ' + error.message);
          console.error('查找相似股票失败:', error);
        }
      },
      
      // 调整图表大小
      resizeChart() {
        if (this.klineChart) {
          this.klineChart.resize();
        }
      },
      
      // 格式化成交量
      formatVolume(volume) {
        if (volume >= 100000000) {
          return (volume / 100000000).toFixed(2) + '亿手';
        } else if (volume >= 10000) {
          return (volume / 10000).toFixed(2) + '万手';
        } else {
          return volume + '手';
        }
      }
    }
  };
  </script> -->
  <script>
  import * as echarts from 'echarts';
  import { fetchStockList, loadKlineData, findSimilarStocks } from '@/api/system/stockReturn';
  
  export default {
    name: 'StockAnalysis',
    data() {
      return {
        searchKeyword: '',
        stockList: [],
        selectedStock: null,
        timeRange: 'day',
        sortOrder: 'desc',
        currentPage: 1,
        pageSize: 20,
        totalStocks: 0,
        chartLoading: false,
        klineChart: null,
        similarStocks: []
      };
    },
    computed: {
      sortedStockList() {
        if (!this.stockList.length) return [];
        
        const list = [...this.stockList];
        if (this.sortOrder === 'desc') {
          return list.sort((a, b) => b.seven_day_return - a.seven_day_return);
        } else {
          return list.sort((a, b) => a.seven_day_return - b.seven_day_return);
        }
      }
    },
    mounted() {
      this.fetchStockList();
      this.initChart();
      
      // 窗口大小变化时调整图表大小
      window.addEventListener('resize', this.resizeChart);
    },
    beforeDestroy() {
      window.removeEventListener('resize', this.resizeChart);
      if (this.klineChart) {
        this.klineChart.dispose();
      }
    },
    methods: {
      // 获取股票列表
      async fetchStockList() {
        try {
          const params = {
            page: this.currentPage,
            page_size: this.pageSize,
            sort_by: 'seven_day_return',
            sort_order: this.sortOrder,
            keyword: this.searchKeyword || undefined
          };
          const response = await fetchStockList(params);
          
          this.stockList = response.data.items;
          this.totalStocks = response.data.total;
          
          // 如果是第一页且未选择股票，默认选择第一个
          if (this.currentPage === 1 && !this.selectedStock && this.stockList.length > 0) {
            this.handleStockSelect(this.stockList[0]);
          }
        } catch (error) {
          this.$message.error('获取股票列表失败: ' + error.message);
          console.error('获取股票列表失败:', error);
        }
      },
      
      // 初始化图表
      initChart() {
        if (this.$refs.klineChart) {
          this.klineChart = echarts.init(this.$refs.klineChart);
          this.klineChart.setOption({
            title: {
              text: '请选择股票查看K线图',
              left: 'center'
            },
            grid: {
              left: '10%',
              right: '10%',
              bottom: '15%'
            },
            tooltip: {
              trigger: 'axis',
              axisPointer: {
                type: 'cross'
              }
            },
            xAxis: {
              type: 'category',
              data: [],
              scale: true,
              boundaryGap: false,
              axisLine: { onZero: false },
              splitLine: { show: false },
              splitNumber: 20
            },
            yAxis: {
              scale: true,
              splitArea: {
                show: true
              }
            },
            dataZoom: [
              {
                type: 'inside',
                start: 0,
                end: 100
              },
              {
                show: true,
                type: 'slider',
                top: '90%',
                start: 0,
                end: 100
              }
            ],
            series: []
          });
        }
      },
      
      // 加载K线图数据
      async loadKlineData() {
        if (!this.selectedStock) return;
        
        this.chartLoading = true;
        
        try {
          const params = {
            time_range: this.timeRange
          };
          const response = await loadKlineData(this.selectedStock.code, params);
          
          const klineData = response.data;
          
          // 更新图表选项
          const option = {
            title: {
              text: `${this.selectedStock.name} (${this.selectedStock.code}) K线图`,
              left: 'center'
            },
            xAxis: {
              data: klineData.categories
            },
            series: [
              {
                name: this.selectedStock.name,
                type: 'candlestick',
                data: klineData.values,
                itemStyle: {
                  color: '#ec0000',
                  color0: '#00da3c',
                  borderColor: '#8A0000',
                  borderColor0: '#008F28'
                }
              },
              {
                name: 'MA5',
                type: 'line',
                data: klineData.ma5,
                smooth: true,
                lineStyle: {
                  opacity: 0.8
                }
              },
              {
                name: 'MA10',
                type: 'line',
                data: klineData.ma10,
                smooth: true,
                lineStyle: {
                  opacity: 0.8
                }
              },
              {
                name: 'MA20',
                type: 'line',
                data: klineData.ma20,
                smooth: true,
                lineStyle: {
                  opacity: 0.8
                }
              }
            ]
          };
          
          // 如果有相似股票，添加相似股票的收盘价线图
          if (this.similarStocks.length > 0) {
            // 最多显示前3个相似股票
            const topSimilarStocks = this.similarStocks.slice(0, 3);
            
            for (const stock of topSimilarStocks) {
              const similarParams = {
                time_range: this.timeRange,
                data_type: 'close' // 只获取收盘价
              };
              const similarResponse = await loadKlineData(stock.code, similarParams);
              
              option.series.push({
                name: `${stock.name} (相似度: ${(stock.similarity * 100).toFixed(2)}%)`,
                type: 'line',
                data: similarResponse.data.close,
                smooth: true,
                symbolSize: 0,
                lineStyle: {
                  width: 1.5
                }
              });
            }
          }
          
          this.klineChart.setOption(option);
        } catch (error) {
          this.$message.error('加载K线图数据失败: ' + error.message);
          console.error('加载K线图数据失败:', error);
        } finally {
          this.chartLoading = false;
        }
      },
      
      // 搜索股票
      handleSearch() {
        this.currentPage = 1;
        this.fetchStockList();
      },
      
      // 清除搜索条件
      handleClear() {
        this.searchKeyword = '';
        this.currentPage = 1;
        this.fetchStockList();
      },
      
      // 选择股票
      handleStockSelect(stock) {
        this.selectedStock = stock;
        this.similarStocks = []; // 清空相似股票列表
        this.loadKlineData();
      },
      
      // 选择相似股票
      handleSimilarStockSelect(stock) {
        this.selectedStock = stock;
        this.loadKlineData();
      },
      
      // 改变时间范围
      handleTimeRangeChange() {
        this.loadKlineData();
      },
      
      // 改变排序方式
      handleSortChange() {
        this.fetchStockList();
      },
      
      // 改变页码
      handleCurrentChange(page) {
        this.currentPage = page;
        this.fetchStockList();
      },
      
      // 查找相似股票
      async findSimilarStocks() {
        if (!this.selectedStock) return;
        
        try {
          const response = await findSimilarStocks(this.selectedStock.code);
          this.similarStocks = response.data;
          
          // 更新K线图，包含相似股票的数据
          this.loadKlineData();
          
          this.$message.success('已找到' + this.similarStocks.length + '支相似股票');
        } catch (error) {
          this.$message.error('查找相似股票失败: ' + error.message);
          console.error('查找相似股票失败:', error);
        }
      },
      
      // 调整图表大小
      resizeChart() {
        if (this.klineChart) {
          this.klineChart.resize();
        }
      },
      
      // 格式化成交量
      formatVolume(volume) {
        if (volume >= 100000000) {
          return (volume / 100000000).toFixed(2) + '亿手';
        } else if (volume >= 10000) {
          return (volume / 10000).toFixed(2) + '万手';
        } else {
          return volume + '手';
        }
      }
    }
  };
  </script>
  <style scoped>
  .stock-analysis-container {
    padding: 20px;
    background-color: #f0f2f5;
    min-height: 100vh;
  }
  
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
  
  .search-box {
    display: flex;
    width: 350px;
  }
  
  .search-box .el-input {
    margin-right: 10px;
  }
  
  .panel {
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    padding: 20px;
    margin-bottom: 20px;
  }
  
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
  
  .panel-header h2 {
    margin: 0;
    font-size: 18px;
  }
  
  .chart-container {
    height: 400px;
    width: 100%;
  }
  
  .stock-details {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #eee;
  }
  
  .detail-item {
    text-align: center;
    padding: 10px;
    border-radius: 4px;
    background-color: #f9f9f9;
    height: 100%;
  }
  
  .detail-item .label {
    color: #888;
    font-size: 14px;
    margin-bottom: 5px;
  }
  
  .detail-item .value {
    font-size: 16px;
    font-weight: bold;
  }
  
  .similar-stocks {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #eee;
  }
  
  .similar-stocks h3 {
    margin-top: 0;
    margin-bottom: 15px;
  }
  
  .pagination {
    margin-top: 20px;
    text-align: center;
  }
  
  .up-text {
    color: #f56c6c;
  }
  
  .down-text {
    color: #67c23a;
  }
  
  /* 响应式调整 */
  @media screen and (max-width: 1200px) {
    .el-col-8 {
      width: 100%;
    }
    
    .el-col-16 {
      width: 100%;
    }
  }
  </style>