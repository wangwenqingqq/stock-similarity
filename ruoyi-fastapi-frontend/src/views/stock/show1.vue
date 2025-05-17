<template>
  <div class="app-container">
    <h1 class="main-title">关注股票列表</h1>
    
    <!-- 通知提示 -->
    <el-alert
      v-if="notification.show"
      :title="notification.message"
      :type="notification.type"
      show-icon
      :closable="false"
    />
    
    <!-- 搜索区域 -->
    <el-form :inline="true" class="search-form">
      <el-form-item>
        <el-input
          v-model="searchQuery"
          @input="handleSearchInput"
          :placeholder="isSearching ? '搜索新股票添加到关注列表...' : '在关注列表中搜索...'"
          clearable
          style="width: 300px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="toggleSearchMode">
          {{ isSearching ? "返回" : "添加" }}
        </el-button>
      </el-form-item>
      <el-form-item v-if="!isSearching && watchlist.length > 0">
        <el-button type="danger" @click="clearWatchlist">清空</el-button>
      </el-form-item>
    </el-form>
    
    <!-- 搜索结果下拉框 -->
    <el-card v-if="isSearching && searchResults.length > 0" class="search-results">
      <el-scrollbar height="300px">
        <div
          v-for="stock in searchResults"
          :key="stock.code"
          class="search-result-item"
          @click="addToWatchlist(stock)"
        >
          <div>
            <span class="stock-name">{{ stock.name }}</span>
            <span class="stock-code">{{ stock.code }}</span>
          </div>
          <el-button type="primary" icon="Plus" circle size="small" />
        </div>
      </el-scrollbar>
    </el-card>
    
    <!-- 关注列表表格 -->
    <el-table
      v-if="!isSearching"
      v-loading="loading"
      :data="filteredWatchlist"
      border
      style="width: 100%"
    >
      <el-table-column prop="code" label="代码" align="center" />
      <el-table-column prop="name" label="名称" align="center" />
      <el-table-column prop="price" label="价格" align="center">
        <template #default="scope">
          {{ scope.row.price.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="涨跌" align="center">
        <template #default="scope">
          <span :class="scope.row.change >= 0 ? 'text-success' : 'text-danger'">
            {{ scope.row.change >= 0 ? '+' : '' }}{{ scope.row.change.toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" align="center" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-button
            link
            type="primary"
            icon="Delete"
            @click="removeFromWatchlist(scope.row.code)"
          >删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <div class="empty-text">
          {{ watchlist.length === 0 ? "关注列表为空，请添加股票" : "没有找到匹配的股票" }}
        </div>
      </template>
    </el-table>
    
    <!-- 添加股票模式下的提示 -->
    <el-empty
      v-if="isSearching && ((searchResults.length === 0 && searchQuery.trim() !== '') || searchQuery.trim() === '')"
      :description="searchQuery.trim() !== '' ? '没有找到匹配的股票，请尝试其他关键字' : '请输入股票代码或名称进行搜索'"
    />
  </div>
</template>

<script setup name="StockWatchlist">
import { ElMessageBox } from 'element-plus'
import { ref, computed, onMounted, watch } from 'vue';
import { Search, Plus, Delete } from '@element-plus/icons-vue';
import { getWatchlist, searchStocks, addToWatchlist as addStockAPI, removeFromWatchlist as removeStockAPI, clearWatchlist as clearStockAPI } from '@/api/stock/stockInfo';

// 响应式状态
const watchlist = ref([]);
const searchQuery = ref('');
const searchResults = ref([]);
const isSearching = ref(false);
const loading = ref(false);
const notification = ref({ show: false, message: '', type: 'success' });

// 计算属性：过滤后的关注列表
const filteredWatchlist = computed(() => {
  if (!searchQuery.value.trim() || isSearching.value) return watchlist.value;
  
  return watchlist.value.filter(stock => 
    stock.code.toLowerCase().includes(searchQuery.value.toLowerCase()) || 
    stock.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  );
});

// 方法：显示通知
const showNotification = (message, type = 'success') => {
  notification.value = { show: true, message, type };
  setTimeout(() => {
    notification.value = { show: false, message: '', type: '' };
  }, 3000);
};

// 方法：处理搜索输入
const handleSearchInput = async () => {
  if (!isSearching.value) return;
  
  if (!searchQuery.value.trim()) {
    searchResults.value = [];
    return;
  }
  
  try {
    loading.value = true;
    // 从后端API获取搜索结果
    const result = await searchStocks(searchQuery.value);
    searchResults.value = result.data || [];
    loading.value = false;
  } catch (error) {
    console.error('搜索股票失败', error);
    showNotification('搜索股票失败，请稍后再试', 'error');
    searchResults.value = [];
    loading.value = false;
  }
};

// 方法：切换搜索模式
const toggleSearchMode = () => {
  isSearching.value = !isSearching.value;
  searchQuery.value = '';
  searchResults.value = [];
};

// 方法：添加股票到关注列表
const addToWatchlist = (stock) => {
  if (watchlist.value.some(item => item.code === stock.code)) {
    showNotification(`${stock.name}(${stock.code}) 已在关注列表中`, 'warning');
    return;
  }
  
  watchlist.value.push(stock);
  showNotification(`已添加 ${stock.name}(${stock.code}) 到关注列表`);
  searchQuery.value = '';
  searchResults.value = [];
};

// 方法：从关注列表中删除股票
const removeFromWatchlist = (stockCode) => {
  const stockToRemove = watchlist.value.find(stock => stock.code === stockCode);
  if (stockToRemove) {
    watchlist.value = watchlist.value.filter(stock => stock.code !== stockCode);
    showNotification(`已从关注列表中移除 ${stockToRemove.name}(${stockToRemove.code})`);
  }
};

// 方法：清空关注列表
const clearWatchlist = () => {
  if (watchlist.value.length === 0) return;
  
  ElMessageBox.confirm('确定要清空关注列表吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    watchlist.value = [];
    showNotification('已清空关注列表');
  }).catch(() => {});
};

// 生命周期钩子：组件挂载时从本地存储加载关注列表
onMounted(() => {
  const savedWatchlist = localStorage.getItem('stockWatchlist');
  if (savedWatchlist) {
    try {
      watchlist.value = JSON.parse(savedWatchlist);
    } catch (e) {
      console.error('无法解析保存的关注列表', e);
    }
  }
});

// 监听器：当关注列表变化时，保存到本地存储
watch(watchlist, (newValue) => {
  localStorage.setItem('stockWatchlist', JSON.stringify(newValue));
}, { deep: true });
</script>

<style scoped>
.app-container {
  padding: 20px;
}

.main-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 20px;
}

.search-form {
  margin-bottom: 20px;
}

.search-results {
  margin-bottom: 20px;
}

.search-result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
}

.search-result-item:hover {
  background-color: #f5f7fa;
}

.stock-name {
  font-weight: 500;
  margin-right: 10px;
}

.stock-code {
  color: #909399;
}

.text-success {
  color: #67c23a;
}

.text-danger {
  color: #f56c6c;
}

.empty-text {
  text-align: center;
  color: #909399;
  padding: 30px 0;
}
</style>