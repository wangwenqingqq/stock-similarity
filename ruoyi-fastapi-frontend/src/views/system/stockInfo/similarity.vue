<template>
    <div class="app-container">
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span class="font-bold">股票相似性分析工具</span>
          </div>
        </template>
  
        <!-- 查询区域 -->
        <el-form :model="queryParams" ref="queryRef" :inline="true">
          <el-form-item label="股票代码" prop="stockCode">
            <el-input
              v-model="queryParams.stockCode"
              placeholder="请输入股票代码（如: 600000）"
              clearable
              style="width: 200px"
              @keyup.enter="calculateSimilarity"
            />
          </el-form-item>
          <el-form-item label="开始日期" prop="startDate">
            <el-date-picker
              v-model="queryParams.startDate"
              type="date"
              placeholder="选择开始日期"
              style="width: 200px"
              :disabled-date="disabledStartDate"
            />
          </el-form-item>
          <el-form-item label="结束日期" prop="endDate">
            <el-date-picker
              v-model="queryParams.endDate"
              type="date"
              placeholder="选择结束日期"
              style="width: 200px"
              :disabled-date="disabledEndDate"
            />
          </el-form-item>
          <el-form-item label="相似股票数量" prop="similarCount">
            <el-input-number
              v-model="queryParams.similarCount"
              :min="1"
              :max="10"
              style="width: 200px"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" icon="Search" @click="calculateSimilarity" :loading="loading">
              {{ loading ? '计算中...' : '计算相似性' }}
            </el-button>
            <el-button icon="Refresh" @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
  
        <!-- 分析参数配置 -->
        <el-card class="box-card mb-4">
          <template #header>
            <div class="card-header">
              <span>分析参数</span>
            </div>
          </template>
          
          <el-form :model="queryParams" label-width="120px">
            <el-form-item label="相似性计算方法" prop="similarityMethod">
              <el-select v-model="queryParams.similarityMethod" placeholder="请选择计算方法" style="width: 100%">
                <el-option label="皮尔森相关系数" value="pearson" />
                <el-option label="动态规整算法" value="dtw" />
                <el-option label="图匹配" value="graphMatching" />
                <el-option label="图神经网络" value="gnn" />
              </el-select>
            </el-form-item>

            <el-form-item label="指标选择" prop="indicators">
              <el-checkbox-group v-model="queryParams.indicators">
                <el-checkbox label="turnoverRate">换手率</el-checkbox>
                <el-checkbox label="highPriceChange">最高价涨幅</el-checkbox>
                <el-checkbox label="lowPriceChange">最低价涨幅</el-checkbox>
                <el-checkbox label="closePriceChange">收盘价涨幅</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            
            <el-form-item label="是否集成语言模型" prop="useLLM">
              <el-radio-group v-model="queryParams.useLLM">
                <el-radio :label="true">是</el-radio>
                <el-radio :label="false">否</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-form>
        </el-card>
  
        <!-- 结果展示区域 -->
        <div v-if="showResults">
          <el-card class="box-card" v-loading="loading">
            <template #header>
              <div class="card-header">
                <span>分析结果</span>
              </div>
            </template>
  
            <div v-if="!loading">
              <el-divider content-position="left">最相似的股票列表</el-divider>
              
              <el-row :gutter="20">
                <el-col :xs="24" :sm="12" :md="8" v-for="(stock, index) in similarStocks" :key="index">
                  <el-card shadow="hover" class="mb-4">
                    <div class="flex justify-between">
                      <span class="font-bold">{{ stock.code }}</span>
                      <span class="text-gray">{{ stock.name }}</span>
                    </div>
                    <div class="mt-2">
                      <span>相似度: </span>
                      <span :class="getSimilarityClass(stock.similarity)">
                        {{ (stock.similarity * 100).toFixed(2) }}%
                      </span>
                    </div>
                  </el-card>
                </el-col>
              </el-row>
  
              <el-divider content-position="left">收益率对比</el-divider>
              <div ref="chartRef" style="width: 100%; height: 400px;"></div>
  
              <div v-if="queryParams.useLLM">
                <el-divider content-position="left">语言模型分析</el-divider>
                <el-card shadow="hover" class="mb-4 bg-gray">
                  <span>{{ llmAnalysis }}</span>
                </el-card>
              </div>
            </div>
          </el-card>
        </div>
      </el-card>
    </div>
  </template>
  
  <script setup name="StockSimilarity">
  import { ref, reactive, onMounted, onUnmounted, nextTick, toRefs } from 'vue';
  import * as echarts from 'echarts/core';
  import { LineChart } from 'echarts/charts';
  import {
    TitleComponent,
    TooltipComponent,
    LegendComponent,
    GridComponent,
    ToolboxComponent,
    DataZoomComponent
  } from 'echarts/components';
  import { CanvasRenderer } from 'echarts/renderers';
  import { calculateStockSimilarity } from '@/api/system/stockSimilar.js';
  import { ElMessage } from 'element-plus';
  
  const { proxy } = getCurrentInstance();
  
  // 注册 ECharts 组件
  echarts.use([
    TitleComponent,
    TooltipComponent,
    LegendComponent,
    GridComponent,
    ToolboxComponent,
    DataZoomComponent,
    LineChart,
    CanvasRenderer
  ]);
  
  // 响应式状态
  const loading = ref(false);
  const showResults = ref(false);
  const similarStocks = ref([]);
  const llmAnalysis = ref('');
  const chartRef = ref(null);
  
  // 查询参数和表单
  const data = reactive({
    queryParams: {
      stockCode: '',
      startDate: getDefaultStartDate(),
      endDate: getDefaultEndDate(),
      indicators: ['closePriceChange'],
      similarityMethod: 'pearson',
      useLLM: false,
      similarCount: 3
    }
  });
  
  const { queryParams } = toRefs(data);
  
  // 图表实例
  let chartInstance = null;
  
  // 实例化计算工具
  const calculator = new calculateStockSimilarity();
   // 定义最小和最大日期
    const minDate = new Date('1990-12-18')
    const maxDate = new Date('2025-02-19')
    // 禁用早于1990-12-18的日期
  const disabledStartDate = (time) => {
    return time < minDate || time > maxDate || 
           (queryParams.endDate && time > queryParams.endDate)
  }

  // 禁用晚于2025-02-19的日期
  const disabledEndDate = (time) => {
    return time < minDate || time > maxDate || 
           (queryParams.startDate && time < queryParams.startDate)
  }

  // 生命周期钩子
  onMounted(() => {
    window.addEventListener('resize', handleResize);
  });
  
  onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
    if (chartInstance) {
      chartInstance.dispose();
    }
  });
  
  // 方法
  function getDefaultStartDate() {
    const endDate = new Date('2025-02-18');
    // 将月份减去1
    endDate.setMonth(endDate.getMonth() - 1);
    return endDate.toISOString().split('T')[0];
}

function getDefaultEndDate() {
    return '2025-02-18';
}
  
  function handleResize() {
    if (chartInstance) {
      chartInstance.resize();
    }
  }
  
  function getSimilarityClass(similarity) {
    if (similarity > 0.8) return 'text-danger';
    if (similarity > 0.6) return 'text-warning';
    return 'text-primary';
  }
  
  function resetQuery() {
    proxy.$refs["queryRef"].resetFields();
    showResults.value = false;
  }
  
  async function calculateSimilarity() {
    if (!queryParams.value.stockCode) {
      ElMessage.warning('请输入股票代码');
      return;
    }
    
    if (queryParams.value.indicators.length === 0) {
      ElMessage.warning('请至少选择一个指标');
      return;
    }
    
    loading.value = true;
    showResults.value = true;
    
    try {
      const result = await calculator.calculateSimilarity({
        stockCode: queryParams.value.stockCode,
        startDate: queryParams.value.startDate,
        endDate: queryParams.value.endDate,
        indicators: queryParams.value.indicators,
        similarityMethod: queryParams.value.similarityMethod,
        useLLM: queryParams.value.useLLM,
        similarCount: queryParams.value.similarCount
      });
      
      similarStocks.value = result.similarStocks;
      llmAnalysis.value = result.llmAnalysis || '';
      
      await nextTick();
      drawChart(result.performanceData);
      ElMessage.success('分析完成');
    } catch (error) {
      console.error('计算相似性出错:', error);
      ElMessage.error('计算过程中出现错误，请检查输入并重试');
    } finally {
      loading.value = false;
    }
  }
  
  function drawChart(data) {
    if (!chartRef.value) return;
    
    // 如果已存在图表实例，先销毁
    if (chartInstance) {
      chartInstance.dispose();
    }
    
    // 初始化图表
    chartInstance = echarts.init(chartRef.value);
    
    const series = data.stocks.map(stock => ({
      name: `${stock.code} ${stock.name || ''}`,
      type: 'line',
      data: stock.returns,
      smooth: true
    }));
    
    const option = {
      tooltip: {
        trigger: 'axis',
        formatter: function(params) {
          let result = params[0].axisValue + '<br/>';
          params.forEach(param => {
            result += `${param.seriesName}: ${param.value.toFixed(2)}%<br/>`;
          });
          return result;
        }
      },
      legend: {
        data: data.stocks.map(stock => `${stock.code} ${stock.name || ''}`),
        type: 'scroll',
        bottom: 0
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: data.dates
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: '{value}%'
        }
      },
      series: series,
      toolbox: {
        feature: {
          saveAsImage: {}
        }
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100
        },
        {
          start: 0,
          end: 100
        }
      ]
    };
    
    chartInstance.setOption(option);
  }
  </script>
  
  <style scoped>
  .app-container {
    padding: 20px;
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .mb-4 {
    margin-bottom: 16px;
  }
  
  .font-bold {
    font-weight: bold;
  }
  
  .text-gray {
    color: #909399;
  }
  
  .text-danger {
    color: #f56c6c;
  }
  
  .text-warning {
    color: #e6a23c;
  }
  
  .text-primary {
    color: #409eff;
  }
  
  .mt-2 {
    margin-top: 8px;
  }
  
  .flex {
    display: flex;
  }
  
  .justify-between {
    justify-content: space-between;
  }
  
  .bg-gray {
    background-color: #f5f7fa;
  }
  </style>