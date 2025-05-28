<template>
  <div class="stock-analysis-container">
    <!-- 头部标题和搜索框 -->
    <div class="header">
      <h1>股票相似性计算系统</h1>
      <div class="search-box">
        <el-autocomplete
          v-model="searchKeyword"
          :fetch-suggestions="querySearchAsync"
          placeholder="输入股票代码或名称"
          :prefix-icon="Search"
          clearable
          @clear="handleClear"
          @select="handleAutoSelect"
          style="width: 250px;"
        ></el-autocomplete>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>
    </div>

    <!-- 上部分：股票列表 -->
    <div class="panel stock-list-panel">
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
        height="300"
        border
        highlight-current-row
        @current-change="handleStockSelect"
        style="width: 100%"
        v-loading="tableLoading"
      >
        <el-table-column prop="code" label="代码" width="120"></el-table-column>
        <el-table-column prop="name" label="名称" width="180"></el-table-column>
        <el-table-column prop="price" label="当前价" width="120">
          <template #default="{ row }">
            <span v-if="row && row.price !== undefined">{{ (parseFloat(row.price) || 0).toFixed(2) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="change_rate" label="涨跌幅" width="120">
          <template #default="{ row }">
            <span 
              v-if="row && row.change_rate !== undefined && row.change_rate !== null" 
              :class="row.change_rate >= 0 ? 'up-text' : 'down-text'"
            >
              {{ (row.change_rate >= 0 ? '+' : '') + (parseFloat(row.change_rate) || 0).toFixed(2) + '%' }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="seven_day_return" label="7日收益率" min-width="120">
          <template #default="{ row }">
            <span 
              v-if="row && row.seven_day_return !== undefined" 
              :class="row.seven_day_return >= 0 ? 'up-text' : 'down-text'"
            >
              {{ formatPercentage(row.seven_day_return) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <!-- 添加关注按钮列 -->
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              v-if="!isWatched(row)"
              size="small"
              type="danger"
              @click="handleAddToWatchlist(row)"
              :loading="row.addingToWatchlist"
            >
              关注
            </el-button>
            <el-button
              v-else
              size="small"
              type="warning"
              disabled
            >
              已关注
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination
          @current-change="handleCurrentChange"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="totalStocks"
        ></el-pagination>
      </div>
    </div>

   <!-- 下部分：K线图和详情 -->
    <div class="panel chart-detail-panel">
      <div class="panel-header">
        <h2 v-if="displayStock">
          {{ displayStock.name }} ({{ displayStock.code }})
          <span :class="displayStock.change_rate >= 0 ? 'up-text' : 'down-text'">
            {{ (parseFloat(displayStock.price) || 0).toFixed(2) }}
            {{ (displayStock.change_rate >= 0 ? '+' : '') + (parseFloat(displayStock.change_rate) || 0).toFixed(2) + '%' }}
          </span>
        </h2>
        <h2 v-else>加载中...</h2>
        <div class="panel-actions" v-if="displayStock">
          <el-radio-group v-model="timeRange" size="small" @change="handleTimeRangeChange">
            <el-radio-button label="day">日K</el-radio-button>
            <el-radio-button label="week">周K</el-radio-button>
            <el-radio-button label="month">月K</el-radio-button>
          </el-radio-group>

          
          <!-- 添加一个按钮来切换时间线选择模式 -->
          <el-button 
            type="primary" 
            size="small"
            @click="toggleTimelineSelectionMode" 
            :type="timelineSelectionMode ? 'success' : 'info'"
          >
            {{ timelineSelectionMode ? '正在选择时间线' : '选择时间区间' }}
          </el-button>
          
          <!-- 添加导航按钮，当两条时间线都选择后激活 -->
          <el-button 
            type="primary" 
            size="small"
            @click="navigateWithSelectedTimelines" 
            :disabled="!canNavigate"
          >
            使用选中区间分析
          </el-button>

          <!-- 添加重置按钮，当有选中的时间线时显示 -->
          <el-button 
            type="danger" 
            size="small"
            @click="clearTimelineState" 
            :disabled="!firstTimeline && !secondTimeline"
          >
            清除选择区间
          </el-button>
        </div>
      </div>

      <!-- K线图区域 -->
      <div class="chart-container" ref="klineChartRef" v-loading="chartLoading"></div>
      
      <!-- 显示选中的时间线信息 -->
      <div class="selected-timelines" v-if="firstTimeline || secondTimeline">
        <div v-if="firstTimeline" class="timeline-info">
          <span class="timeline-label">起始时间:</span> 
          <span class="timeline-value">{{ formatDate(firstTimeline.time) }}</span>
        </div>
        <div v-if="secondTimeline" class="timeline-info">
          <span class="timeline-label">结束时间:</span> 
          <span class="timeline-value">{{ formatDate(secondTimeline.time) }}</span>
        </div>
        <div v-if="firstTimeline && secondTimeline" class="timeline-info">
          <span class="timeline-label">区间长度:</span> 
          <span class="timeline-value">{{ calculateDays(firstTimeline.time, secondTimeline.time) }} 天</span>
        </div>
      </div>

      <!-- 股票详情信息 -->
      <div class="stock-details" v-if="displayStock">
        <el-row :gutter="20">
          <el-col :span="4">
            <div class="detail-item">
              <div class="label">开盘价</div>
              <div class="value">{{ getSafeValue(displayStock, 'open') }}</div>
            </div>
          </el-col>
          <!-- <el-col :span="4">
            <div class="detail-item">
              <div class="label">收盘价</div>
              <div class="value">{{ getSafeValue(displayStock, 'close') }}</div>
            </div>
          </el-col> -->
          <el-col :span="4">
            <div class="detail-item">
              <div class="label">最高价</div>
              <div class="value">{{ getSafeValue(displayStock, 'high') }}</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="detail-item">
              <div class="label">最低价</div>
              <div class="value">{{ getSafeValue(displayStock, 'low') }}</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="detail-item">
              <div class="label">成交量</div>
              <div class="value">{{ formatVolume(displayStock.volume) }}</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="detail-item">
              <div class="label">7日收益率</div>
              <div class="value" :class="(displayStock.seven_day_return || 0) >= 0 ? 'up-text' : 'down-text'">
                {{ getSafePercentage(displayStock, 'seven_day_return') }}
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useRouter } from 'vue-router';
import { Search, RefreshRight } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus';

// 导入API方法
// 注意：根据你的实际API导入路径可能需要调整
import { fetchStockList, loadKlineData as apiLoadKlineData } from '@/api/stock/stockReturn';
import {addToWatchlist,getWatchlist} from '@/api/stock/stockWatchlist';
import useUserStore from '@/store/modules/user';
// 响应式状态
const searchKeyword = ref('');
const stockList = ref([]);
const selectedStock = ref(null);
const timeRange = ref('day');
const sortOrder = ref('desc');
const currentPage = ref(1);
const pageSize = ref(20);
const totalStocks = ref(0);
const chartLoading = ref(false);
const tableLoading = ref(false);
const similarStocks = ref([]);
// 选中的时间线
const router = useRouter();
const timelineSelectionMode = ref(false);
const firstTimeline = ref(null);
const secondTimeline = ref(null);
const canNavigate = computed(() => firstTimeline.value && secondTimeline.value);
const chartInstance = ref(null); // 存储图表实例
// 关注列表
const watchlist = ref([]);
// 用户store
const userStore = useUserStore();
// 获取用户ID
const currentUserId = computed(() => userStore.id);
// 计算属性：显示的股票（选中的或默认第一个）
const displayStock = computed(() => {
  return selectedStock.value || (stockList.value.length > 0 ? stockList.value[0] : null);
});
// DOM引用
const klineChartRef = ref(null);
let klineChart = null;

// 计算属性：排序后的股票列表
const sortedStockList = computed(() => {
  if (!stockList.value || !stockList.value.length) return [];
  
  // 创建副本并确保所有数值都是数字类型
  const list = stockList.value.map(stock => {
    return {
      ...stock,
      price: parseFloat(stock.price) || 0,
      change_rate: parseFloat(stock.change_rate) || 0,
      seven_day_return: parseFloat(stock.seven_day_return) || 0,
      open_price: parseFloat(stock.open_price) || 0,
      close_price: parseFloat(stock.close_price) || 0,
      high_price: parseFloat(stock.high_price) || 0,
      low_price: parseFloat(stock.low_price) || 0,
      volume: parseFloat(stock.volume) || 0
    };
  });
  
  if (sortOrder.value === 'desc') {
    return list.sort((a, b) => b.seven_day_return - a.seven_day_return);
  } else {
    return list.sort((a, b) => a.seven_day_return - b.seven_day_return);
  }
});

// 生命周期钩子
onMounted(() => {
  fetchStockListData();
  nextTick(() => {
    initChart();
  });
  
  // 窗口大小变化时调整图表大小
  window.addEventListener('resize', resizeChart);
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart);
  if (klineChart) {
    klineChart.dispose();
    klineChart = null;
  }
});

async function querySearchAsync(queryString, cb) {
  if (!queryString) {
    cb([]);
    return;
  }
  try {
    // 这里建议后端接口支持模糊搜索
    const params = {
      page: 1,
      page_size: 10,
      keyword: queryString
    };
    const response = await fetchStockList(params);
    let results = [];
    if (response.data && Array.isArray(response.data.items)) {
      results = response.data.items;
    } else if (response.data && Array.isArray(response.data)) {
      results = response.data;
    }
    // 返回格式：label和value
    cb(results.map(item => ({
      value: item.name + '（' + item.code + '）',
      ...item
    })));
  } catch (e) {
    cb([]);
  }
}

// 选择建议项时
function handleAutoSelect(stock) {
  selectedStock.value = stock;
  searchKeyword.value = stock.code;
  // 也可以自动触发详情加载
}
// 监听显示股票变化
watch(displayStock, (newVal) => {
  if (newVal) {
    loadKlineChartData();
  }
});

// 安全地获取对象属性值并格式化为数字
function getSafeValue(obj, prop, decimals = 2) {
  if (!obj || obj[prop] === undefined || obj[prop] === null) return '-';
  return (parseFloat(obj[prop]) || 0).toFixed(decimals);
}

// 安全地获取百分比值
function getSafePercentage(obj, prop) {
  if (!obj || obj[prop] === undefined || obj[prop] === null) return '-';
  const value = parseFloat(obj[prop]) || 0;
  return (value >= 0 ? '+' : '') + value.toFixed(2) + '%';
}

// 方法
//添加关注
async function handleAddToWatchlist(stock) {
  if (!stock) return;
  
  try {
    // 设置加载状态
    stock.addingToWatchlist = true;
    
    // 准备请求数据，注意参数命名
    const requestData = {
      stock_code: stock.code,  // 确保使用stock_code而非stockCode
      user_id: String(currentUserId.value), // 使用正确的参数命名并转换为字符串
      status: 1
    };
    
    // 调用API
    const response = await addToWatchlist(requestData);
    
    if (response && response.success) {
      // 添加成功后更新本地关注列表
      if (watchlist.value) {
        // 判断是否已关注
        const exists = watchlist.value.some(item => item.code === stock.code);
        if (!exists) {
          // 将新关注的股票添加到关注列表
          watchlist.value.unshift({
            ...stock,
            create_time: new Date().toISOString()
          });
        }
      }
      
      // 显示成功消息
      ElMessage.success(`已成功关注 ${stock.name}(${stock.code})`);
    } else {
      // 显示错误消息
      ElMessage.error(response?.msg || '添加关注失败');
    }
  } catch (error) {
    // 处理异常
    if (error.message.includes('超时')) {
      ElMessage.warning('请求超时，正在重试...');
      // 可以在这里添加重试逻辑
      setTimeout(() => handleAddToWatchlist(stock), 2000);
    } else {
      ElMessage.error('添加关注失败: ' + (error.message || '未知错误'));
      console.error('添加关注失败:', error);
    }
  } finally {
    // 清除加载状态
    stock.addingToWatchlist = false;
  }
}

function isWatched(stock) {
  return watchlist.value.some(item => item.code === stock.code);
}
// 获取股票列表
async function fetchStockListData() {
  tableLoading.value = true;
  try {
    // console.log('开始获取股票列表数据');
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      sort_by: 'seven_day_return',
      sort_order: sortOrder.value,
      keyword: searchKeyword.value || undefined
    };
    
    const response = await fetchStockList(params);
    // console.log('API返回数据:', response);
    
    // 处理可能的数据结构差异
    if (response.data && Array.isArray(response.data.items)) {
      stockList.value = response.data.items;
      totalStocks.value = response.data.total || 0;
    } else if (response.data && Array.isArray(response.data)) {
      // 后端直接返回数组的情况
      stockList.value = response.data;
      totalStocks.value = response.data.length;
    } else {
      console.error('返回数据结构不符合预期:', response);
      ElMessage.error('返回数据结构不符合预期');
      stockList.value = [];
      totalStocks.value = 0;
    }
  } catch (error) {
    ElMessage.error('获取股票列表失败: ' + (error.message || '未知错误'));
    console.error('获取股票列表失败:', error);
    stockList.value = [];
    totalStocks.value = 0;
  } finally {
    tableLoading.value = false;
  }
}



// 初始化图表
function initChart() {
  if (klineChartRef.value) {
    klineChart = echarts.init(klineChartRef.value);
    klineChart.setOption({
      title: {
        text: '加载中...',
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
  } else {
    console.error('klineChartRef未找到，无法初始化图表');
  }
}

// 加载K线图数据
async function loadKlineChartData() {
  // 显示的股票为计算属性，可能是选中的或列表中第一个
  if (!displayStock.value) {
    console.warn('没有可用的股票数据，无法加载K线图');
    return;
  }
  
  chartLoading.value = true;
  
  try {
    // console.log('开始加载K线数据，股票代码:', displayStock.value.code);
    const params = {
      time_range: timeRange.value
    };
    const response = await apiLoadKlineData(displayStock.value.code, params);
    
    // 检查响应数据
    if (!response || !response.data) {
      throw new Error('K线数据响应为空');
    }
    
    console.log('K线数据响应:', response);
    const klineData = response.data;
    
    // 更新图表选项
    const option = {
      title: {
        text: `${displayStock.value.name} (${displayStock.value.code}) K线图`,
        left: 'center'
      },
      xAxis: {
        data: klineData.categories || []
      },
      series: [
        {
          name: displayStock.value.name,
          type: 'candlestick',
          data: klineData.values || [],
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
          data: klineData.ma5 || [],
          smooth: true,
          lineStyle: {
            opacity: 0.8
          }
        },
        {
          name: 'MA10',
          type: 'line',
          data: klineData.ma10 || [],
          smooth: true,
          lineStyle: {
            opacity: 0.8
          }
        },
        {
          name: 'M30',
          type: 'line',
          data: klineData.ma30 || [],
          smooth: true,
          lineStyle: {
            opacity: 0.8
          }
        }
      ]
    };
    
    
    if (klineChart) {
      klineChart.setOption(option);
    } else {
      console.error('图表实例不存在，无法设置选项');
    }
  } catch (error) {
    ElMessage.error('加载K线图数据失败: ' + (error.message || '未知错误'));
    console.error('加载K线图数据失败:', error);
  } finally {
    chartLoading.value = false;
  }
}
//选时间线进行分析
// 将字符串时间转换为Date对象的函数
const parseDate = (dateStr) => {
  if (!dateStr) return null;
  // 假设时间格式是 "YYYY-MM-DD" 或其他标准格式
  // 如果您的格式不是标准的，需要根据实际格式调整
  return new Date(dateStr);
};

// 格式化日期的函数 - 对于已经是字符串格式的时间，可能直接返回即可
const formatDate = (dateStr) => {
  if (!dateStr) return '';
  // 如果需要统一格式化，可以先解析再格式化
  // 也可以直接返回原始字符串，取决于您的数据格式
  return dateStr;
};

// 计算两个日期字符串之间的天数
const calculateDays = (startDateStr, endDateStr) => {
  if (!startDateStr || !endDateStr) return 0;
  
  // 将字符串日期转换为Date对象
  const start = parseDate(startDateStr);
  const end = parseDate(endDateStr);
  
  if (!start || !end) return 0;
  
  const diffTime = Math.abs(end - start);
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
};

// 比较两个日期字符串的先后
const compareDates = (dateStr1, dateStr2) => {
  const date1 = parseDate(dateStr1);
  const date2 = parseDate(dateStr2);
  
  if (!date1 || !date2) return 0;
  return date1 - date2;
};

// 切换时间线选择模式
const toggleTimelineSelectionMode = () => {
  timelineSelectionMode.value = !timelineSelectionMode.value;
  if (!timelineSelectionMode.value) {
    // 退出选择模式时清空选中的时间线
    firstTimeline.value = null;
    secondTimeline.value = null;
    
    // 移除图表上的标记线
    updateChartTimelines();
  }
};

// 处理图表点击事件 - 调整为处理字符串时间
const handleChartClick = (params) => {
  if (!timelineSelectionMode.value) return;
  
  // 从点击事件中获取字符串时间
  // 注意: 根据ECharts的实现，可能需要获取params.name或params.value[0]
  // 这取决于您的echarts配置
  const clickTimeStr = params.name || (Array.isArray(params.value) ? params.value[0] : params.value);
  const dataIndex = params.dataIndex;
  
  if (!firstTimeline.value) {
    firstTimeline.value = {
      time: clickTimeStr,
      index: dataIndex
    };
  } else if (!secondTimeline.value) {
    // 确保第二个时间点与第一个不同
    if (dataIndex !== firstTimeline.value.index) {
      secondTimeline.value = {
        time: clickTimeStr,
        index: dataIndex
      };
      
      // 确保时间顺序正确（开始时间应该小于结束时间）
      if (compareDates(firstTimeline.value.time, secondTimeline.value.time) > 0) {
        const temp = firstTimeline.value;
        firstTimeline.value = secondTimeline.value;
        secondTimeline.value = temp;
      }
    }
  } else {
    // 如果两条时间线都已选择，重新开始选择
    firstTimeline.value = {
      time: clickTimeStr,
      index: dataIndex
    };
    secondTimeline.value = null;
  }
  
  // 更新图表上的标记线
  updateChartTimelines();
};

// 更新图表上的标记线
const updateChartTimelines = () => {
  if (!chartInstance.value) return;
  
  const option = {
    series: [{
      markLine: {
        silent: true,
        symbol: ['none', 'none'],
        lineStyle: {
          width: 2
        },
        label: {
          show: true,
          formatter: function(params) {
            return params.value;
          }
        },
        data: []
      }
    }]
  };
  
  // 添加第一条时间线
  if (firstTimeline.value) {
    option.series[0].markLine.data.push({
      name: '起始时间',
      xAxis: firstTimeline.value.index,
      lineStyle: {
        color: '#FF4500',
        type: 'solid'
      },
      label: {
        formatter: '起始: ' + firstTimeline.value.time
      }
    });
  }
  
  // 添加第二条时间线
  if (secondTimeline.value) {
    option.series[0].markLine.data.push({
      name: '结束时间',
      xAxis: secondTimeline.value.index,
      lineStyle: {
        color: '#1E90FF',
        type: 'solid'
      },
      label: {
        formatter: '结束: ' + secondTimeline.value.time
      }
    });
  }
  
  // 如果两条线都存在，添加区域着色
  if (firstTimeline.value && secondTimeline.value) {
    // 标记区域
    option.series[0].markArea = {
      silent: true,
      itemStyle: {
        color: 'rgba(255, 173, 177, 0.2)'
      },
      data: [[
        {
          name: '选中区间',
          xAxis: Math.min(firstTimeline.value.index, secondTimeline.value.index)
        },
        {
          xAxis: Math.max(firstTimeline.value.index, secondTimeline.value.index)
        }
      ]]
    };
  } else {
    // 移除区域标记
    option.series[0].markArea = {
      data: []
    };
  }
  
  // 更新图表
  chartInstance.value.setOption(option);
};

// 保存时间线状态到本地存储
const saveTimelineState = () => {
  if (firstTimeline.value && secondTimeline.value && displayStock.value) {
    const state = {
      firstTimeline: firstTimeline.value,
      secondTimeline: secondTimeline.value,
      stockCode: displayStock.value.code,
      timelineSelectionMode: timelineSelectionMode.value
    };
    localStorage.setItem('klineTimelineState', JSON.stringify(state));
  }
};

// 从本地存储恢复时间线状态
const restoreTimelineState = () => {
  const savedState = localStorage.getItem('klineTimelineState');
  if (savedState) {
    try {
      const state = JSON.parse(savedState);
      
      // 只有当当前显示的股票与保存时的股票相同时才恢复状态
      if (displayStock.value && state.stockCode === displayStock.value.code) {
        firstTimeline.value = state.firstTimeline;
        secondTimeline.value = state.secondTimeline;
        timelineSelectionMode.value = state.timelineSelectionMode;
        
        // 恢复图表上的标记线
        nextTick(() => {
          updateChartTimelines();
        });
      }
    } catch (error) {
      console.error('恢复时间线状态出错:', error);
    }
  }
};

// 清除时间线状态
const clearTimelineState = () => {
  firstTimeline.value = null;
  secondTimeline.value = null;
  timelineSelectionMode.value = false;
  localStorage.removeItem('klineTimelineState');
  updateChartTimelines();
};

// 修改导航函数，在导航前保存状态
const navigateWithSelectedTimelines = () => {
  if (!firstTimeline.value || !secondTimeline.value || !displayStock.value) return;
  
  // 保存当前状态，以便返回时恢复
  saveTimelineState();
  
  // 构建要传递的参数
  const params = {
    stockCode: displayStock.value.code,
    stockName: displayStock.value.name,
    startTime: firstTimeline.value.time,
    endTime: secondTimeline.value.time
  };
  
  // 使用路径导航
  router.push({
    path: '/stock/stockSimilarity',
    query: params
  });
};

// 在onMounted钩子中初始化图表时，添加点击事件监听
onMounted(() => {
  // 假设您的图表初始化代码如下
  // 在初始化完成后保存图表实例并添加事件监听
  fetchWatchlistData();
  nextTick(() => {
    if (klineChartRef.value) {
      // 这里是您原有的初始化图表的代码
      // ...
      
      // 获取并保存图表实例
      chartInstance.value = echarts.getInstanceByDom(klineChartRef.value) || 
                            echarts.init(klineChartRef.value);
      
      // 添加点击事件监听
      chartInstance.value.on('click', handleChartClick);
      
      // 恢复之前保存的时间线状态
      restoreTimelineState();
    }
  });
});

// 在组件卸载时移除事件监听
onUnmounted(() => {
  if (chartInstance.value) {
    chartInstance.value.off('click');
    chartInstance.value.dispose();
  }
});

async function fetchWatchlistData() {
  try {
    const response = await getWatchlist(String(currentUserId.value));
    if (response && response.data) {
      watchlist.value = response.data;
    }
  } catch (error) {
    watchlist.value = [];
  }
}
// 搜索股票
function handleSearch() {
  currentPage.value = 1;
  fetchStockListData();
}

// 清除搜索条件
function handleClear() {
  searchKeyword.value = '';
  currentPage.value = 1;
  fetchStockListData();
}

// 选择股票
function handleStockSelect(stock) {
  console.log('选择股票:', stock);
  selectedStock.value = stock;
  similarStocks.value = []; // 清空相似股票列表
}

// 选择相似股票
function handleSimilarStockSelect(stock) {
  console.log('选择相似股票:', stock);
  selectedStock.value = stock;
}

// 改变时间范围
function handleTimeRangeChange() {
  console.log('改变时间范围为:', timeRange.value);
  loadKlineChartData();
}

// 改变排序方式
function handleSortChange() {
  console.log('改变排序方式为:', sortOrder.value);
  fetchStockListData();
}

// 改变页码
function handleCurrentChange(page) {
  console.log('改变页码为:', page);
  currentPage.value = page;
  fetchStockListData();
}

// 调整图表大小
function resizeChart() {
  if (klineChart) {
    klineChart.resize();
  }
}

// 格式化工具函数
function formatNumber(value, decimals = 2) {
  if (value === undefined || value === null) return '-';
  return Number(parseFloat(value) || 0).toFixed(decimals);
}

function formatPercentage(value) {
  if (value === undefined || value === null) return '-';
  const numValue = parseFloat(value) || 0;
  return (numValue >= 0 ? '+' : '') + numValue.toFixed(2) + '%';
}

function formatVolume(volume) {
  if (volume === undefined || volume === null) return '-';
  const numVolume = parseFloat(volume) || 0;
  
  if (numVolume >= 100000000) {
    return (numVolume / 100000000).toFixed(2) + '亿手';
  } else if (numVolume >= 10000) {
    return (numVolume / 10000).toFixed(2) + '万手';
  } else {
    return numVolume + '手';
  }
}
</script>

<style scoped>
.stock-analysis-container {
  padding: 20px;
  background-color: #f0f2f5;
  min-height: 100vh;
  max-width: 1800px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h1 {
  margin: 0;
  color: #303133;
  font-size: 24px;
}

.search-box {
  display: flex;
  width: 350px;
}

.search-box :deep(.el-input) {
  margin-right: 10px;
}

.panel {
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
}

.stock-list-panel {
  margin-bottom: 20px;
}

.chart-detail-panel {
  margin-bottom: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.panel-header h2 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.chart-container {
  height: 400px;
  width: 100%;
  margin-bottom: 20px;
}

.stock-details {
  margin-top: 20px;
  margin-bottom: 20px;
}

.detail-item {
  text-align: center;
  padding: 10px;
  border-radius: 4px;
  background-color: #f9f9f9;
  height: 100%;
}

.detail-item .label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 5px;
}

.detail-item .value {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.similar-stocks {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}

.similar-stocks h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 16px;
  color: #303133;
}

.pagination {
  margin-top: 15px;
  text-align: right;
}

.up-text {
  color: #f56c6c;
}

.down-text {
  color: #67c23a;
}

/* 响应式调整 */
@media screen and (max-width: 768px) {
  .stock-analysis-container {
    padding: 10px;
  }
  
  .header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header h1 {
    margin-bottom: 15px;
  }
  
  .search-box {
    width: 100%;
  }
  
  .panel {
    padding: 15px;
  }
  
  .detail-item {
    margin-bottom: 10px;
  }
  .selected-timelines {
  margin-top: 10px;
  padding: 10px 15px;
  background-color: #f0f8ff;
  border-radius: 4px;
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.timeline-info {
  display: flex;
  align-items: center;
}

.timeline-label {
  font-weight: bold;
  margin-right: 5px;
  color: #333;
}

.timeline-value {
  color: #1890ff;
  font-weight: 500;
}
}
</style>