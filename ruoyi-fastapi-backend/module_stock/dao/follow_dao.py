# dao/follow_dao.py
import asyncio
from datetime import datetime

import clickhouse_connect
from sqlalchemy import select, and_, delete, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import logging
import pandas as pd

from config.env import ClickHouseConfig
from entity.do.watchlist_do import StockWatchlist
from utils import ck_util
from utils.data_util import convert_result_to_dataframe

logger = logging.getLogger(__name__)


class FollowDAO:
    """
    股票关注数据访问对象，负责处理与股票关注相关的数据库操作
    """

    # ClickHouse查询中常用的列
    STOCK_COLUMNS = ['code', 'open', 'close', 'high', 'low', 'ycp', 'vol', 'timestamps']

    @classmethod
    async def search_stocks(cls, keyword: str) -> List[Dict[str, Any]]:
        """
        根据关键词搜索股票

        Args:
            keyword: 搜索关键词

        Returns:
            List[Dict[str, Any]]: 符合条件的股票列表
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._search_stocks_sync, keyword)
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            raise

    @classmethod
    def _search_stocks_sync(cls, keyword: str) -> List[Dict[str, Any]]:
        """
        同步方法根据关键词搜索股票

        Args:
            keyword: 搜索关键词

        Returns:
            List[Dict[str, Any]]: 符合条件的股票列表
        """
        try:
            query = f"""
               WITH latest_dates AS (
                   SELECT 
                       code,
                       MAX(timestamps) as latest_date
                   FROM ods_stock.ll_stock_daily_sharing
                   GROUP BY code
               )
               SELECT 
                   s.code, 
                   i.SecuName as name, 
                   s.close as price, 
                   (s.close - s.ycp) / s.ycp * 100 as change 
               FROM ods_stock.ll_stock_daily_sharing s
               JOIN events_temp.lc_csiinduspe i ON s.code = i.SecuCode
               JOIN latest_dates ld ON s.code = ld.code AND s.timestamps = ld.latest_date
               WHERE (s.code LIKE '%{keyword}%' OR i.SecuName LIKE '%{keyword}%') and s.category = 'stock'
               ORDER BY 
                   CASE 
                       WHEN s.code = '{keyword}' THEN 0
                       WHEN s.code LIKE '{keyword}%' THEN 1
                       WHEN s.code LIKE '%{keyword}%' THEN 2
                       WHEN i.SecuName = '{keyword}' THEN 3
                       WHEN i.SecuName LIKE '{keyword}%' THEN 4
                       WHEN i.SecuName LIKE '%{keyword}%' THEN 5
                       ELSE 6
                   END
               LIMIT 10
               """

            result = ck_util.query(query)
            stocks = []
            for row in result.result_rows:
                stocks.append({
                    "code": row[0],
                    "name": row[1],
                    "price": row[2],
                    "change": row[3]
                })

            return stocks
        except Exception as e:
            logger.error(f"执行搜索股票查询出错: {e}")
            raise





    @classmethod
    async def get_stock_history(cls, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        异步查询指定股票的历史数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD

        Returns:
            pd.DataFrame: 包含股票历史数据的DataFrame
        """
        try:
            query = f"""
            SELECT 
                code,
                open,
                close,
                high,
                low,
                ycp,
                vol,
                timestamps
            FROM ods_stock.ll_stock_daily_sharing
            WHERE code = '{stock_code}'
                AND timestamps >= toDate('{start_date}')
                AND timestamps <= toDate('{end_date}')
            ORDER BY timestamps
            """

            result = ck_util.query(query)
            return convert_result_to_dataframe(result, cls.STOCK_COLUMNS)
        except Exception as e:
            logger.error(f"获取股票历史数据出错，股票代码: {stock_code}, 错误: {e}")
            raise

    @classmethod
    async def get_user_watchlist(cls, db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户关注的股票列表，结合MySQL和ClickHouse数据

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            List[Dict[str, Any]]: 用户关注的股票列表
        """
        try:
            # 先从MySQL获取用户关注的股票代码
            result = await db.execute(
                select(StockWatchlist.stock_code, StockWatchlist.add_time)
                .where(StockWatchlist.user_id == user_id)
                .order_by(StockWatchlist.add_time.desc())
            )
            records = result.all()

            # 创建股票代码到添加时间的映射字典
            stock_code_to_add_time = {row[0]: row[1] for row in records}
            stock_codes = list(stock_code_to_add_time.keys())

            if not stock_codes:
                return []

            # 然后从ClickHouse获取这些股票的详细数据，传递映射字典
            return await cls._get_stocks_detail_from_clickhouse(stock_codes, stock_code_to_add_time)
        except Exception as e:
            logger.error(f"获取用户关注列表失败，用户ID: {user_id}, 错误: {e}")
            raise

    @classmethod
    async def _get_stocks_detail_from_clickhouse(cls, stock_codes: List[str],
                                                 stock_code_to_add_time: Dict[str, datetime]) -> List[Dict[str, Any]]:
        """
        从ClickHouse获取多个股票的详细信息

        Args:
            stock_codes: 股票代码列表
            stock_code_to_add_time: 股票代码到添加时间的映射
        """
        try:
            if not stock_codes:
                return []

            # 将股票代码列表转为SQL IN子句格式
            codes_str = "', '".join(stock_codes)

            query = f"""
            WITH latest_dates AS (
                SELECT 
                    code,
                    MAX(timestamps) as latest_date
                FROM ods_stock.ll_stock_daily_sharing
                WHERE code IN ('{codes_str}')
                GROUP BY code
            )
            SELECT 
                s.code, 
                i.SecuName as name, 
                s.close as price, 
                (s.close - s.ycp) / s.ycp * 100 as change,
                s.open,
                s.high,
                s.low,
                s.vol as volume,
                s.timestamps as update_time
            FROM ods_stock.ll_stock_daily_sharing s
            JOIN events_temp.lc_csiinduspe i ON s.code = i.SecuCode
            JOIN latest_dates ld ON s.code = ld.code AND s.timestamps = ld.latest_date
            WHERE s.code IN ('{codes_str}') AND s.category = 'stock'
            ORDER BY 
                -- 保持与输入顺序一致
                CASE 
                    {" ".join([f"WHEN s.code = '{code}' THEN {i}" for i, code in enumerate(stock_codes)])}
                    ELSE {len(stock_codes)}
                END
            """

            result = ck_util.query(query)

            stocks = []
            for row in result.result_rows:
                stock_code = row[0]
                # 从映射中获取对应的添加时间
                add_time = stock_code_to_add_time.get(stock_code)

                stocks.append({
                    "code": stock_code,
                    "name": row[1],
                    "price": row[2],
                    "change_rate": row[3],
                    "open": row[4],
                    "high": row[5],
                    "low": row[6],
                    "volume": row[7],
                    "add_time": add_time,  # 使用对应的单个时间值
                })

            return stocks
        except Exception as e:
            logger.error(f"从ClickHouse获取股票详情查询出错: {e}")
            raise

    @classmethod
    async def add_to_watchlist(cls, db: AsyncSession, user_id: str, stock_code: str) -> bool:
        """
        将股票添加到用户关注列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            stock_code: 股票代码

        Returns:
            bool: 添加成功返回True
        """
        try:
            # 先检查股票是否存在于ClickHouse
            stock_exists = await cls._check_stock_exists(stock_code)
            if not stock_exists:
                logger.warning(f"股票代码 {stock_code} 不存在")
                return False

            # 检查是否已经存在
            result = await db.execute(
                select(func.count())
                .select_from(StockWatchlist)
                .where(
                    and_(
                        StockWatchlist.user_id == user_id,
                        StockWatchlist.stock_code == stock_code
                    )
                )
            )
            count = result.scalar_one()

            if count > 0:
                logger.info(f"股票 {stock_code} 已在用户 {user_id} 的关注列表中")
                return False

            # 添加新记录
            new_watchlist = StockWatchlist(
                user_id=user_id,
                stock_code=stock_code
            )
            db.add(new_watchlist)
            await db.commit()

            logger.info(f"股票 {stock_code} 已成功添加到用户 {user_id} 的关注列表")
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"添加股票到关注列表失败: {e}")
            raise

    @classmethod
    async def _check_stock_exists(cls, stock_code: str) -> bool:
        """
        检查股票代码是否存在于ClickHouse
        """
        try:
            query = f"""
            SELECT 1 FROM ods_stock.ll_stock_daily_sharing
            WHERE code = '{stock_code}' and category = 'stock'
            LIMIT 1
            """

            # 创建一个新的临时连接而不是使用全局连接
            temp_client = clickhouse_connect.get_client(
                host=ClickHouseConfig.ck_host,
                port=ClickHouseConfig.ck_port,
                username=ClickHouseConfig.ck_username,
                password=ClickHouseConfig.ck_password
            )

            try:
                result = temp_client.query(query)
                return len(result.result_rows) > 0
            finally:
                temp_client.close()  # 确保关闭连接

        except Exception as e:
            logger.error(f"检查股票是否存在出错: {e}")
            raise

    @classmethod
    async def remove_from_watchlist(cls, db: AsyncSession, user_id: str, stock_code: str) -> bool:
        """
        从用户关注列表中移除股票

        Args:
            db: 数据库会话
            user_id: 用户ID
            stock_code: 股票代码

        Returns:
            bool: 操作成功返回True
        """
        try:
            # 查询要删除的记录
            result = await db.execute(
                delete(StockWatchlist)
                .where(
                    and_(
                        StockWatchlist.user_id == user_id,
                        StockWatchlist.stock_code == stock_code
                    )
                )
            )

            await db.commit()

            affected_rows = result.rowcount
            logger.info(f"股票 {stock_code} 已从用户 {user_id} 的关注列表中移除")

            return affected_rows > 0
        except Exception as e:
            await db.rollback()
            logger.error(f"从关注列表移除股票失败: {e}")
            raise

    @classmethod
    async def clear_watchlist(cls, db: AsyncSession, user_id: str) -> bool:
        """
        清空用户关注列表

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            bool: 操作成功返回True
        """
        try:
            result = await db.execute(
                delete(StockWatchlist)
                .where(StockWatchlist.user_id == user_id)
            )

            await db.commit()

            affected_rows = result.rowcount
            logger.info(f"用户 {user_id} 的关注列表已清空，移除了 {affected_rows} 条记录")

            return affected_rows > 0
        except Exception as e:
            await db.rollback()
            logger.error(f"清空关注列表失败: {e}")
            raise