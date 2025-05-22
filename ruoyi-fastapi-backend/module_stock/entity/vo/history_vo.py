from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class SimilarStockResultVO(BaseModel):
    """相似股票结果视图对象"""
    stock_code: str
    stock_name: str
    similarity: float

    class Config:
        orm_mode = True
class QueryHistoryVO(BaseModel):
    """查询历史视图对象"""
    stock_code: str = Field(..., alias="stock_code")
    stock_name: str = Field(..., alias="stock_name")
    start_date: str = Field(..., alias="start_date")
    end_date: str = Field(..., alias="end_date")
    indicators: List[str]
    method: str
    compare_scope: str = Field(..., alias="compare_scope")
    similar_count: int = Field(..., alias="similar_count")
    user_id: int = Field(None, alias="user_id")
    remark: Optional[str] = None
    query_time: str = Field(..., alias="query_time")
    status: int = 1,
    similar_results : List[SimilarStockResultVO] = Field(..., alias="similar_results")

class QueryHistoryDetailVO(BaseModel):
    """查询历史详情视图对象"""
    id: int
    stock_code: str
    stock_name: str
    query_time: datetime
    start_date: str
    end_date: str
    indicators: List[str]
    method: str
    compare_scope: str
    similar_count: int
    results: List[SimilarStockResultVO]
    user_id: int
    remark: Optional[str] = None
    status: int = 1

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryHistoryListResponse(BaseModel):
    """查询历史列表响应"""
    items: List[QueryHistoryVO]
    total: int
    page: int = 1
    pageSize: int = 10


class QueryHistoryDetailResponse(BaseModel):
    """查询历史详情响应"""
    id: int
    stock_code: str
    stock_name: str
    query_time: datetime
    start_date: str
    end_date: str
    indicators: List[str]
    method: str
    compare_scope: str
    similar_count: int
    results: List[SimilarStockResultVO]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryHistorySearchResponse(BaseModel):
    """查询历史搜索响应"""
    items: List[QueryHistoryVO]
    keyword: str
    total: int


class SimilarStocksDetailResponse(BaseModel):
    """相似股票详情响应"""
    historyId: int
    stock_code: str
    stock_name: str
    queryTime: datetime
    results: List[SimilarStockResultVO]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HotStockVO(BaseModel):
    """热门股票视图对象"""
    stock_code: str
    stock_name: str
    query_count: int


class DailyCountVO(BaseModel):
    """每日统计视图对象"""
    date: str
    count: int


class QueryHistoryStatisticsResponse(BaseModel):
    """查询历史统计响应"""
    totalCount: int
    dateRange: str
    hotStocks: List[HotStockVO]
    dailyCounts: List[DailyCountVO]
    methodDistribution: Dict[str, int]


class RecentQueryHistoryResponse(BaseModel):
    """最近查询历史响应"""
    items: List[QueryHistoryVO]
    limit: int


class ClearHistoryResponse(BaseModel):
    """清空历史响应"""
    clearedCount: int
    success: bool


class DeleteBatchResponse(BaseModel):
    """批量删除响应"""
    deletedCount: int
    requestedCount: int