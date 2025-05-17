from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class StockBaseModel(BaseModel):
    """股票基础模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    price: float = Field(..., description="当前价格")
    change: float = Field(..., description="涨跌幅")


class StockDetailModel(StockBaseModel):
    """股票详细信息模型"""
    open: float = Field(..., description="开盘价")
    close: float = Field(..., description="收盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    volume: int = Field(..., description="成交量")
    update_time: datetime = Field(..., description="更新时间")

class StockAddToWatchlistRequest(BaseModel):
    """股票添加到关注列表请求模型"""
    stock_code: str = Field(..., description="股票代码")
    user_id: str = Field(None, description="用户ID")
    status: int = Field(..., description="关注状态，1表示已关注，0表示未关注")

class StockHistoryModel(BaseModel):
    """股票历史数据模型"""
    date: str = Field(..., description="日期")
    open: float = Field(..., description="开盘价")
    close: float = Field(..., description="收盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    volume: int = Field(..., description="成交量")


class StockDetailWithHistoryModel(StockDetailModel):
    """包含历史数据的股票详细信息模型"""
    history: List[StockHistoryModel] = Field(default_factory=list, description="历史数据")


class StockIndexModel(BaseModel):
    """股票指数模型"""
    name: str = Field(..., description="指数名称")
    code: str = Field(..., description="指数代码")
    current: float = Field(..., description="当前点位")
    change: float = Field(..., description="涨跌幅")


class StockMarketOverviewModel(BaseModel):
    """市场概览模型"""
    date: str = Field(..., description="日期")
    indexes: List[StockIndexModel] = Field(default_factory=list, description="指数列表")


class PaginationModel(BaseModel):
    """分页模型"""
    current: int = Field(..., description="当前页")
    pageSize: int = Field(..., description="每页大小")
    total: int = Field(..., description="总记录数")


class StockListModel(BaseModel):
    """股票列表返回模型"""
    list: List[StockBaseModel] = Field(default_factory=list, description="股票列表")
    pagination: PaginationModel = Field(..., description="分页信息")


# 接口响应模型
class StockListResponse(BaseModel):
    """股票列表接口响应"""
    code: int = Field(..., description="响应代码")
    msg: str = Field(..., description="响应消息")
    data: Optional[StockListModel] = Field(None, description="股票列表数据")


class StockSearchResponse(BaseModel):
    """股票搜索接口响应"""
    code: int = Field(..., description="响应代码")
    msg: str = Field(..., description="响应消息")
    data: Optional[List[StockBaseModel]] = Field(None, description="搜索结果")


class StockDetailResponse(BaseModel):
    """股票详情接口响应"""
    code: int = Field(..., description="响应代码")
    msg: str = Field(..., description="响应消息")
    data: Optional[StockDetailWithHistoryModel] = Field(None, description="股票详情数据")


class StockWatchlistResponse(BaseModel):
    """用户关注股票列表接口响应"""
    code: int = Field(..., description="响应代码")
    msg: str = Field(..., description="响应消息")
    data: Optional[List[StockBaseModel]] = Field(None, description="关注的股票列表")


class StockWatchlistAddResponse(BaseModel):
    """添加股票到关注列表接口响应"""
    code: int = Field(..., description="响应代码")
    msg: str = Field(..., description="响应消息")


class StockWatchlistRemoveResponse(BaseModel):
    """从关注列表移除股票接口响应"""
    code: int = Field(..., description="响应代码")
    msg: str = Field(..., description="响应消息")


class StockWatchlistClearResponse(BaseModel):
    """清空关注列表接口响应"""
    code: int = Field(..., description="响应代码")
    msg: str = Field(..., description="响应消息")


class StockMarketOverviewResponse(BaseModel):
    """市场概览接口响应"""
    code: int = Field(..., description="响应代码")
    msg: str = Field(..., description="响应消息")
    data: Optional[StockMarketOverviewModel] = Field(None, description="市场概览数据")