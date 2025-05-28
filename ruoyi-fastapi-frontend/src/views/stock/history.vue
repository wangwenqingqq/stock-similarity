<template>
  <div class="query-history-container">
    <h2 class="page-title">相似性计算查询历史</h2>
    
    <!-- 搜索栏 -->
    <div class="search-bar">
      <input
        v-model="searchKeyword"
        type="text"
        placeholder="搜索股票代码或名称"
        class="search-input"
        @input="debouncedSearch"
      />
      <button v-if="searchKeyword" @click="clearSearch" class="clear-button">
        清空
      </button>
    </div>
    
    <div class="query-list">
      <div
        v-for="query in filteredQueryHistory"
        :key="query.query_time"
        class="query-item"
        :class="{ 'expanded': expandedItems.includes(query.query_time) }"
        @click="toggleExpand(query.query_time)"
      >
        <!-- 折叠状态显示的摘要信息 -->
        <div class="query-summary">
          <div class="summary-left">
            <span class="stock-code" v-html="highlightText(query.stock_code)"></span>
            <span class="stock-name" v-html="highlightText(query.stock_name)"></span>
            <span class="query-time">{{ formatDate(query.query_time) }}</span>
          </div>
          <div class="summary-right">
            <span class="result-count">找到 {{ query.similar_count }} 个相似股票</span>
            <i :class="expandedItems.includes(query.query_time) ? 'el-icon-arrow-up' : 'el-icon-arrow-down'"></i>
          </div>
        </div>
        
        <!-- 展开状态显示的详细信息 -->
        <div v-if="expandedItems.includes(query.query_time)" class="query-details">
          <div class="detail-section">
            <h4>查询条件</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <label>股票代码：</label>
                <span>{{ query.stock_code }}</span>
              </div>
              <div class="detail-item">
                <label>股票名称：</label>
                <span>{{ query.stock_name }}</span>
              </div>
              <div class="detail-item">
                <label>时间段：</label>
                <span>{{ query.start_date }} 至 {{ query.end_date }}</span>
              </div>
              <div class="detail-item">
                <label>时间长度：</label>
                <span>{{ getDuration(query.start_date, query.end_date) }}</span>
              </div>
              <div class="detail-item" v-if="shouldShowIndicators(query.method)">
                <label>选择指标：</label>
                <span>{{ formatIndicators(query.indicators) }}</span>
              </div>
              <div class="detail-item">
                <label>计算方法：</label>
                <span>{{ formatMethod(query.method) }}</span>
              </div>
              <div class="detail-item">
                <label>对比范围：</label>
                <span>{{ formatCompareScope(query.compare_scope) }}</span>
              </div>
              <div class="detail-item">
                <label>相似个数：</label>
                <span>{{ query.similar_count }}</span>
              </div>
            </div>
          </div>
          
          <div class="detail-section">
            <h4>相似股票结果</h4>
            <table class="result-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>股票代码</th>
                  <th>股票名称</th>
                  <th>相似度</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(result, index) in query.similar_results" :key="result.stock_code">
                  <td>{{ index + 1 }}</td>
                  <td>{{ result.stock_code }}</td>
                  <td>{{ result.stock_name }}</td>
                  <td>{{ (result.similarity * 100).toFixed(2) }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="filteredQueryHistory.length === 0" class="empty-state">
      {{ searchKeyword ? '没有找到匹配的查询记录' : '暂无查询历史记录' }}
    </div>
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
// 在Vue组件中使用
import { 
  getQueryHistoryList, 
  searchQueryHistory, 
  deleteQueryHistory 
} from '@/api/stock/stockHistory'
import useUserStore from '@/store/modules/user';
import { debounce } from 'lodash'
// 用户store
const userStore = useUserStore();
// 获取用户ID
const currentUserId = computed(() => userStore.id);
// 获取查询历史
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const fetchHistory = async () => {
  try {
    const params = {
      user_id: currentUserId.value,
      page: currentPage.value,
      page_size: pageSize.value,
      sort_by: 'query_time',
      sort_order: 'desc'
    }
    const response = await getQueryHistoryList(params)
    queryHistory.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    console.error('获取历史记录失败', error)
  }
}

// 搜索历史记录
const handleSearch = async () => {
  try {
    const response = await searchQueryHistory(searchKeyword.value)
    queryHistory.value = response.data.items
  } catch (error) {
    queryHistory.value = []
  }
}
// 防抖函数
const debouncedSearch = debounce(() => {
  handleSearch()
}, 300)

// 删除记录
const handleDelete = async (historyId) => {
  try {
    await deleteQueryHistory(historyId)
    // 刷新列表
    await fetchHistory()
  } catch (error) {
    console.error('删除失败', error)
  }
}
// 展开的项目ID列表
const expandedItems = ref([])

// 搜索关键词
const searchKeyword = ref('')

const queryHistory = ref([])
// 过滤后的查询历史（根据搜索关键词）
const filteredQueryHistory = computed(() => {
  if (!searchKeyword.value) {
    return queryHistory.value
  }
  return queryHistory.value
})


// 清空搜索
const clearSearch = () => {
  searchKeyword.value = ''
  fetchHistory()
}

// 高亮搜索关键词
const highlightText = (text) => {
  if (!searchKeyword.value) return text
  const keyword = searchKeyword.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${keyword})`, 'gi')
  return text.replace(regex, '<span class="highlight">$1</span>')
}

// 切换展开状态
const toggleExpand = (id) => {
  const index = expandedItems.value.indexOf(id)
  if (index > -1) {
    expandedItems.value.splice(index, 1)
  } else {
    expandedItems.value.push(id)
  }
}

// 格式化日期
const formatDate = (date) => {
  const d = new Date(date)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
function getDuration(start, end) {
  if (!start || !end) return ''
  // 只取日期部分，防止有时分秒影响
  const startDate = new Date(start.split(' ')[0])
  const endDate = new Date(end.split(' ')[0])
  // 计算毫秒差
  const diffTime = endDate - startDate
  // 计算天数差（包含起止日+1）
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)) + 1
  return `${diffDays}天`
}

// 新增：指标转换函数
const indicatorMap = {
  close: '收盘价涨跌幅',
  high: '最高价涨跌幅',
  low: '最低价涨跌幅',
  turnover: '换手率',
}
function formatIndicators(indicators) {
  if (!Array.isArray(indicators)) return ''
  return indicators.map(i => indicatorMap[i] || i).join(', ')
}

// 新增：方法转换函数
const methodMap = {
  maxCommonSubgraph: '最大公共子图',
  graphEditing: '图编辑距离',
  dtw: '动态规整算法',
  pearson: '皮尔森相关系数',
  euclidean: '欧式距离',
  coIntegration: '协整性算法',
  shape: '形状相似性',
  position: '位置相似性',
}
function formatMethod(method) {
  return methodMap[method] || method
}
function shouldShowIndicators(method) {
  return method !== 'shape' && method !== 'position'
}

// 新增：对比范围转换函数
function formatCompareScope(scope) {
  if (scope === '1') return '中证三级行业'
  if (scope === '0') return '证监会一级行业'
  return scope
}

// 新增分页改变处理函数
const handlePageChange = (page) => {
  currentPage.value = page
  fetchHistory()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchHistory()
}

// 组件挂载时可以从API获取真实数据
onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.query-history-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
}

/* 搜索栏样式 */
.search-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  position: relative;
}

.search-input {
  flex: 1;
  padding: 10px 15px;
  border: 1px solid #d0d0d0;
  border-radius: 4px;
  font-size: 16px;
  outline: none;
  transition: border-color 0.3s;
}

.search-input:focus {
  border-color: #1890ff;
}

.clear-button {
  position: absolute;
  right: 10px;
  padding: 5px 10px;
  background: #f0f0f0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: background-color 0.3s;
}

.clear-button:hover {
  background: #e0e0e0;
}

/* 高亮样式 */
:deep(.highlight) {
  background-color: #ffd666;
  font-weight: bold;
  padding: 0 2px;
  border-radius: 2px;
}

.query-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.query-item {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
}

.query-item:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.query-item.expanded {
  cursor: default;
}

.query-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
}

.summary-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stock-code {
  font-weight: bold;
  color: #1890ff;
  font-size: 16px;
}

.stock-name {
  color: #333;
  font-weight: 500;
}

.query-time {
  color: #666;
  font-size: 14px;
}

.summary-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.result-count {
  color: #52c41a;
  font-weight: 500;
}

.query-details {
  border-top: 1px solid #f0f0f0;
  padding: 20px;
  background: #fafafa;
}

.detail-section {
  margin-bottom: 25px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  color: #333;
  margin-bottom: 15px;
  font-size: 16px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.detail-item {
  display: flex;
  gap: 10px;
}

.detail-item label {
  color: #666;
  font-weight: 500;
  white-space: nowrap;
}

.detail-item span {
  color: #333;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
}

.result-table th {
  background: #f5f5f5;
  padding: 12px;
  text-align: left;
  font-weight: 500;
  color: #333;
  border-bottom: 2px solid #e0e0e0;
}

.result-table td {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.result-table tr:last-child td {
  border-bottom: none;
}

.positive {
  color: #52c41a;
  font-weight: 500;
}

.negative {
  color: #f5222d;
  font-weight: 500;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  font-size: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .search-bar {
    margin-bottom: 15px;
  }
  
  .search-input {
    font-size: 14px;
  }
  
  .query-summary {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .summary-left {
    flex-wrap: wrap;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .result-table {
    font-size: 14px;
  }
  
  .result-table th,
  .result-table td {
    padding: 8px;
  }
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>