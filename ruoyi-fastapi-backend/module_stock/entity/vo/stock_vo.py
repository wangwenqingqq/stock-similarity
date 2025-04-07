from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from module_admin.annotation.pydantic_annotation import as_query


class StockModel(BaseModel):
    """
    股票信息模型
    """
    code: Optional[str] = Field(default=None, description='股票代码')
    open: Optional[float] = Field(default=None, description='开盘价')
    close: Optional[float] = Field(default=None, description='收盘价')
    high: Optional[float] = Field(default=None, description='最高价')
    low: Optional[float] = Field(default=None, description='最低价')
    ycp: Optional[float] = Field(default=None, description='昨日收盘价')
    vol: Optional[int] = Field(default=None, description='成交量')
    timestamps: Optional[datetime] = Field(default=None, description='时间戳')
    create_by: Optional[str] = Field(default=None, description='创建者')
    create_time: Optional[datetime] = Field(default=None, description='创建时间')
    update_by: Optional[str] = Field(default=None, description='更新者')
    update_time: Optional[datetime] = Field(default=None, description='更新时间')
class StockQueryModel(BaseModel):
    """
    股票信息不分页查询模型
    """
    begin_time: Optional[str] = Field(default=None, description='开始时间')
    end_time: Optional[str] = Field(default=None, description='结束时间')

@as_query
class StockPageQueryModel(BaseModel):
    """
    股票信息分页查询模型
    """
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')

class DeleteStockModel(BaseModel):
    """
    删除股票信息模型
    """
    stockIds: str