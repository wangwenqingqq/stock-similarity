from typing import List, Optional, Dict, Any, Tuple
import asyncio
import pandas as pd
import logging
from datetime import datetime

from utils import ck_util
from utils.data_util import convert_result_to_dataframe

# 配置日志记录器
logger = logging.getLogger(__name__)


class FollowDAO:
    """
    股票关注数据访问对象，负责处理与股票关注相关的数据库操作
    """

    # ClickHouse查询中常用的列
    STOCK_COLUMNS = ['code', 'open', 'close', 'high', 'low', 'ycp', 'vol', 'timestamps']

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
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_stock_history_sync, stock_code, start_date, end_date)
        except Exception as e:
            logger.error(f"获取股票历史数据出错，股票代码: {stock_code}, 错误: {e}")
            raise

    @classmethod
    def _get_stock_history_sync(cls, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        同步方法查询指定股票的历史数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD

        Returns:
            pd.DataFrame: 包含股票历史数据的DataFrame
        """
        try:
            if not stock_code:
                logger.warning("股票代码为空")
                return pd.DataFrame(columns=cls.STOCK_COLUMNS)

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
            logger.error(f"执行股票历史数据查询出错: {e}")
            raise

    @classmethod
    async def get_stock_list(
            cls,
            page: int = 1,
            size: int = 10,
            keyword: Optional[str] = None,
            status: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        获取股票列表信息

        Args:
            page: 页码，默认为1
            size: 每页数量，默认为10
            keyword: 搜索关键词，可选
            status: 股票状态，可选

        Returns:
            Tuple[List[Dict[str, Any]], int]: 股票列表和总数
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_stock_list_sync, page, size, keyword, status)
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise

    @classmethod
    def _get_stock_list_sync(
            cls,
            page: int = 1,
            size: int = 10,
            keyword: Optional[str] = None,
            status: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        同步方法获取股票列表信息

        Args:
            page: 页码，默认为1
            size: 每页数量，默认为10
            keyword: 搜索关键词，可选
            status: 股票状态，可选

        Returns:
            Tuple[List[Dict[str, Any]], int]: 股票列表和总数
        """
        try:
            # 构建查询条件
            conditions = []
            if keyword:
                conditions.append(f"(s.code LIKE '%{keyword}%' OR i.SecuName LIKE '%{keyword}%')")
            if status:
                conditions.append(f"s.status = '{status}'")

            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

            # 查询总数
            count_query = f"""
            SELECT COUNT(*) as total 
            FROM ods_stock.ll_stock_daily_sharing s
            JOIN events_temp.lc_csiinduspe i ON s.code = i.SecuCode
            {where_clause}
            """
            count_result = ck_util.query(count_query)
            total = count_result.result_rows[0][0] if count_result.result_rows else 0

            # 查询数据列表
            offset = (page - 1) * size
            query = f"""
            SELECT 
                s.code, 
                i.SecuName as name, 
                s.close as price, 
                (s.close - s.ycp) / s.ycp * 100 as change 
            FROM ods_stock.ll_stock_daily_sharing s
            JOIN events_temp.lc_csiinduspe i ON s.code = i.SecuCode
            {where_clause}
            ORDER BY s.code
            LIMIT {size} OFFSET {offset}
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

            return stocks, total
        except Exception as e:
            logger.error(f"执行获取股票列表查询出错: {e}")
            raise

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
            WHERE (s.code LIKE '%{keyword}%' OR i.SecuName LIKE '%{keyword}%')
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
    async def get_stock_detail(cls, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票详细信息

        Args:
            code: 股票代码

        Returns:
            Optional[Dict[str, Any]]: 股票详细信息，如果不存在则返回None
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_stock_detail_sync, code)
        except Exception as e:
            logger.error(f"获取股票详情失败，股票代码: {code}, 错误: {e}")
            raise

    @classmethod
    def _get_stock_detail_sync(cls, code: str) -> Optional[Dict[str, Any]]:
        """
        同步方法获取股票详细信息

        Args:
            code: 股票代码

        Returns:
            Optional[Dict[str, Any]]: 股票详细信息，如果不存在则返回None
        """
        try:
            query = f"""
            SELECT 
                s.code, 
                i.SecuName as name, 
                s.close as price, 
                (s.close - s.ycp) / s.ycp * 100 as change,
                s.open,
                s.close,
                s.high,
                s.low,
                s.vol as volume,
                s.timestamps as update_time
            FROM ods_stock.ll_stock_daily_sharing s
            JOIN events_temp.lc_csiinduspe i ON s.code = i.SecuCode
            WHERE s.code = '{code}'
            ORDER BY s.timestamps DESC
            LIMIT 1
            """

            result = ck_util.query(query)
            if not result.result_rows:
                return None

            row = result.result_rows[0]
            return {
                "code": row[0],
                "name": row[1],
                "price": row[2],
                "change": row[3],
                "open": row[4],
                "close": row[5],
                "high": row[6],
                "low": row[7],
                "volume": row[8],
                "update_time": row[9]
            }
        except Exception as e:
            logger.error(f"执行获取股票详情查询出错: {e}")
            raise

    @classmethod
    async def get_user_watchlist(cls, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户关注的股票列表

        Args:
            user_id: 用户ID

        Returns:
            List[Dict[str, Any]]: 用户关注的股票列表
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_user_watchlist_sync, user_id)
        except Exception as e:
            logger.error(f"获取用户关注列表失败，用户ID: {user_id}, 错误: {e}")
            raise

    @classmethod
    def _get_user_watchlist_sync(cls, user_id: str) -> List[Dict[str, Any]]:
        """
        同步方法获取用户关注的股票列表

        Args:
            user_id: 用户ID

        Returns:
            List[Dict[str, Any]]: 用户关注的股票列表
        """
        try:
            query = f"""
            SELECT 
                s.code, 
                i.SecuName as name, 
                s.close as price, 
                (s.close - s.ycp) / s.ycp * 100 as change
            FROM watchlist w
            JOIN ods_stock.ll_stock_daily_sharing s ON w.stock_code = s.code
            JOIN events_temp.lc_csiinduspe i ON s.code = i.SecuCode
            WHERE w.user_id = '{user_id}'
            ORDER BY w.add_time DESC
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
            logger.error(f"执行获取用户关注列表查询出错: {e}")
            raise

    @classmethod
    async def add_to_watchlist(cls, user_id: str, stock_code: str) -> bool:
        """
        将股票添加到用户关注列表

        Args:
            user_id: 用户ID
            stock_code: 股票代码

        Returns:
            bool: 添加成功返回True，股票已存在返回False
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._add_to_watchlist_sync, user_id, stock_code)
        except Exception as e:
            logger.error(f"添加股票到关注列表失败，用户ID: {user_id}, 股票代码: {stock_code}, 错误: {e}")
            raise

    @classmethod
    def _add_to_watchlist_sync(cls, user_id: str, stock_code: str) -> bool:
        """
        同步方法将股票添加到用户关注列表

        Args:
            user_id: 用户ID
            stock_code: 股票代码

        Returns:
            bool: 添加成功返回True，股票已存在返回False
        """
        try:
            # 先检查是否已经存在
            check_query = f"""
            SELECT 1 FROM watchlist 
            WHERE user_id = '{user_id}' AND stock_code = '{stock_code}'
            LIMIT 1
            """
            check_result = ck_util.query(check_query)
            if check_result.result_rows:
                logger.info(f"股票 {stock_code} 已在用户 {user_id} 的关注列表中")
                return False

            # 不存在则添加
            insert_query = f"""
            INSERT INTO watchlist (user_id, stock_code, add_time)
            VALUES ('{user_id}', '{stock_code}', now())
            """
            ck_util.query(insert_query)
            logger.info(f"股票 {stock_code} 已成功添加到用户 {user_id} 的关注列表")
            return True
        except Exception as e:
            logger.error(f"执行添加股票到关注列表查询出错: {e}")
            raise

    @classmethod
    async def remove_from_watchlist(cls, user_id: str, stock_code: str) -> bool:
        """
        从用户关注列表中移除股票

        Args:
            user_id: 用户ID
            stock_code: 股票代码

        Returns:
            bool: 操作成功返回True
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._remove_from_watchlist_sync, user_id, stock_code)
        except Exception as e:
            logger.error(f"从关注列表移除股票失败，用户ID: {user_id}, 股票代码: {stock_code}, 错误: {e}")
            raise

    @classmethod
    def _remove_from_watchlist_sync(cls, user_id: str, stock_code: str) -> bool:
        """
        同步方法从用户关注列表中移除股票

        Args:
            user_id: 用户ID
            stock_code: 股票代码

        Returns:
            bool: 操作成功返回True
        """
        try:
            query = f"""
            ALTER TABLE watchlist
            DELETE WHERE user_id = '{user_id}' AND stock_code = '{stock_code}'
            """
            ck_util.query(query)
            logger.info(f"股票 {stock_code} 已从用户 {user_id} 的关注列表中移除")
            return True
        except Exception as e:
            logger.error(f"执行从关注列表移除股票查询出错: {e}")
            raise

    @classmethod
    async def clear_watchlist(cls, user_id: str) -> bool:
        """
        清空用户关注列表

        Args:
            user_id: 用户ID

        Returns:
            bool: 操作成功返回True
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._clear_watchlist_sync, user_id)
        except Exception as e:
            logger.error(f"清空关注列表失败，用户ID: {user_id}, 错误: {e}")
            raise

    @classmethod
    def _clear_watchlist_sync(cls, user_id: str) -> bool:
        """
        同步方法清空用户关注列表

        Args:
            user_id: 用户ID

        Returns:
            bool: 操作成功返回True
        """
        try:
            query = f"""
            ALTER TABLE watchlist
            DELETE WHERE user_id = '{user_id}'
            """
            ck_util.query(query)
            logger.info(f"用户 {user_id} 的关注列表已清空")
            return True
        except Exception as e:
            logger.error(f"执行清空关注列表查询出错: {e}")
            raise