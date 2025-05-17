import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from entity.do.history_do import StockHistory

logger = logging.getLogger(__name__)


class HistoryDAO:
    """
    股票相似性查询历史数据访问对象，负责处理与查询历史相关的数据库操作
    """

    @classmethod
    async def fetch_history_list(
            cls,
            db: AsyncSession,
            page: int = 1,
            page_size: int = 10,
            stock_code: Optional[str] = None,
            stock_name: Optional[str] = None,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            sort_by: str = 'query_time',
            sort_order: str = 'desc'
    ) -> Dict[str, Any]:
        """
        获取查询历史列表

        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            stock_code: 股票代码
            stock_name: 股票名称
            start_date: 开始日期
            end_date: 结束日期
            sort_by: 排序字段
            sort_order: 排序方式

        Returns:
            Dict: 包含总数和列表的字典
        """
        try:
            # 构建查询条件
            query = select(StockHistory)

            # 添加筛选条件
            filters = []
            if stock_code:
                filters.append(StockHistory.stock_code.like(f"%{stock_code}%"))
            if stock_name:
                filters.append(StockHistory.stock_name.like(f"%{stock_name}%"))
            if start_date:
                filters.append(StockHistory.query_time >= start_date)
            if end_date:
                filters.append(StockHistory.query_time <= end_date)

            if filters:
                query = query.where(and_(*filters))

            # 添加排序
            sort_column = getattr(StockHistory, sort_by, StockHistory.query_time)
            if sort_order == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            # 获取总数
            count_query = select(func.count()).select_from(query.subquery())
            total = await db.scalar(count_query)

            # 分页查询
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            result = await db.execute(query)
            histories = result.scalars().all()

            return {
                'total': total,
                'items': [history.to_dict() for history in histories]
            }
        except Exception as e:
            logger.error(f"获取查询历史列表失败: {e}")
            raise

    @classmethod
    async def create_history(
            cls,
            db: AsyncSession,
            stock_code: str,
            stock_name: str,
            start_date: str,
            end_date: str,
            indicators: List[str],
            method: str,
            compare_scope: str,
            similar_count: int = 10,
            user_id: str = None,
            remark: Optional[str] = None,
            status:int = 1,
    ) -> int:
        """
        创建新的查询历史记录

        Args:
            db: 数据库会话
            stock_code: 股票代码
            stock_name: 股票名称
            start_date: 开始日期
            end_date: 结束日期
            indicators: 选择的指标列表
            method: 计算方法
            compare_scope: 对比范围
            similar_count: 相似个数
            user_id: 用户ID
            remark: 备注
            status: 状态
        Returns:
            int: 新创建的历史记录ID
        """
        try:
            # 创建新的历史记录对象
            new_history = StockHistory(
                stock_code=stock_code,
                stock_name=stock_name,
                start_date=start_date,
                end_date=end_date,
                indicators=indicators,
                method=method,
                compare_scope=compare_scope,
                similar_count=similar_count,
                user_id=user_id or "system",  # 默认用户ID
                remark=remark,
                query_time=datetime.now(),
                status=1
            )

            # 添加到数据库并提交
            db.add(new_history)
            await db.commit()

            # 刷新实例以获取数据库生成的值（如自增ID）
            await db.refresh(new_history)

            logger.info(f"创建查询历史记录成功，ID: {new_history.id}, 股票代码: {stock_code}")
            return new_history.id
        except Exception as e:
            await db.rollback()
            logger.error(f"创建查询历史记录失败: {e}")
            raise

    @classmethod
    async def get_history_by_id(cls, db: AsyncSession, history_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取历史记录

        Args:
            db: 数据库会话
            history_id: 历史记录ID

        Returns:
            Optional[Dict]: 历史记录字典或None
        """
        try:
            query = select(StockHistory).where(
                StockHistory.id == history_id
            )

            result = await db.execute(query)
            history = result.scalar_one_or_none()

            return history.to_dict() if history else None
        except Exception as e:
            logger.error(f"获取历史记录失败，ID: {history_id}, 错误: {e}")
            raise

    @classmethod
    async def delete_history(cls, db: AsyncSession, history_id: int) -> bool:
        """
        删除历史记录

        Args:
            db: 数据库会话
            history_id: 历史记录ID

        Returns:
            bool: 是否成功
        """
        try:
            result = await db.execute(
                delete(StockHistory).where(
                    StockHistory.id == history_id
                )
            )
            await db.commit()

            affected_rows = result.rowcount
            logger.info(f"删除历史记录成功，ID: {history_id}")

            return affected_rows > 0
        except Exception as e:
            await db.rollback()
            logger.error(f"删除历史记录失败，ID: {history_id}, 错误: {e}")
            raise

    @classmethod
    async def delete_history_batch(cls, db: AsyncSession, history_ids: List[int]) -> int:
        """
        批量删除历史记录

        Args:
            db: 数据库会话
            history_ids: 历史记录ID列表

        Returns:
            int: 删除的记录数
        """
        try:
            result = await db.execute(
                delete(StockHistory).where(
                    StockHistory.id.in_(history_ids)
                )
            )
            await db.commit()

            affected_rows = result.rowcount
            logger.info(f"批量删除历史记录成功，删除了 {affected_rows} 条记录")

            return affected_rows
        except Exception as e:
            await db.rollback()
            logger.error(f"批量删除历史记录失败: {e}")
            raise

    @classmethod
    async def search_history(cls, db: AsyncSession, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索历史记录

        Args:
            db: 数据库会话
            keyword: 搜索关键词

        Returns:
            List[Dict]: 历史记录列表
        """
        try:
            query = select(StockHistory).where(
                or_(
                    StockHistory.stock_code.like(f"%{keyword}%"),
                    StockHistory.stock_name.like(f"%{keyword}%")
                )
            ).order_by(StockHistory.query_time.desc())

            result = await db.execute(query)
            histories = result.scalars().all()

            return [history.to_dict() for history in histories]
        except Exception as e:
            logger.error(f"搜索历史记录失败，关键词: {keyword}, 错误: {e}")
            raise

    @classmethod
    async def get_history_statistics(
            cls,
            db: AsyncSession,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取历史统计信息

        Args:
            db: 数据库会话
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict: 统计信息
        """
        try:
            # 基础查询
            query = select(StockHistory)

            # 日期筛选
            filters = []
            if start_date:
                filters.append(StockHistory.query_time >= start_date)
            if end_date:
                filters.append(StockHistory.query_time <= end_date)

            if filters:
                query = query.where(and_(*filters))

            # 获取总数
            count_query = select(func.count()).select_from(query.subquery())
            total_count = await db.scalar(count_query)

            # 获取方法分布
            method_query = select(
                StockHistory.method,
                func.count().label('count')
            ).group_by(StockHistory.method)

            if filters:
                method_query = method_query.where(and_(*filters))

            method_result = await db.execute(method_query)
            method_distribution = {row[0]: row[1] for row in method_result}

            # 获取每日统计
            daily_query = select(
                func.date(StockHistory.query_time).label('date'),
                func.count().label('count')
            ).group_by(func.date(StockHistory.query_time))

            if filters:
                daily_query = daily_query.where(and_(*filters))

            daily_result = await db.execute(daily_query)
            daily_counts = [{'date': str(row[0]), 'count': row[1]} for row in daily_result]

            return {
                'total_count': total_count,
                'method_distribution': method_distribution,
                'daily_counts': daily_counts
            }
        except Exception as e:
            logger.error(f"获取历史统计信息失败: {e}")
            raise

    @classmethod
    async def get_hot_stocks(
            cls,
            db: AsyncSession,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取热门股票

        Args:
            db: 数据库会话
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制数量

        Returns:
            List[Dict]: 热门股票列表
        """
        try:
            query = select(
                StockHistory.stock_code,
                StockHistory.stock_name,
                func.count().label('query_count')
            ).group_by(
                StockHistory.stock_code,
                StockHistory.stock_name
            ).order_by(func.count().desc()).limit(limit)

            # 日期筛选
            filters = []
            if start_date:
                filters.append(StockHistory.query_time >= start_date)
            if end_date:
                filters.append(StockHistory.query_time <= end_date)

            if filters:
                query = query.where(and_(*filters))

            result = await db.execute(query)

            return [{
                'stock_code': row[0],
                'stock_name': row[1],
                'query_count': row[2]
            } for row in result]
        except Exception as e:
            logger.error(f"获取热门股票失败: {e}")
            raise

    @classmethod
    async def get_recent_history(cls, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的历史记录

        Args:
            db: 数据库会话
            limit: 限制数量

        Returns:
            List[Dict]: 历史记录列表
        """
        try:
            query = select(StockHistory).order_by(
                StockHistory.query_time.desc()
            ).limit(limit)

            result = await db.execute(query)
            histories = result.scalars().all()

            return [history.to_dict() for history in histories]
        except Exception as e:
            logger.error(f"获取最近历史记录失败: {e}")
            raise

    @classmethod
    async def delete_all(cls, db: AsyncSession) -> int:
        """
        删除所有记录

        Args:
            db: 数据库会话

        Returns:
            int: 删除的记录数
        """
        try:
            result = await db.execute(delete(StockHistory))
            await db.commit()

            affected_rows = result.rowcount
            logger.info(f"删除所有历史记录成功，共删除 {affected_rows} 条记录")

            return affected_rows
        except Exception as e:
            await db.rollback()
            logger.error(f"删除所有记录失败: {e}")
            raise