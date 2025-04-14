from typing import List, Optional
from pydantic import BaseModel
from datetime import date


# 请求模型
class StockSimilarityRequest(BaseModel):
    stockCode: str  # 股票代码
    startDate: str  # 开始日期
    endDate: str  # 结束日期
    sectionLevel: int #选择的行业细分
    indicators: List[str]  # 选择的指标
    similarityMethod: str  # 相似性计算方法
    useLLM: bool  # 是否使用大语言模型分析
    similarCount: int  # 返回相似股票的数量

    class Config:
        json_schema_extra = {
            "example": {
                "stockCode": "000001",
                "startDate": "2023-01-01",
                "endDate": "2023-06-30",
                "sectionLevel": 1,
                "indicators": ["close", "high", "low", "turnover"],
                "similarityMethod": "dtw",
                "useLLM": True,
                "similarCount": 5
            }
        }


# 响应模型
class StockBasic(BaseModel):
    code: str
    name: str


class SimilarStock(StockBasic):
    similarity: float


class StockPerformanceData(BaseModel):
    code: str
    name: str
    data: List[float]


class PerformanceData(BaseModel):
    dates: List[str]
    stocks: List[StockPerformanceData]


class StockSimilarityResponse(BaseModel):
    similarStocks: List[SimilarStock]
    performanceData: PerformanceData
    llmAnalysis: Optional[str] = None


# 股票基本信息响应
class StockInfoResponse(BaseModel):
    code: str
    name: str
    industry: str
    description: Optional[str] = None


# 股票历史数据点
class StockHistoryPoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float


# 股票历史数据响应
class StockHistoryResponse(BaseModel):
    code: str
    name: str
    data: List[StockHistoryPoint]


# 支持的方法和指标
class SimilarityMethod(BaseModel):
    id: str
    name: str
    description: str


class Indicator(BaseModel):
    id: str
    name: str
    description: str
