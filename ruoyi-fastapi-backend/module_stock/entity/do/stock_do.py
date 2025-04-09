
from sqlalchemy import Column, String, Float, DateTime
from config.database import Base

class StockInfo(Base):
    """
    股票信息实体类
    """
    __tablename__ = 'll_stock_daily_sharing'

    code = Column(String(20), primary_key=True, comment='股票代码')
    open = Column(Float, comment='开盘价')
    close = Column(Float, comment='收盘价')
    high = Column(Float, comment='最高价')
    low = Column(Float, comment='最低价')
    ycp = Column(Float, comment='昨日收盘价')
    vol = Column(Float, comment='成交量')
    timestamps = Column(DateTime, primary_key=True, comment='时间戳')