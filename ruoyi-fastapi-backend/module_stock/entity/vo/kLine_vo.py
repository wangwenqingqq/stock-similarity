from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


class StockBase(BaseModel):
    """股票基本信息模型"""
    code: Optional[str] = Field("", description="股票代码")  # 允许None，默认为空字符串
    name: Optional[str] = Field("", description="股票名称")  # 允许None，默认为空字符串

class Stock(StockBase):
    """股票详细信息模型"""
    price: Optional[float] = Field(0.0, description="最新价格")  # 添加默认值
    change_rate: Optional[float] = Field(0.0, description="涨跌幅")
    # 将volume改为float，允许小数
    volume: Optional[float] = Field(0.0, description="成交量(手)")
    amount: Optional[float] = Field(0.0, description="成交额(元)")  # 添加默认值
    high: Optional[float] = Field(0.0, description="最高价")
    low: Optional[float] = Field(0.0, description="最低价")
    open: Optional[float] = Field(0.0, description="开盘价")
    pre_close: Optional[float] = Field(0.0, description="昨收价")
    seven_day_return: Optional[float] = Field(0.0, description="7日收益率")
    thirty_day_return: Optional[float] = Field(None, description="30日收益率")
    update_time: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        orm_mode = True
        # 添加额外配置以更宽松地处理数据
        extra = "ignore"  # 忽略额外字段
        arbitrary_types_allowed = True  # 允许任意类型

class StockListResponse(BaseModel):
    """股票列表响应模型"""
    items: List[Stock] = Field(default_factory=list, description="股票列表")  # 使用default_factory
    total: Optional[int] = Field(0, description="总数量")  # 增加默认值


class StockQueryParams(BaseModel):
    """股票查询参数模型"""
    page: int = Field(1, description="页码")
    page_size: int = Field(20, description="每页大小")
    sort_by: str = Field("seven_day_return", description="排序字段")
    sort_order: str = Field("desc", description="排序方式")
    keyword: Optional[str] = Field(None, description="搜索关键词")


class KlineDataResponse(BaseModel):
    """K线图数据模型"""
    categories: List[str] = Field(..., description="日期分类数据")
    values: List[List[float]] = Field(..., description="K线数据 [open, close, low, high]")
    close: Optional[List[float]] = Field(None, description="收盘价数据，仅用于相似股票对比")
    ma5: List[float] = Field(..., description="MA5均线数据")
    ma10: List[float] = Field(..., description="MA10均线数据")
    ma30: List[float] = Field(..., description="MA30均线数据")
    volumes: Optional[List[float]] = Field(None, description="成交量数据")
    stockName: str  # 股票名称
    stockCode: str  # 股票代码


class KlineQueryParams(BaseModel):
    """K线图查询参数模型"""
    time_range: str = Field("day", description="时间范围：day-日K, week-周K, month-月K")
    data_type: Optional[str] = Field(None, description="数据类型：若为'close'则仅返回收盘价")


class SimilarStockResponse(StockBase):
    """相似股票信息模型"""
    stockName: str  # 股票名称
    stockCode: str  # 股票代码
    similarity: float = Field(..., description="相似度（0-1之间的值，越接近1表示越相似）")
    correlation: Optional[float] = Field(None, description="相关系数")
    seven_day_return: float = Field(..., description="7日收益率")
    thirty_day_return: Optional[float] = Field(None, description="30日收益率")


# API响应的通用模型
class ResponseModel(BaseModel):
    """API通用响应模型"""
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")