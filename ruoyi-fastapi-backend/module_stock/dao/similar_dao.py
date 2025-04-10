from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from fastdtw import fastdtw
from clickhouse_driver import Client
from module_stock.entity.vo.similar_vo import *
from config.env import ClickHouseSettings
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from utils import ck_util
from utils.data_util import convert_result_to_dataframe
from domain.extract_record_info import to_object_single

settings = ClickHouseSettings()
logger = logging.getLogger(__name__)


class SimilarDao:
    """股票数据访问对象，负责从数据源获取股票数据"""

    @classmethod
    async def get_all_stocks(cls) -> List[Dict[str, str]]:
        """获取所有可用的股票列表

        Returns:
            List[Dict[str, str]]: 股票列表，每个股票包含代码和名称
        """
        try:
            # 使用线程池执行同步数据库操作
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_all_stocks_sync)
        except Exception as e:
            logger.error(f"获取股票列表出错: {e}")
            return []

    @classmethod
    def _get_all_stocks_sync(cls) -> List[Dict[str, str]]:
        """同步方法获取所有股票列表"""
        try:
            # 使用参考文件中的 ck_util 进行查询
            query = """
            SELECT DISTINCT code, code as name 
            FROM ods_stock.ll_stock_daily_sharing 
            WHERE category = 'stock'
            GROUP BY code
            ORDER BY code
            """
            logger.info(f"执行查询: {query}")
            result = ck_util.query(query)

            stocks = []
            # 假设 result 是包含(code, name)元组的列表
            for row in result.result_rows:
                stocks.append({"code": row[0], "name": row[1]})

            logger.info(f"处理了 {len(stocks)} 条股票记录")
            return stocks
        except Exception as e:
            logger.error(f"获取股票列表出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    @classmethod
    async def get_stock_info(cls, stock_code: str) -> Dict[str, Any]:
        """获取单个股票的基本信息

        Args:
            stock_code: 股票代码

        Returns:
            Dict[str, Any]: 股票基本信息
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_stock_info_sync, stock_code)
        except Exception as e:
            logger.error(f"获取股票信息出错 {stock_code}: {e}")
            raise

    @classmethod
    def _get_stock_info_sync(cls, stock_code: str) -> Dict[str, Any]:
        """同步方法获取单个股票基本信息"""
        try:
            # 参考新提供的函数 get_stock_info
            query = f"""
            SELECT code as security_id, category as security_type, code as symbol
            FROM ods_stock.ll_stock_daily_sharing
            WHERE code = '{stock_code}'
            AND category = 'stock'
            LIMIT 1
            """

            logger.info(f"执行查询: {query}")
            result = ck_util.query(query)

            if not result.result_rows:
                logger.warning(f"未找到股票信息: {stock_code}")
                # 返回默认信息
                return {
                    "code": stock_code,
                    "name": stock_code,
                    "industry": "未知行业",
                    "description": "没有可用的描述信息"
                }

            row = result.result_rows[0]
            # 仅使用 ll_stock_daily_sharing 表中可获得的信息
            stock_info = {
                "code": row[0],
                "name": row[0],  # 使用代码作为名称
                "industry": "未知行业",  # 默认行业
                "description": "没有可用的描述信息"  # 默认描述
            }

            return stock_info
        except Exception as e:
            logger.error(f"获取股票信息出错 {stock_code}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    @classmethod
    async def get_stock_data(cls, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取股票历史数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 股票历史数据
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_stock_data_sync, stock_code, start_date, end_date)
        except Exception as e:
            logger.error(f"获取股票数据出错 {stock_code}: {e}")
            raise

    @classmethod
    def _get_stock_data_sync(cls, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """同步方法获取股票历史数据"""
        try:
            # 参考参考文件中的查询方式
            COLUMNS_TO_READ = ['code', 'open', 'close', 'high', 'low', 'ycp', 'vol', 'timestamps']

            query = f"""
            WITH
            -- 计算查询的开始日期和结束日期
            date_range AS (
                SELECT toDate('{start_date}') AS start_date,
                       toDate('{end_date}') AS end_date
            )
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
                AND category = 'stock'
                AND timestamps >= (SELECT start_date FROM date_range)
                AND timestamps <= (SELECT end_date FROM date_range)
            ORDER BY timestamps
            """

            logger.info(f"执行查询: {query}")
            result = ck_util.query(query)

            # 使用参考文件中的方法转换为DataFrame
            df = convert_result_to_dataframe(result, COLUMNS_TO_READ)

            if df.empty:
                logger.warning(f"未找到股票数据: {stock_code}")
                # 返回空的DataFrame
                return pd.DataFrame()

            # 设置日期为索引
            if 'timestamps' in df.columns:
                df.rename(columns={'timestamps': 'date'}, inplace=True)
                df.set_index('date', inplace=True)
            elif 'date' in df.columns:
                df.set_index('date', inplace=True)

            logger.info(f"成功获取股票数据: {stock_code}, 记录数: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"获取股票数据出错 {stock_code}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    @classmethod
    async def get_stock_data_before_event(cls, stock_code: str, ts_time: str, day_far: int,
                                          day_near: int) -> pd.DataFrame:
        """获取事件前的股票数据

        Args:
            stock_code: 股票代码
            ts_time: 事件时间
            day_far: 最远时间间隔天数
            day_near: 最近时间间隔天数

        Returns:
            pd.DataFrame: 股票历史数据
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_stock_data_before_event_sync, stock_code, ts_time, day_far,
                                              day_near)
        except Exception as e:
            logger.error(f"获取事件前股票数据出错 {stock_code}: {e}")
            raise

    @classmethod
    def _get_stock_data_before_event_sync(cls, stock_code: str, ts_time: str, day_far: int,
                                          day_near: int) -> pd.DataFrame:
        """同步方法获取事件前的股票数据"""
        COLUMNS_TO_READ = ['code', 'open', 'close', 'high', 'low', 'ycp', 'vol', 'timestamps']
        security_id = str(stock_code)

        query = f"""
        WITH
        -- 计算查询的开始日期和结束日期
        date_range AS (
              SELECT addDays(toDate('{ts_time}'), -{day_far}) AS start_date,
                   addDays(toDate('{ts_time}'), -{day_near}) AS end_date
        )
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
        WHERE code = '{security_id}'
            AND category = 'stock'
            AND timestamps > (SELECT start_date FROM date_range)
            AND timestamps <= (SELECT end_date FROM date_range)
        ORDER BY timestamps
        """

        result = ck_util.query(query)
        # 将查询结果转换为 Pandas DataFrame
        df = convert_result_to_dataframe(result, COLUMNS_TO_READ)

        # 设置日期为索引
        if 'timestamps' in df.columns:
            df.rename(columns={'timestamps': 'date'}, inplace=True)
            df.set_index('date', inplace=True)
        elif 'date' in df.columns:
            df.set_index('date', inplace=True)

        return df

    @classmethod
    async def get_section_stock_data(cls, section_code_list: List[str], ts_time: str, day_far: int,
                                     day_near: int) -> pd.DataFrame:
        """获取一组股票在特定时间段的数据

        Args:
            section_code_list: 股票代码列表
            ts_time: 事件时间
            day_far: 最远时间间隔天数
            day_near: 最近时间间隔天数

        Returns:
            pd.DataFrame: 股票历史数据
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_section_stock_data_sync, section_code_list, ts_time,
                                              day_far, day_near)
        except Exception as e:
            logger.error(f"获取一组股票数据出错: {e}")
            raise

    @classmethod
    def _get_section_stock_data_sync(cls, section_code_list: List[str], ts_time: str, day_far: int,
                                     day_near: int) -> pd.DataFrame:
        """同步方法获取一组股票在特定时间段的数据"""
        COLUMNS_TO_READ = ['code', 'open', 'close', 'high', 'low', 'ycp', 'vol', 'timestamps']

        query = f"""
         WITH
        -- 计算查询的开始日期和结束日期
        date_range AS (
            SELECT addDays(toDate('{ts_time}'), -{day_far}) AS start_date,
                   addDays(toDate('{ts_time}'), -{day_near}) AS end_date
        )
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
        WHERE code IN ({', '.join(f"'{code}'" for code in section_code_list)})
            AND category ='stock'
            AND timestamps >= (SELECT start_date FROM date_range)
            AND timestamps <= (SELECT end_date FROM date_range)
        ORDER BY code, timestamps
        """

        result = ck_util.query(query)
        # 将查询结果转换为 Pandas DataFrame
        df = convert_result_to_dataframe(result, COLUMNS_TO_READ)

        # 设置日期为索引
        if 'timestamps' in df.columns:
            df.rename(columns={'timestamps': 'date'}, inplace=True)
            df.set_index('date', inplace=True)
        elif 'date' in df.columns:
            df.set_index('date', inplace=True)

        return df

    @classmethod
    async def get_event_stock_data(cls, extract_record, before_days: int, after_days: int) -> pd.DataFrame:
        """获取事件前后的股票数据

        Args:
            extract_record: 包含股票事件信息的对象
            before_days: 事件前的天数
            after_days: 事件后的天数

        Returns:
            pd.DataFrame: 股票历史数据
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_event_stock_data_sync, extract_record, before_days,
                                              after_days)
        except Exception as e:
            logger.error(f"获取事件前后股票数据出错: {e}")
            raise

    @classmethod
    def _get_event_stock_data_sync(cls, extract_record, before_days: int, after_days: int) -> pd.DataFrame:
        """同步方法获取事件前后的股票数据"""
        COLUMNS_TO_READ = ['code', 'open', 'close', 'high', 'low', 'timestamps', 'period']
        ts_time = extract_record.TStime
        tr_time = extract_record.TStime  # 这里使用的是TStime，如果需要TRtime应该是extract_record.TRtime
        security_id = str(extract_record.securityId)

        query = f"""
        WITH
        -- 计算 TStime 的前 before_days+1 个日期范围的开始日期和结束日期
        start_date_before AS (
            SELECT addDays(toDate('{ts_time}'), -({before_days} + 1)) AS start_date,
                toDate('{ts_time}') - INTERVAL 1 DAY AS end_date
        ),
        -- 计算 TRtime 的后 after_days+1 个日期范围的开始日期和结束日期
        start_date_after AS (
            SELECT toDate('{tr_time}') + INTERVAL 1 DAY AS start_date,
                addDays(toDate('{tr_time}'), {after_days} + 1) AS end_date
        ),
        -- 查询 TStime 日期范围之前的数据并添加行号和 period 列
        before_data AS (
            SELECT *,
                row_number() over (partition by code order by timestamps desc) AS row_num,
                0 AS period
            FROM ods_stock.ll_stock_daily_sharing
            WHERE code = '{security_id}'
                AND category = 'stock'
                AND timestamps <= (SELECT end_date FROM start_date_before)
        ),
        -- 查询 TRtime 日期范围之后的数据并添加行号和 period 列
        after_data AS (
            SELECT *,
                row_number() over (partition by code order by timestamps asc) AS row_num,
                2 AS period
            FROM ods_stock.ll_stock_daily_sharing
            WHERE code = '{security_id}'
                AND category = 'stock'
                AND timestamps > (SELECT start_date FROM start_date_after)
        )
        -- 合并两个结果集并按照 timestamps 排序
        SELECT *
        FROM (
                SELECT *
                FROM before_data
                WHERE row_num <= {before_days} + 1
                UNION ALL
                SELECT *
                FROM after_data
                WHERE row_num <= {after_days} + 1
            ) AS combined_data
        ORDER BY timestamps
        """

        result = ck_util.query(query)
        # 将查询结果转换为 Pandas DataFrame
        df = convert_result_to_dataframe(result, COLUMNS_TO_READ)
        return df

    @classmethod
    async def fetch_event_stock_list(cls, event_id: int) -> pd.DataFrame:
        """获取指定事件下所有停牌重组的股票的停牌复牌日期

        Args:
            event_id: 事件ID

        Returns:
            pd.DataFrame: 包含股票ID、文章ID、停牌时间、复牌时间的DataFrame
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._fetch_event_stock_list_sync, event_id)
        except Exception as e:
            logger.error(f"获取事件股票列表出错: {e}")
            raise

    @classmethod
    def _fetch_event_stock_list_sync(cls, event_id: int) -> pd.DataFrame:
        """同步方法获取指定事件下所有停牌重组的股票的停牌复牌日期"""
        # 由于没有ads_events.events_attr_extract_record表，我们模拟一个结果
        logger.warning(f"无法从数据库获取事件{event_id}的股票列表，将返回模拟数据")

        # 创建一个空的DataFrame
        df = pd.DataFrame(columns=['security_id', 'article_id', 'TStime', 'TRtime'])
        return df

    @classmethod
    async def calculate_rate_by_stock_list(cls, stock_code_list: List[str], timestamps: List[str]) -> pd.DataFrame:
        """根据股票代码列表和时间戳列表计算收益率

        Args:
            stock_code_list: 股票代码列表
            timestamps: 时间戳列表

        Returns:
            pd.DataFrame: 包含股票代码和相应时间点数据的DataFrame
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._calculate_rate_by_stock_list_sync, stock_code_list, timestamps)
        except Exception as e:
            logger.error(f"根据股票列表计算收益率出错: {e}")
            raise

    @classmethod
    def _calculate_rate_by_stock_list_sync(cls, stock_code_list: List[str], timestamps: List[str]) -> pd.DataFrame:
        """同步方法根据股票代码列表和时间戳列表计算收益率"""
        COLUMNS_TO_READ = ['code', 'open', 'close', 'high', 'low', 'timestamps']

        if not timestamps:
            return pd.DataFrame(columns=COLUMNS_TO_READ)

        # 格式化时间戳元组
        if len(timestamps) == 1:
            timestamps_str = f"('{timestamps[0]}')"
        else:
            timestamps_str = str(tuple(timestamps))

        all_data_frames = []
        for stock_code in stock_code_list:
            query = f"""
            SELECT {', '.join(COLUMNS_TO_READ)}
            FROM ods_stock.ll_stock_daily_sharing
            WHERE code = '{stock_code}' AND timestamps IN {timestamps_str} AND category = 'stock'
            ORDER BY code, timestamps
            """

            result = ck_util.query(query)
            if result.result_rows:
                df = pd.DataFrame(result.result_rows, columns=result.column_names)
                all_data_frames.append(df)

        if not all_data_frames:
            return pd.DataFrame(columns=COLUMNS_TO_READ)

        combined_df = pd.concat(all_data_frames)
        combined_df['timestamps'] = pd.to_datetime(combined_df['timestamps']).dt.strftime('%Y-%m-%d')
        combined_df = combined_df.reset_index(drop=True)

        return combined_df

    @classmethod
    async def get_supported_similarity_methods(cls) -> List[Dict[str, str]]:
        """获取支持的相似性计算方法

        Returns:
            List[Dict[str, str]]: 相似性计算方法列表
        """
        # 由于没有ll_similarity_methods表，直接返回默认方法列表
        methods = [
            {"id": "dtw", "name": "动态时间规整", "description": "计算时间序列的动态时间规整距离"},
            {"id": "pearson", "name": "皮尔逊相关系数", "description": "计算两个时间序列的皮尔逊相关系数"},
            {"id": "euclidean", "name": "欧氏距离", "description": "计算两个时间序列的欧氏距离"}
        ]
        logger.info(f"返回 {len(methods)} 种相似性计算方法")
        return methods

    @classmethod
    async def get_supported_indicators(cls) -> List[Dict[str, str]]:
        """获取支持的指标列表

        Returns:
            List[Dict[str, str]]: 支持的指标列表
        """
        # 由于没有ll_stock_indicators表，直接返回默认指标列表
        indicators = [
            {"id": "close", "name": "收盘价", "description": "股票的收盘价"},
            {"id": "high", "name": "最高价涨幅", "description": "每日最高价相对于前收盘的涨幅"},
            {"id": "low", "name": "最低价涨幅", "description": "每日最低价相对于前收盘的涨幅"},
            {"id": "turnover", "name": "换手率", "description": "股票的换手率"}
        ]
        logger.info(f"返回 {len(indicators)} 个支持的指标")
        return indicators