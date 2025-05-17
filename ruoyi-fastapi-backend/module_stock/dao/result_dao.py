import logging
from typing import List, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from entity.do.result_do import StockResult

logger = logging.getLogger(__name__)


class ResultDAO:
    """
    股票相似性结果数据访问对象，负责处理与相似股票结果相关的数据库操作
    """

    @classmethod
    async def get_results_by_history_id(cls, db: AsyncSession, history_id: int) -> List[Dict[str, Any]]:
        """
        根据历史记录ID获取相似股票结果

        Args:
            db: 数据库会话
            history_id: 历史记录ID

        Returns:
            List[Dict]: 相似股票结果列表
        """
        try:
            query = select(StockResult).where(
                StockResult.history_id == history_id
            ).order_by(StockResult.similarity.desc())

            result = await db.execute(query)
            results = result.scalars().all()

            return [result.to_dict() for result in results]
        except Exception as e:
            logger.error(f"获取相似股票结果失败，历史ID: {history_id}, 错误: {e}")
            raise

    @classmethod
    async def delete_by_history_id(cls, db: AsyncSession, history_id: int) -> int:
        """
        根据历史记录ID删除结果

        Args:
            db: 数据库会话
            history_id: 历史记录ID

        Returns:
            int: 删除的记录数
        """
        try:
            result = await db.execute(
                delete(StockResult).where(
                    StockResult.history_id == history_id
                )
            )
            await db.commit()

            affected_rows = result.rowcount
            logger.info(f"删除相似股票结果成功，历史ID: {history_id}, 删除了 {affected_rows} 条记录")

            return affected_rows
        except Exception as e:
            await db.rollback()
            logger.error(f"删除相似股票结果失败，历史ID: {history_id}, 错误: {e}")
            raise

    @classmethod
    async def delete_by_history_ids(cls, db: AsyncSession, history_ids: List[int]) -> int:
        """
        根据多个历史记录ID删除结果

        Args:
            db: 数据库会话
            history_ids: 历史记录ID列表

        Returns:
            int: 删除的记录数
        """
        try:
            result = await db.execute(
                delete(StockResult).where(
                    StockResult.history_id.in_(history_ids)
                )
            )
            await db.commit()

            affected_rows = result.rowcount
            logger.info(f"批量删除相似股票结果成功，删除了 {affected_rows} 条记录")

            return affected_rows
        except Exception as e:
            await db.rollback()
            logger.error(f"批量删除相似股票结果失败: {e}")
            raise

    @classmethod
    async def delete_all(cls, db: AsyncSession) -> int:
        """
        删除所有结果记录

        Args:
            db: 数据库会话

        Returns:
            int: 删除的记录数
        """
        try:
            result = await db.execute(delete(StockResult))
            await db.commit()

            affected_rows = result.rowcount
            logger.info(f"删除所有结果记录成功，共删除 {affected_rows} 条记录")

            return affected_rows
        except Exception as e:
            await db.rollback()
            logger.error(f"删除所有结果记录失败: {e}")
            raise

    @classmethod
    async def save_results(cls, db: AsyncSession, history_id: int, results: List[Dict[str, Any]]) -> int:
        """
        保存相似股票结果

        Args:
            db: 数据库会话
            history_id: 历史记录ID
            results: 结果列表

        Returns:
            int: 保存的记录数
        """
        try:
            saved_count = 0
            for result_data in results:
                result = StockResult(
                    history_id=history_id,
                    stock_code=result_data['stock_code'],
                    stock_name=result_data['stock_name'],
                    similarity=result_data['similarity'],
                    return_rate=result_data.get('return_rate', 0),
                    volatility=result_data.get('volatility', 0),
                    sharpe_ratio=result_data.get('sharpe_ratio', 0),
                    max_drawdown=result_data.get('max_drawdown', 0)
                )
                db.add(result)
                saved_count += 1

            await db.commit()
            logger.info(f"保存相似股票结果成功，历史ID: {history_id}, 保存了 {saved_count} 条记录")

            return saved_count
        except Exception as e:
            await db.rollback()
            logger.error(f"保存相似股票结果失败，历史ID: {history_id}, 错误: {e}")
            raise

    @classmethod
    async def update_result(cls, db: AsyncSession, result_id: int, update_data: Dict[str, Any]) -> bool:
        """
        更新结果记录

        Args:
            db: 数据库会话
            result_id: 结果记录ID
            update_data: 更新数据

        Returns:
            bool: 是否成功
        """
        try:
            result = await db.get(StockResult, result_id)
            if not result:
                logger.warning(f"结果记录不存在，ID: {result_id}")
                return False

            for key, value in update_data.items():
                if hasattr(result, key):
                    setattr(result, key, value)

            await db.commit()
            logger.info(f"更新结果记录成功，ID: {result_id}")

            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"更新结果记录失败，ID: {result_id}, 错误: {e}")
            raise

    @classmethod
    async def batch_save_results(cls, db: AsyncSession, results_data: List[Dict[str, Any]]) -> int:
        """
        批量保存结果记录

        Args:
            db: 数据库会话
            results_data: 结果数据列表

        Returns:
            int: 保存的记录数
        """
        try:
            saved_count = 0
            for data in results_data:
                result = StockResult(**data)
                db.add(result)
                saved_count += 1

            await db.commit()
            logger.info(f"批量保存结果记录成功，保存了 {saved_count} 条记录")

            return saved_count
        except Exception as e:
            await db.rollback()
            logger.error(f"批量保存结果记录失败: {e}")
            raise