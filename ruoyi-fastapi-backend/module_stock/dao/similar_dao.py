from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from fastdtw import fastdtw
from clickhouse_driver import Client
from module_stock.entity.vo.similar_vo import *
import logging
import asyncio
from utils import ck_util
from utils.data_util import convert_result_to_dataframe
logger = logging.getLogger(__name__)


class SimilarDao:
    """股票数据访问对象，负责从数据源获取股票数据"""

    @classmethod
    async def get_section_stock_info(cls, section_code_list: list, start_date: str, end_date: str) -> pd.DataFrame:
        """
        异步查询指定股票代码列表对应的所有股票的相关数据

        Args:
            section_code_list: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 包含多只股票数据的DataFrame
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_section_stock_info_sync, section_code_list, start_date,
                                              end_date)
        except Exception as e:
            logger.error(f"获取板块股票数据出错: {e}")
            raise

    @classmethod
    def _get_section_stock_info_sync(cls, section_code_list: list, start_date: str, end_date: str) -> pd.DataFrame:
        """
        同步方法查询指定股票代码列表对应的所有股票的相关数据

        Args:
            section_code_list: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 包含多只股票数据的DataFrame
        """
        try:
            COLUMNS_TO_READ = ['code', 'open', 'close', 'high', 'low', 'ycp', 'vol', 'timestamps']

            if not section_code_list:
                logger.warning("股票代码列表为空")
                return pd.DataFrame(columns=COLUMNS_TO_READ)

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
            WHERE code IN ({', '.join(f"'{code}'" for code in section_code_list)})
                AND category = 'stock'
                AND timestamps >= toDate('{start_date}')
                AND timestamps <= toDate('{end_date}')
            ORDER BY code, timestamps
            """

            result = ck_util.query(query)
            # 将查询结果转换为 Pandas DataFrame
            return convert_result_to_dataframe(result, COLUMNS_TO_READ)
        except Exception as e:
            logger.error(f"执行板块股票数据查询出错: {e}")
            raise

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
            # 使用新的数据源 events_temp.lc_csiinduspe
            query = f"""
            SELECT SecuCode, SecuName
            FROM events_temp.lc_csiinduspe
            WHERE SecuCode = '{stock_code}'
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
            # 使用 lc_csiinduspe 表中的信息
            stock_info = {
                "code": row[0],  # SecuCode
                "name": row[1],  # SecuName
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
    async def get_stock_nums(cls, stock_code: str, section_level: int = 1) -> pd.DataFrame:
        """获取股票行业分类数据

        Args:
            stock_code: 股票代码
            section_level: 行业分类级别，默认为1

        Returns:
            pd.DataFrame: 行业分类数据
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_stock_nums_sync, stock_code, section_level)
        except Exception as e:
            logger.error(f"获取股票行业分类数据出错 {stock_code}: {e}")
            raise

    @classmethod
    def _get_stock_nums_sync(cls, stock_code: str, section_level: int = 1) -> pd.DataFrame:
        """同步方法获取股票行业分类数据"""
        COLUMNS_TO_READ = ['SecuCode', 'SecuAbbr', 'IndustryName', 'FirstIndustryCode', 'FirstIndustryName']

        query = f"""
        SELECT * FROM events_temp.lc_csiinduspe WHERE SecuCode = '{stock_code}'
        """

        result = ck_util.query(query)
        # 将查询结果转换为 Pandas DataFrame
        df = pd.DataFrame(result.result_rows, columns=result.column_names)

        return df

    @classmethod
    async def get_stock(cls, stock_code: str, code: str, board: int, code_type: str, is_st: int) -> tuple:
        """获取符合条件的股票代码和名称列表

        Args:
            stock_code: 需要排除的股票代码
            code: 条件代码值
            board: 板块值
            code_type: 查询的列名
            is_st: 是否为ST股票，1表示是，0表示否

        Returns:
            tuple: 包含股票代码列表和股票名称列表的元组
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_stock_sync, stock_code, code, board, code_type, is_st)
        except Exception as e:
            logger.error(
                f"获取股票列表出错，参数：stock_code={stock_code}, code={code}, board={board}, code_type={code_type}, is_st={is_st}: {e}")
            raise

    @classmethod
    def _get_stock_sync(cls, stock_code: str, code: str, board: int, code_type: str, is_st: int) -> tuple:
        """同步方法获取符合条件的股票代码和名称列表"""
        column_name = code_type
        try:
            if is_st == 1:
                query = (
                    f"SELECT SecuName,SecuCode FROM events_temp.lc_csiinduspe WHERE {column_name} = '{code}' AND board = {board} AND ("
                    f"SecuName LIKE 'ST%' OR SecuName LIKE '*ST%');")
            else:
                query = (
                    f"SELECT SecuName,SecuCode FROM events_temp.lc_csiinduspe WHERE {column_name} = '{code}' AND board = {board} AND NOT "
                    f"(SecuName LIKE 'ST%' OR SecuName LIKE '*ST%');")

            result = ck_util.query(query)
            # 将查询结果转换为 Pandas DataFrame
            df = pd.DataFrame(result.result_rows, columns=result.column_names).pipe(
                lambda x: x[x['SecuCode'] != stock_code]).reset_index(drop=True)

            stock_code_list = df['SecuCode'].tolist()
            stock_name_list = df['SecuName'].tolist()

            return stock_code_list, stock_name_list
        except Exception as e:
            logger.error(f"执行股票查询出错: {e}")
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