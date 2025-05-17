from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any

Base = declarative_base()


class StockResult(Base):
    """
    股票相似性计算结果表模型
    """
    __tablename__ = 'stock_result'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 关联历史记录
    history_id = Column(Integer, ForeignKey('stock_similarity_history.id'), nullable=False, index=True,
                        comment='历史记录ID')

    # 相似股票信息
    stock_code = Column(String(20), nullable=False, index=True, comment='相似股票代码')
    stock_name = Column(String(50), nullable=False, comment='相似股票名称')

    # 相似度指标
    similarity = Column(Float, nullable=False, comment='相似度分数')
    return_rate = Column(Float, default=0.0, comment='收益率对比')

    # 时间信息
    create_time = Column(DateTime, default=datetime.now, nullable=False, comment='创建时间')



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
            'return_rate': self.return_rate,
            'create_time': self.create_time.isoformat() if self.create_time else None
        }

    def __repr__(self):
        return f"<StockResult(id={self.id}, stock_code={self.stock_code}, similarity={self.similarity})>"