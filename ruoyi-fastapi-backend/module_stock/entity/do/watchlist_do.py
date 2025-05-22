from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, func
from config.database import Base


class StockWatchlist(Base):
    """股票关注表实体模型"""
    __tablename__ = "stock_watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, comment="用户ID")
    stock_code = Column(String(20), nullable=False, comment="股票代码")
    add_time = Column(DateTime, nullable=False, default=func.now(), comment="添加时间")

    __table_args__ = (
        UniqueConstraint('user_id', 'stock_code', name='uniq_user_stock'),
    )