from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from datetime import datetime
from typing import Dict, Any

from config.database import Base


class StockHistory(Base):
    """
    股票相似性查询历史记录表模型
    """
    __tablename__ = 'stock_history'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 股票信息
    stock_code = Column(String(20), nullable=False, index=True, comment='股票代码')
    stock_name = Column(String(50), nullable=False, comment='股票名称')

    # 查询参数
    start_date = Column(String(10), nullable=False, comment='开始日期')
    end_date = Column(String(10), nullable=False, comment='结束日期')
    indicators = Column(JSON, nullable=False, comment='选择的指标列表')
    method = Column(String(50), nullable=False, comment='计算方法')
    compare_scope = Column(String(50), nullable=False, comment='对比范围')
    similar_count = Column(Integer, nullable=False, default=10, comment='相似个数')

    # 查询元数据
    query_time = Column(DateTime, default=datetime.now, nullable=False, index=True, comment='查询时间')
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')

    # 其他信息
    remark = Column(Text, comment='备注')
    status = Column(Integer, default=1, comment='状态：1-正常，0-已删除')

    def to_dict(self) -> Dict[str, Any]:
        """
        将模型转换为字典

        Returns:
            Dict[str, Any]: 包含所有字段的字典
        """
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'indicators': self.indicators,
            'method': self.method,
            'compare_scope': self.compare_scope,
            'similar_count': self.similar_count,
            'query_time': self.query_time.isoformat() if self.query_time else None,
            'user_id': self.user_id,
            'remark': self.remark,
            'status': self.status
        }

    def __repr__(self):
        return f"<StockHistory(id={self.id}, stock_code={self.stock_code}, query_time={self.query_time})>"