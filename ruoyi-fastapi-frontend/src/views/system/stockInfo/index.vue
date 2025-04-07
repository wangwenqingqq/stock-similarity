<template>
  <div class="app-container">
     <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
        <el-form-item label="股票代码" prop="stockCode">
           <el-input
              v-model="queryParams.stockCode"
              placeholder="请输入股票代码"
              clearable
              style="width: 200px"
              @keyup.enter="handleQuery"
           />
        </el-form-item>
        <el-form-item label="股票名称" prop="stockName">
           <el-input
              v-model="queryParams.stockName"
              placeholder="请输入股票名称"
              clearable
              style="width: 200px"
              @keyup.enter="handleQuery"
           />
        </el-form-item>
        <el-form-item label="状态" prop="status">
           <el-select v-model="queryParams.status" placeholder="股票状态" clearable style="width: 200px">
              <el-option
                 v-for="dict in sys_stock_status"
                 :key="dict.value"
                 :label="dict.label"
                 :value="dict.value"
              />
           </el-select>
        </el-form-item>
        <el-form-item>
           <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
           <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
     </el-form>

     <el-row :gutter="10" class="mb8">
        <el-col :span="1.5">
           <el-button
              type="primary"
              plain
              icon="Plus"
              @click="handleAdd"
              v-hasPermi="['system:stockInfo:add']"
           >新增</el-button>
        </el-col>
        <el-col :span="1.5">
           <el-button
              type="success"
              plain
              icon="Edit"
              :disabled="single"
              @click="handleUpdate"
              v-hasPermi="['system:stockInfo:edit']"
           >修改</el-button>
        </el-col>
        <el-col :span="1.5">
           <el-button
              type="danger"
              plain
              icon="Delete"
              :disabled="multiple"
              @click="handleDelete"
              v-hasPermi="['system:stockInfo:remove']"
           >删除</el-button>
        </el-col>
        <el-col :span="1.5">
           <el-button
              type="warning"
              plain
              icon="Download"
              @click="handleExport"
              v-hasPermi="['system:stockInfo:export']"
           >导出</el-button>
        </el-col>
        <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
     </el-row>

     <el-table v-loading="loading" :data="stockList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="股票编号" align="center" prop="stockId" />
        <el-table-column label="股票代码" align="center" prop="stockCode" />
        <el-table-column label="股票名称" align="center" prop="stockName" />
        <el-table-column label="当前价格" align="center" prop="currentPrice" />
        <el-table-column label="状态" align="center" prop="status">
           <template #default="scope">
              <dict-tag :options="sys_stock_status" :value="scope.row.status" />
           </template>
        </el-table-column>
        <el-table-column label="创建时间" align="center" prop="createTime" width="180">
           <template #default="scope">
              <span>{{ parseTime(scope.row.createTime) }}</span>
           </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" class-name="small-padding fixed-width">
           <template #default="scope">
              <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)" v-hasPermi="['system:stockInfo:edit']">修改</el-button>
              <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)" v-hasPermi="['system:stockInfo:remove']">删除</el-button>
           </template>
        </el-table-column>
     </el-table>

     <pagination
        v-show="total > 0"
        :total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="getList"
     />

     <!-- 添加或修改股票信息对话框 -->
     <el-dialog :title="title" v-model="open" width="500px" append-to-body>
        <el-form ref="stockRef" :model="form" :rules="rules" label-width="80px">
           <el-form-item label="股票名称" prop="stockName">
              <el-input v-model="form.stockName" placeholder="请输入股票名称" />
           </el-form-item>
           <el-form-item label="股票代码" prop="stockCode">
              <el-input v-model="form.stockCode" placeholder="请输入股票代码" />
           </el-form-item>
           <el-form-item label="当前价格" prop="currentPrice">
              <el-input-number v-model="form.currentPrice" controls-position="right" :min="0" />
           </el-form-item>
           <el-form-item label="股票状态" prop="status">
              <el-radio-group v-model="form.status">
                 <el-radio
                    v-for="dict in sys_stock_status"
                    :key="dict.value"
                    :value="dict.value"
                 >{{ dict.label }}</el-radio>
              </el-radio-group>
           </el-form-item>
           <el-form-item label="备注" prop="remark">
              <el-input v-model="form.remark" type="textarea" placeholder="请输入内容" />
           </el-form-item>
        </el-form>
        <template #footer>
           <div class="dialog-footer">
              <el-button type="primary" @click="submitForm">确 定</el-button>
              <el-button @click="cancel">取 消</el-button>
           </div>
        </template>
     </el-dialog>
  </div>
</template>

<script setup name="StockInfo">
import { listStockInfo, addStockInfo, delStockInfo, getStockInfo, updateStockInfo } from "@/api/system/stockInfo";

const { proxy } = getCurrentInstance();
const { sys_stock_status } = proxy.useDict("sys_stock_status");

const stockList = ref([]);
const open = ref(false);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);
const title = ref("");

const data = reactive({
 form: {},
 queryParams: {
   pageNum: 1,
   pageSize: 10,
   stockCode: undefined,
   stockName: undefined,
   status: undefined
 },
 rules: {
   stockName: [{ required: true, message: "股票名称不能为空", trigger: "blur" }],
   stockCode: [{ required: true, message: "股票代码不能为空", trigger: "blur" }],
   currentPrice: [{ required: true, message: "当前价格不能为空", trigger: "blur" }],
 }
});

const { queryParams, form, rules } = toRefs(data);

/** 查询股票信息列表 */
function getList() {
 loading.value = true;
 listStockInfo(queryParams.value).then(response => {
   stockList.value = response.rows;
   total.value = response.total;
   loading.value = false;
 });
}
/** 取消按钮 */
function cancel() {
 open.value = false;
 reset();
}
/** 表单重置 */
function reset() {
 form.value = {
   stockId: undefined,
   stockCode: undefined,
   stockName: undefined,
   currentPrice: 0,
   status: "0",
   remark: undefined
 };
 proxy.resetForm("stockRef");
}
/** 搜索按钮操作 */
function handleQuery() {
 queryParams.value.pageNum = 1;
 getList();
}
/** 重置按钮操作 */
function resetQuery() {
 proxy.resetForm("queryRef");
 handleQuery();
}
/** 多选框选中数据 */
function handleSelectionChange(selection) {
 ids.value = selection.map(item => item.stockId);
 single.value = selection.length != 1;
 multiple.value = !selection.length;
}
/** 新增按钮操作 */
function handleAdd() {
 reset();
 open.value = true;
 title.value = "添加股票信息";
}
/** 修改按钮操作 */
function handleUpdate(row) {
 reset();
 const stockId = row.stockId || ids.value;
 getStockInfo(stockId).then(response => {
   form.value = response.data;
   open.value = true;
   title.value = "修改股票信息";
 });
}
/** 提交按钮 */
function submitForm() {
 proxy.$refs["stockRef"].validate(valid => {
   if (valid) {
     if (form.value.stockId != undefined) {
       updateStockInfo(form.value).then(response => {
         proxy.$modal.msgSuccess("修改成功");
         open.value = false;
         getList();
       });
     } else {
       addStockInfo(form.value).then(response => {
         proxy.$modal.msgSuccess("新增成功");
         open.value = false;
         getList();
       });
     }
   }
 });
}
/** 删除按钮操作 */
function handleDelete(row) {
 const stockIds = row.stockId || ids.value;
 proxy.$modal.confirm('是否确认删除股票编号为"' + stockIds + '"的数据项？').then(function() {
   return delStockInfo(stockIds);
 }).then(() => {
   getList();
   proxy.$modal.msgSuccess("删除成功");
 }).catch(() => {});
}
/** 导出按钮操作 */
function handleExport() {
 proxy.download("system/stockInfo/export", {
   ...queryParams.value
 }, `stockInfo_${new Date().getTime()}.xlsx`);
}

getList();
</script>