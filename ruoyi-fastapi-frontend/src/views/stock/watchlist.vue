<template>
  <div class="stock-watchlist-container">
    <!-- 头部标题 -->
    <div class="header">
      <h1>我的关注股票</h1>
      <div class="header-actions">
        <el-button type="primary" :icon="RefreshRight" @click="refreshWatchlist">
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- 搜索框区域 -->
    <div class="search-section">
      <div class="search-wrapper">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索股票代码或名称"
          size="large"
          :prefix-icon="Search"
          clearable
          @input="handleSearchInput"
          @clear="handleClearSearch"
          class="search-input"
        >
          <template #append>
            <el-button 
              type="primary" 
              :icon="Search"
              @click="handleSearch"
            >
              搜索
            </el-button>
          </template>
        </el-input>
      </div>
    </div>

    <!-- 上部分：关注股票列表 -->
    <div class="panel watchlist-panel">
      <div class="panel-header">
        <h2>关注列表</h2>
        <div class="panel-actions">
          <el-select v-model="sortField" placeholder="排序方式" size="small" @change="handleSortChange">
            <el-option label="按涨跌幅" value="change_rate"></el-option>
            <!-- <el-option label="按7日收益率" value="seven_day_return"></el-option> -->
            <el-option label="按关注时间" value="add_time"></el-option>
          </el-select>
          <el-select v-model="sortOrder" placeholder="排序顺序" size="small" @change="handleSortChange">
            <el-option label="高→低" value="desc"></el-option>
            <el-option label="低→高" value="asc"></el-option>
          </el-select>
        </div>
      </div>
      <el-table
        :data="sortedWatchlist"
        height="400"
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
        <!-- <el-table-column prop="seven_day_return" label="7日收益率" width="140">
          <template #default="{ row }">
            <span 
              v-if="row && row.seven_day_return !== undefined" 
              :class="row.seven_day_return >= 0 ? 'up-text' : 'down-text'"
            >
              {{ formatPercentage(row.seven_day_return) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column> -->
        <el-table-column prop="add_time" label="关注时间" width="160">
          <template #default="{ row }">
            <span>{{ formatDateTime(row.add_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button 
              size="small" 
              type="danger" 
              @click.stop="handleRemoveFromWatchlist(row)"
              :loading="row.removingFromWatchlist"
            >
              取消关注
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="watchlist-stats">
        <span>共关注 <strong>{{ totalWatchedStocks }}</strong> 只股票</span>
        <span>今日涨幅 <strong :class="todayUpCount > todayDownCount ? 'up-text' : 'down-text'">
          {{ todayUpCount }}</strong> / {{ todayDownCount }}</span>
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
        <h2 v-else>请选择股票查看详情</h2>
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
              <!-- <div class="label">7日收益率</div> -->
              <div class="value" :class="(displayStock.seven_day_return || 0) >= 0 ? 'up-text' : 'down-text'">
                {{ getSafePercentage(displayStock, 'seven_day_return') }}
              </div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="detail-item">
              <div class="label">关注天数</div>
              <div class="value">{{ calculateWatchDays(displayStock.add_time) }}天</div>
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
import { RefreshRight, Search } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import { ElMessage, ElMessageBox } from 'element-plus';
import useUserStore from '@/store/modules/user';
// 导入API方法
import { loadKlineData as apiLoadKlineData } from '@/api/stock/stockReturn';
import { getWatchlist, removeFromWatchlist, searchStocks } from '@/api/stock/stockWatchlist';

// 用户store
const userStore = useUserStore();
// 获取用户ID
const currentUserId = computed(() => userStore.id);

// 响应式状态
const watchlist = ref([]);
const selectedStock = ref(null);
const timeRange = ref('day');
const sortField = ref('change_rate');
const sortOrder = ref('desc');
const chartLoading = ref(false);
const tableLoading = ref(false);
const similarStocks = ref([]);
const searchKeyword = ref('');
const searchResults = ref([]);

// 选中的时间线
const router = useRouter();
const timelineSelectionMode = ref(false);
const firstTimeline = ref(null);
const secondTimeline = ref(null);
const canNavigate = computed(() => firstTimeline.value && secondTimeline.value);
const chartInstance = ref(null); // 存储图表实例


// 计算属性：显示的股票
const displayStock = computed(() => {
  return selectedStock.value || (watchlist.value.length > 0 ? watchlist.value[0] : null);
});

// 计算属性：过滤并排序后的关注列表
const sortedWatchlist = computed(() => {
  if (!watchlist.value || !watchlist.value.length) return [];
  
  // 先进行搜索过滤
  let list = watchlist.value;
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase();
    list = list.filter(stock => {
      return (stock.code && stock.code.toLowerCase().includes(keyword)) ||
             (stock.name && stock.name.toLowerCase().includes(keyword));
    });
  }
  
  // 复制数组以避免直接修改原数组
  list = [...list];
  
  // 进行排序
  list.sort((a, b) => {
    let aValue, bValue;
    
    switch (sortField.value) {
      case 'change_rate':
        aValue = parseFloat(a.change_rate) || 0;
        bValue = parseFloat(b.change_rate) || 0;
        break;
      case 'seven_day_return':
        aValue = parseFloat(a.seven_day_return) || 0;
        bValue = parseFloat(b.seven_day_return) || 0;
        break;
      case 'add_time':
        aValue = new Date().getTime();
        bValue = new Date().getTime();
        break;
      default:
        aValue = 0;
        bValue = 0;
    }
    
    if (sortOrder.value === 'desc') {
      return bValue - aValue;
    } else {
      return aValue - bValue;
    }
  });
  
  return list;
});

// 计算属性：统计信息
const totalWatchedStocks = computed(() => watchlist.value.length);
const todayUpCount = computed(() => watchlist.value.filter(stock => stock.change_rate >= 0).length);
const todayDownCount = computed(() => watchlist.value.filter(stock => stock.change_rate < 0).length);

// DOM引用
const klineChartRef = ref(null);
let klineChart = null;

// 生命周期钩子
onMounted(() => {
  // 初始化获取关注列表
  fetchWatchlistData();
  
  nextTick(() => {
    initChart();
  });
  
  window.addEventListener('resize', resizeChart);
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart);
  if (klineChart) {
    klineChart.dispose();
    klineChart = null;
  }
});

// 监听用户ID变化
watch(currentUserId, (newVal) => {
  if (newVal) {
    fetchWatchlistData();
  }
});

// 监听显示股票变化
watch(displayStock, (newVal) => {
  if (newVal) {
    loadKlineChartData();
    fetchSimilarStocks();
  }
});

// 获取关注列表数据
async function fetchWatchlistData() {
  tableLoading.value = true;
  try {
    console.log('Fetching watchlist data for user ID:', currentUserId.value);
    const response = await getWatchlist(String(currentUserId.value));
    if (response && response.data) {
      watchlist.value = response.data;
      if (watchlist.value.length > 0 && !selectedStock.value) {
        selectedStock.value = watchlist.value[0];
      }
    }
  } catch (error) {
    ElMessage.error('获取关注列表失败: ' + (error.message || '未知错误'));
    console.error('获取关注列表失败:', error);
  } finally {
    tableLoading.value = false;
  }
}

// 获取相似股票
async function fetchSimilarStocks() {
  if (!displayStock.value) return;
  
  try {
    // 假设有一个获取相似股票的API
    // 这里可以根据实际情况实现
    similarStocks.value = [];
  } catch (error) {
    console.error('获取相似股票失败:', error);
  }
}

// 处理从关注列表移除
async function handleRemoveFromWatchlist(stock) {
  if (!stock) return;
  
  try {
    // 设置加载状态
    stock.removingFromWatchlist = true;
    
    // 调用API
    await removeFromWatchlist(stock.code,currentUserId.value);
    
    // 从本地列表中移除
    const index = watchlist.value.findIndex(item => item.code === stock.code);
    if (index !== -1) {
      watchlist.value.splice(index, 1);
    }
    
    // 如果删除的是当前选中的股票，重置选中
    if (selectedStock.value && selectedStock.value.code === stock.code) {
      selectedStock.value = watchlist.value.length > 0 ? watchlist.value[0] : null;
    }
    
    ElMessage.success(`已将 ${stock.name}(${stock.code}) 从关注列表移除`);
  } catch (error) {
    ElMessage.error('取消关注失败: ' + (error.message || '未知错误'));
    console.error('取消关注失败:', error);
  } finally {
    stock.removingFromWatchlist = false;
  }
}
// 初始化图表
function initChart() {
  if (klineChartRef.value) {
    klineChart = echarts.init(klineChartRef.value);
    klineChart.setOption({
      title: {
        text: '请选择股票',
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
  }else {
    console.error('klineChartRef未找到，无法初始化图表');
  }
}

// 加载K线图数据
async function loadKlineChartData() {
  if (!displayStock.value) return;
  
  chartLoading.value = true;
  
  try {
    const params = {
      time_range: timeRange.value
    };
    const response = await apiLoadKlineData(displayStock.value.code, params);
    
    if (!response || !response.data) {
      throw new Error('K线数据响应为空');
    }
    
    const klineData = response.data;
    
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
          name: 'MA20',
          type: 'line',
          data: klineData.ma20 || [],
          smooth: true,
          lineStyle: {
            opacity: 0.8
          }
        }
      ]
    };
    
    if (klineChart) {
      klineChart.setOption(option);
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





// 选择股票
function handleStockSelect(stock) {
  console.log('选择股票:', stock);
  selectedStock.value = stock;
  similarStocks.value = []; // 清空相似股票列表
}



// 改变时间范围
function handleTimeRangeChange() {
  console.log('改变时间范围为:', timeRange.value);
  loadKlineChartData();
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


// 工具函数
function getSafeValue(obj, prop, decimals = 2) {
  if (!obj || obj[prop] === undefined || obj[prop] === null) return '-';
  return (parseFloat(obj[prop]) || 0).toFixed(decimals);
}

function getSafePercentage(obj, prop) {
  if (!obj || obj[prop] === undefined || obj[prop] === null) return '-';
  const value = parseFloat(obj[prop]) || 0;
  return (value >= 0 ? '+' : '') + value.toFixed(2) + '%';
}


function formatDateTime(dateTime) {
  if (!dateTime) return '-';
  const date = new Date(dateTime);
  return date.toLocaleString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function calculateWatchDays(createTime) {
  if (!createTime) return 0;
  const createDate = new Date(createTime);
  const today = new Date();
  const diffTime = Math.abs(today - createDate);
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}




function handleSortChange() {
  // 排序已由计算属性自动处理
}



// 搜索相关函数
function handleSearchInput() {
  // 实时搜索，计算属性会自动更新过滤结果
}

async function handleSearch() {
  if (!searchKeyword.value) return;
  
  try {
    const response = await searchStocks(searchKeyword.value);
    if (response && response.data) {
      searchResults.value = response.data;
      ElMessage.success(`找到 ${searchResults.value.length} 个匹配结果`);
    }
  } catch (error) {
    ElMessage.error('搜索失败: ' + (error.message || '未知错误'));
    console.error('搜索失败:', error);
  }
}

function handleClearSearch() {
  searchKeyword.value = '';
  searchResults.value = [];
  ElMessage.info('已清除搜索条件');
}

// 刷新关注列表
function refreshWatchlist() {
  fetchWatchlistData();
  ElMessage.success('数据已刷新');
}
</script>

<style scoped>
.stock-watchlist-container {
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

.header-actions {
  display: flex;
  gap: 10px;
}

/* 搜索框样式 */
.search-section {
  margin-bottom: 20px;
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.search-wrapper {
  max-width: 600px;
  margin: 0 auto;
}

.search-input {
  width: 100%;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  transition: all 0.3s;
}

.search-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

.search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

.panel {
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
}

.watchlist-panel {
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

.panel-actions {
  display: flex;
  gap: 10px;
}

.watchlist-stats {
  margin-top: 15px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.watchlist-stats strong {
  font-weight: 600;
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

.up-text {
  color: #f56c6c;
}

.down-text {
  color: #67c23a;
}

/* 响应式调整 */
@media screen and (max-width: 768px) {
  .stock-watchlist-container {
    padding: 10px;
  }
  
  .header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header h1 {
    margin-bottom: 15px;
  }
  
  .panel {
    padding: 15px;
  }
  
  .detail-item {
    margin-bottom: 10px;
  }
}
</style>