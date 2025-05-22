from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from typing import Dict, Any

from config.database import Base


class StockResult(Base):
    """
    股票相似性计算结果表模型
    """
    __tablename__ = 'stock_result'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 关联历史记录
    # 在StockResult类中修改
    history_id = Column(Integer,
                        nullable=False, index=True, comment='历史记录ID')

    # 相似股票信息
    stock_code = Column(String(20), nullable=False, index=True, comment='相似股票代码')
    stock_name = Column(String(50), nullable=False, comment='相似股票名称')

    # 相似度指标
    similarity = Column(Float, nullable=False, comment='相似度分数')

    # 时间信息



    def to_dict(self) -> Dict[str, Any]:
        """
        将模型转换为字典

        Returns:
            Dict[str, Any]: 包含所有字段的字典
        """
        return {
            'id': self.id,
            'history_id': self.history_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'similarity': self.similarity,
        }

    def __repr__(self):
        return f"<StockResult(id={self.id}, stock_code={self.stock_code}, similarity={self.similarity})>"