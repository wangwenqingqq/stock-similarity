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
        @input="handleSearch"
      />
      <button v-if="searchKeyword" @click="clearSearch" class="clear-button">
        清空
      </button>
    </div>
    
    <div class="query-list">
      <div
        v-for="query in filteredQueryHistory"
        :key="query.id"
        class="query-item"
        :class="{ 'expanded': expandedItems.includes(query.id) }"
        @click="toggleExpand(query.id)"
      >
        <!-- 折叠状态显示的摘要信息 -->
        <div class="query-summary">
          <div class="summary-left">
            <span class="stock-code" v-html="highlightText(query.stockCode)"></span>
            <span class="stock-name" v-html="highlightText(query.stockName)"></span>
            <span class="query-time">{{ formatDate(query.queryTime) }}</span>
          </div>
          <div class="summary-right">
            <span class="result-count">找到 {{ query.results.length }} 个相似股票</span>
            <i :class="expandedItems.includes(query.id) ? 'el-icon-arrow-up' : 'el-icon-arrow-down'"></i>
          </div>
        </div>
        
        <!-- 展开状态显示的详细信息 -->
        <div v-if="expandedItems.includes(query.id)" class="query-details">
          <div class="detail-section">
            <h4>查询条件</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <label>股票代码：</label>
                <span>{{ query.stockCode }}</span>
              </div>
              <div class="detail-item">
                <label>股票名称：</label>
                <span>{{ query.stockName }}</span>
              </div>
              <div class="detail-item">
                <label>时间段：</label>
                <span>{{ query.startDate }} 至 {{ query.endDate }}</span>
              </div>
              <div class="detail-item">
                <label>选择指标：</label>
                <span>{{ query.indicators.join(', ') }}</span>
              </div>
              <div class="detail-item">
                <label>计算方法：</label>
                <span>{{ query.method }}</span>
              </div>
              <div class="detail-item">
                <label>对比范围：</label>
                <span>{{ query.compareScope }}</span>
              </div>
              <div class="detail-item">
                <label>相似个数：</label>
                <span>{{ query.similarCount }}</span>
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
                  <th>收益率对比</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(result, index) in query.results" :key="result.stockCode">
                  <td>{{ index + 1 }}</td>
                  <td>{{ result.stockCode }}</td>
                  <td>{{ result.stockName }}</td>
                  <td>{{ (result.similarity * 100).toFixed(2) }}%</td>
                  <td>
                    <span :class="result.returnRate > 0 ? 'positive' : 'negative'">
                      {{ result.returnRate > 0 ? '+' : '' }}{{ result.returnRate.toFixed(2) }}%
                    </span>
                  </td>
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

// 获取查询历史
const fetchHistory = async () => {
  try {
    const response = await getQueryHistoryList({
      page: 1,
      pageSize: 10,
      orderBy: 'queryTime',
      order: 'desc'
    })
    queryHistory.value = response.data
  } catch (error) {
    console.error('获取历史记录失败', error)
  }
}

// 搜索历史记录
const handleSearch = async () => {
  try {
    const response = await searchQueryHistory(searchKeyword.value)
    queryHistory.value = response.data
  } catch (error) {
    console.error('搜索失败', error)
  }
}

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

// 模拟的查询历史数据
const queryHistory = ref([
  {
    id: 1,
    stockCode: '000001.SZ',
    stockName: '平安银行',
    queryTime: new Date('2024-05-15 10:30:00'),
    startDate: '2023-01-01',
    endDate: '2024-05-01',
    indicators: ['收益率', '波动率', '成交量'],
    method: '皮尔逊相关系数',
    compareScope: '全部A股',
    similarCount: 10,
    results: [
      { stockCode: '000002.SZ', stockName: '万科A', similarity: 0.92, returnRate: 5.23 },
      { stockCode: '000858.SZ', stockName: '五粮液', similarity: 0.88, returnRate: -2.15 },
      { stockCode: '000333.SZ', stockName: '美的集团', similarity: 0.85, returnRate: 8.76 }
    ]
  },
  {
    id: 2,
    stockCode: '600036.SH',
    stockName: '招商银行',
    queryTime: new Date('2024-05-14 16:20:00'),
    startDate: '2023-06-01',
    endDate: '2024-05-01',
    indicators: ['市盈率', '市净率'],
    method: '余弦相似度',
    compareScope: '银行板块',
    similarCount: 5,
    results: [
      { stockCode: '601166.SH', stockName: '兴业银行', similarity: 0.95, returnRate: 3.45 },
      { stockCode: '601398.SH', stockName: '工商银行', similarity: 0.91, returnRate: 1.23 }
    ]
  },
  {
    id: 3,
    stockCode: '002415.SZ',
    stockName: '海康威视',
    queryTime: new Date('2024-05-13 14:15:00'),
    startDate: '2023-03-01',
    endDate: '2024-05-01',
    indicators: ['成交量', '换手率'],
    method: '欧几里得距离',
    compareScope: '科技板块',
    similarCount: 8,
    results: [
      { stockCode: '002230.SZ', stockName: '科大讯飞', similarity: 0.89, returnRate: 12.34 },
      { stockCode: '300124.SZ', stockName: '汇川技术', similarity: 0.86, returnRate: -5.67 }
    ]
  }
])

// 过滤后的查询历史（根据搜索关键词）
const filteredQueryHistory = computed(() => {
  if (!searchKeyword.value) {
    return queryHistory.value
  }
  
  const keyword = searchKeyword.value.toLowerCase()
  return queryHistory.value.filter(query => {
    return query.stockCode.toLowerCase().includes(keyword) ||
           query.stockName.toLowerCase().includes(keyword)
  })
})

// 清空搜索
const clearSearch = () => {
  searchKeyword.value = ''
}

// 高亮搜索关键词
const highlightText = (text) => {
  if (!searchKeyword.value) {
    return text
  }
  
  const keyword = searchKeyword.value
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

// 组件挂载时可以从API获取真实数据
onMounted(() => {
  // 这里可以添加API调用来获取真实的查询历史数据
  // fetchQueryHistory()
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
</style>