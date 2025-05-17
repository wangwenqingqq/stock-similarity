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
        </div>
      </div>

      <!-- K线图区域 -->
      <div class="chart-container" ref="klineChartRef" v-loading="chartLoading"></div>

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
          <el-table-column prop="code" label="代码" width="120"></el-table-column>
          <el-table-column prop="name" label="名称" width="180"></el-table-column>
          <el-table-column prop="similarity" label="相似度" width="120">
            <template #default="{ row }">
              <span>{{ ((parseFloat(row.similarity) || 0) * 100).toFixed(2) + '%' }}</span>
            </template>
          </el-table-column>
          <!-- <el-table-column prop="seven_day_return" label="7日收益率" width="140">
            <template #default="{ row }">
              <span :class="row.seven_day_return >= 0 ? 'up-text' : 'down-text'">
                {{ (row.seven_day_return >= 0 ? '+' : '') + (parseFloat(row.seven_day_return) || 0).toFixed(2) + '%' }}
              </span>
            </template>
          </el-table-column> -->
          <el-table-column prop="price" label="当前价" width="120">
            <template #default="{ row }">
              <span>{{ (parseFloat(row.price) || 0).toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="change_rate" label="涨跌幅" min-width="120">
            <template #default="{ row }">
              <span :class="row.change_rate >= 0 ? 'up-text' : 'down-text'">
                {{ (row.change_rate >= 0 ? '+' : '') + (parseFloat(row.change_rate) || 0).toFixed(2) + '%' }}
              </span>
            </template>
          </el-table-column>
        </el-table>
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

// 路由
const router = useRouter();

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

// 事件处理函数
function handleStockSelect(stock) {
  selectedStock.value = stock;
  similarStocks.value = [];
}

function handleSimilarStockSelect(stock) {
  ElMessage.info(`选择了相似股票: ${stock.name}(${stock.code})`);
}

function handleTimeRangeChange() {
  loadKlineChartData();
}

function handleSortChange() {
  // 排序已由计算属性自动处理
}

function resizeChart() {
  if (klineChart) {
    klineChart.resize();
  }
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