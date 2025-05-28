<template>
    <div class="app-container">
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span class="font-bold">股票相似性分析工具</span>
          </div>
        </template>

        <!-- 查询区域 -->
      <el-card class="box-card mb-4">
        <template #header>
            <div class="card-header">
              <span>股票信息</span>
            </div>
          </template>
        <el-form :model="queryParams" ref="queryRef" :inline="true">
          <el-form-item label="股票代码" prop="stockCode">
            <el-autocomplete
              v-model="queryParams.stockCode"
              :fetch-suggestions="fuzzySearchUnified"
              placeholder="请输入股票代码（如: 600000）"
              clearable
              style="width: 200px"
              :popper-class="'full-dropdown'"
              @select="handleStockSelect"
            >
            <template #default="{ item }">
                <div>{{ item.stock_code }} {{ item.value }}</div>
              </template>
            </el-autocomplete>
          </el-form-item>
          <el-form-item label="股票名称" prop="stockName">
            <el-autocomplete
              v-model="queryParams.stockName"
              :fetch-suggestions="fuzzySearchUnified"
              placeholder="可输入股票名称（如: 浦发银行）"
              clearable
              style="width: 200px"
              :popper-class="'full-dropdown'"
              @select="handleStockSelect"
            >
            <template #default="{ item }">
                <div>{{ item.stock_code }} {{ item.value }}</div>
              </template>
            </el-autocomplete>
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
          <el-button icon="Refresh" @click="resetQueryStock">重置</el-button>
        </el-form>
      </el-card>
        <!-- 分析参数配置 -->
        <el-card class="box-card mb-4">
          <template #header>
            <div class="card-header">
              <span>调整参数</span>
            </div>
          </template>

          <el-form :model="queryParams" label-width="120px">
            <el-form-item label="相似性计算方法" prop="similarityMethod">
              <el-select v-model="queryParams.similarityMethod" placeholder="请选择计算方法" style="width: 100%">
                <el-option label="皮尔森相关系数" value="pearson" />
                <el-option label="欧氏距离" value="euclidean" />
                <el-option label="协整性" value="coIntegration" />
                <el-option label="动态规整算法" value="dtw" />
                <el-option label="图编辑距离" value="graphEditing" />
                <el-option label="最大公共子图" value="maxCommonSubgraph" />
                <el-option label="形态相似性" value="shape" />
                <el-option label="位置相似性" value="position" />
              </el-select>
            </el-form-item>

            <el-form-item
              label="指标选择"
              prop="indicators"
              v-if="!['shape', 'position'].includes(queryParams.similarityMethod)"
            >
              <el-checkbox-group v-model="queryParams.indicators">
                <el-checkbox label="turnover">换手率</el-checkbox>
                <el-checkbox label="high">最高价涨幅</el-checkbox>
                <el-checkbox label="low">最低价涨幅</el-checkbox>
                <el-checkbox label="close">收盘价涨幅</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="相似性对比范围" prop="sectionLevel">
              <el-select v-model="queryParams.sectionLevel" placeholder="相似性对比范围" style="width: 200px">
                <el-option label="中证三级行业" :value=1 />
                <el-option label="证监会一级行业" :value=0 />
              </el-select>
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
            </div>
          </el-card>
        </div>
      </el-card>
    </div>
  </template>

  <script setup name="StockSimilarity">
  import { ref, reactive, watch, onMounted, onUnmounted, nextTick, toRefs, computed,getCurrentInstance  } from 'vue';
  import { useRoute } from 'vue-router';
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
  import { calculateStockSimilarity,fuzzySearch } from '@/api/stock/stockSimilar.js';
  import { ElMessage } from 'element-plus';
  import useUserStore from '@/store/modules/user';
  import { addQueryHistoryList } from '../../api/stock/stockHistory';
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
  // 获取当前路由对象
  const route = useRoute();
  // 响应式状态
  const loading = ref(false);
  const showResults = ref(false);
  const similarStocks = ref([]);
  const chartRef = ref(null);
  // 查询参数和表单
  const data = reactive({
    queryParams: {
      stockCode: '',
      stockName: '',
      startDate: getDefaultStartDate(),
      endDate: getDefaultEndDate(),
      sectionLevel: 1,
      indicators: ['close'],
      similarityMethod: 'pearson',
      similarCount: 3
    }
  });
  const stockOptions = ref([]); // 候选项
  const showDropdown = ref(false); // 这个变量现在可能不再需要直接控制下拉框显示，但可以保留用于其他目的

  // 用户store
  const userStore = useUserStore();
  // 获取用户ID
  const currentUserId = computed(() => userStore.id);
  const { queryParams } = toRefs(data);

  // 图表实例
  let chartInstance = null;

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
    console.log('组件已挂载');
    console.log('showResults:', showResults.value);
    console.log('similarStocks:', similarStocks.value);
    console.log('chartRef:', chartRef.value);
    window.addEventListener('resize', handleResize);

    // 新增：检查URL参数并填充表单
    if (route.query.stockCode) {
      console.log('检测到路由参数:', route.query);

      // 填充股票代码
      queryParams.value.stockCode = route.query.stockCode;

      // 填充开始日期和结束日期（如果存在）
      if (route.query.startTime) {
        // 确保日期格式正确
        queryParams.value.startDate = new Date(route.query.startTime);
      }

      if (route.query.endTime) {
        // 确保日期格式正确
        queryParams.value.endDate = new Date(route.query.endTime);
      }
      if(route.query.stockName) {
        queryParams.value.stockName = route.query.stockName;
      }

      // 可选：自动触发查询
      // 如果希望页面加载后自动执行查询，可以取消下面这行的注释
      // nextTick(() => calculateSimilarity());
    }

    console.log('showResults:', showResults.value);
    console.log('similarStocks:', similarStocks.value);
    console.log('chartRef:', chartRef.value);
  });

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
    if (chartInstance) {
      chartInstance.dispose();
    }
  });


  // 股票代码输入时自动模糊搜索 (el-autocomplete 会调用 cb)
async function fuzzySearchUnified(queryString, cb) {
  console.log(`--- fuzzySearchUnified triggered for: "${queryString}" ---`);
  if (!queryString) {
    console.log("Empty queryString, calling cb([])");
    stockOptions.value = [];
    cb([]);
    // showDropdown.value = false; // 移除此行
    return;
  }
  try {
    const res = await fuzzySearch(queryString);
    const list = (res.data || []).map(item => ({
      value: item.name, 
      stock_code: item.code 
    }));


    stockOptions.value = list; // 更新本地状态
    cb(list); // 调用回调函数传递给 el-autocomplete

  } catch (e) {
    console.error("模糊搜索出错:", e); // 打印错误信息
    stockOptions.value = [];
    cb([]); // 搜索出错也调用回调函数，并传递空数组
     console.log("cb([]) called due to error");
  }
   console.log(`--- fuzzySearchUnified finished for: "${queryString}" ---`);
}

function handleStockSelect(item) {
  queryParams.value.stockName = item.value;
  queryParams.value.stockCode = item.stock_code;
  showDropdown.value = false; // 保留这行，选中后隐藏自定义控制的下拉框
  stockOptions.value = []; // 保留这行，清空候选项
}

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
  function formatDate(date) {
  const d = new Date(date);
  return d.toISOString().split('T')[0];
}

  function getSimilarityClass(similarity) {
    // if (similarity > 0.2) return 'text-danger';
    // if (similarity > 0.1) return 'text-warning';
    // return 'text-primary';
    const value = parseFloat(similarity);
    if (value >= 0.9) return 'text-success';
    if (value >= 0.5) return 'text-warning';
    return 'text-danger';
  }

  function resetQueryStock() {
  // 修改这里，确保表单引用存在
  if (proxy.$refs["queryRef"]) {
    proxy.$refs["queryRef"].resetFields();
  } else {
    // 如果引用不存在，则手动重置
    queryParams.value.stockCode = '';
    queryParams.value.stockName = '';
    queryParams.value.startDate = getDefaultStartDate();
    queryParams.value.endDate = getDefaultEndDate();
  }
  showResults.value = false;
}

function resetQuery() {
  // 修改这里，确保表单引用存在
  if (proxy.$refs["queryRef"]) {
    proxy.$refs["queryRef"].resetFields();
  } else {
    // 如果引用不存在，则手动重置
    queryParams.value.sectionLevel = 1;
    queryParams.value.indicators = ['close'];
    queryParams.value.similarityMethod = 'pearson';
    queryParams.value.similarCount = 3;
  }
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
      // 先等待DOM更新
    await nextTick();

    try {
      const result = await calculateStockSimilarity({
        stockCode: queryParams.value.stockCode,
        startDate: formatDate(queryParams.value.startDate),
        endDate: formatDate(queryParams.value.endDate),
        sectionLevel: queryParams.value.sectionLevel,
        indicators: queryParams.value.indicators,
        similarityMethod: queryParams.value.similarityMethod,
        similarCount: queryParams.value.similarCount
      });
      console.log('后端返回数据:', result);
      similarStocks.value = result.data.similarStocks;

       // 再次等待DOM更新，确保结果区域已渲染
      await nextTick();
      // 再等一下以确保所有DOM都已渲染完成
      setTimeout(() => {
        drawChart(result.data.performanceData);
      }, 100);
      ElMessage.success('分析完成');
      console.log("用户ID:", currentUserId.value);
  ;
      const historyData = {
        stock_code: queryParams.value.stockCode,  // 改为下划线命名
        stock_name: queryParams.value.stockName || "未知",  // 确保不为空
        start_date: formatDate(queryParams.value.startDate),
        end_date: formatDate(queryParams.value.endDate),
        indicators: queryParams.value.indicators,
        method: queryParams.value.similarityMethod,
        compare_scope: String(queryParams.value.sectionLevel),
        similar_count: parseInt(queryParams.value.similarCount, 10),
        user_id: currentUserId.value,  // 转为整数
        status: 1,
        query_time: new Date().toISOString(),
        similar_results: similarStocks.value.map(stock => ({
          stock_code: stock.code,  // 修改嵌套对象的字段名
          stock_name: stock.name,
          similarity: stock.similarity
        }))
      }
        try {
          const response = await addQueryHistoryList(historyData);
          console.log('提交成功:', response);
          ElMessage.success('查询历史记录保存成功');
        } catch (error) {
          console.error('提交失败:', error);

          // 打印详细的错误信息
          if (error.response && error.response.data) {
            console.error('错误响应数据:', JSON.stringify(error.response.data, null, 2));

            if (error.response.data.detail) {
              // 完整打印详情数组
              console.error('验证错误详情:', JSON.stringify(error.response.data.detail, null, 2));

              let errorMsg = '';
              if (Array.isArray(error.response.data.detail)) {
                errorMsg = error.response.data.detail.map(item => {
                  // 提取字段位置和错误消息
                  const loc = item.loc ? item.loc.slice(1).join('.') : '';
                  return `${loc ? loc + ': ' : ''}${item.msg}`;
                }).join('; ');
              } else {
                errorMsg = JSON.stringify(error.response.data.detail);
              }
              ElMessage.error(`保存失败: ${errorMsg}`);
            } else {
              ElMessage.error('保存失败: ' + (error.response.data.message || '未知错误'));
            }
          } else {
            ElMessage.error('系统异常，请稍后再试');
          }
        }
    } catch (error) {
      console.error('计算相似性出错:', error);
      ElMessage.error('计算过程中出现错误，请检查输入并重试');
    } finally {
      loading.value = false;
    }
  }
function drawChart(data) {
  console.log('绘制图表数据:', data);
  // 增加更多的防御性检查
  if (!chartRef.value) {
    console.error('图表引用不存在，可能是DOM尚未渲染');
    // 更长的延迟
    setTimeout(() => drawChart(data), 300);
    return;
  }
  // 增强数据验证
  if (!data) {
    console.error('图表数据为空或未定义');
    return;
  }

  // 打印数据结构以便调试
  // console.log('数据类型:', typeof data);
  if (typeof data === 'object') {
    console.log('数据属性:', Object.keys(data));
  console.log('图表引用状态:', chartRef.value);

  // 如果图表引用不存在，使用setTimeout尝试延迟绘制
  if (!chartRef.value) {
    console.warn('图表引用暂时不存在，将在100ms后重试');
    setTimeout(() => {
      if (chartRef.value) {
        console.log('延迟后找到图表引用，开始绘制');
        drawChartImplementation(data);
      } else {
        console.error('延迟后仍未找到图表引用，绘制失败');
      }
    }, 100);
    return;
  }

  // 如果图表引用存在，直接绘制
  drawChartImplementation(data);
  }
}

// 将绘制逻辑抽离到单独的函数
function drawChartImplementation(data) {
  // 增强数据验证
  if (!data) {
    console.error('图表数据为空或未定义');
    return;
  }

  // 检查数据结构
  if (!data || !data.stocks || !data.dates) {
    console.error('图表数据结构不正确');
    return;
  }
  console.log('准备绘制图表，数据:', {
    stocks: data.stocks,
    dates: data.dates
  });

  // 如果已存在图表实例，先销毁
  if (chartInstance) {
    chartInstance.dispose();
  }

  // 初始化图表
  try {
    chartInstance = echarts.init(chartRef.value);

    // 确保每个股票都有returns属性
    const series = data.stocks.map(stock => {
      if (!stock.data || !Array.isArray(stock.data)) {
        console.warn(`股票 ${stock.code} 没有returns数据或格式不正确`);
        return {
          name: `${stock.code} ${stock.name || ''}`,
          type: 'line',
          data: [],
          smooth: true
        };
      }

      return {
        name: `${stock.code} ${stock.name || ''}`,
        type: 'line',
        data: stock.data,
        smooth: true
      };
    });

    const option = {
      // 图表配置保持不变
      tooltip: {
        trigger: 'axis',
        formatter: function(params) {
          let result = params[0].axisValue + '<br/>';
          params.forEach(param => {
            const value = typeof param.value === 'number' ? param.value.toFixed(2) : 'N/A';
            result += `${param.seriesName}: ${value}%<br/>`;
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
    console.log('图表绘制成功');
  } catch (error) {
    console.error('绘制图表时出错:', error);
  }
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
  /* 删除按钮样式 */
.delete-button {
  margin-left: 10px;
  padding: 8px;
  background: none;
  border: 1px solid #d0d0d0;
  border-radius: 4px;
  cursor: pointer;
  color: #666;
  transition: all 0.3s;
}

.delete-button:hover {
  background: #f0f0f0;
}

.delete-button.active {
  background: #f5222d;
  color: white;
  border-color: #f5222d;
}

/* 选择模式栏 */
.select-mode-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f5f5f5;
  padding: 10px 15px;
  margin-bottom: 15px;
  border-radius: 4px;
}

.select-mode-actions {
  display: flex;
  gap: 10px;
}

.select-all-button,
.cancel-button,
.confirm-delete-button {
  padding: 6px 12px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.select-all-button {
  background: #f0f0f0;
  color: #333;
}

.cancel-button {
  background: #d9d9d9;
  color: #333;
}

.confirm-delete-button {
  background: #f5222d;
  color: white;
}

.confirm-delete-button:disabled {
  background: #ffb8b8;
  cursor: not-allowed;
}

/* 查询项选择框 */
.query-item {
  display: flex;
  position: relative;
}

.select-checkbox {
  position: absolute;
  left: 15px;
  top: 20px;
  z-index: 5;
  font-size: 20px;
  color: #d9d9d9;
}

.query-item.selected .select-checkbox {
  color: #1890ff;
}

/* 选择模式下的查询项调整 */
.query-item.selected {
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.05);
}
  </style>