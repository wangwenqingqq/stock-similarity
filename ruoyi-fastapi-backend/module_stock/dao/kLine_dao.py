import asyncio
import math
import re

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from utils import ck_util
from utils.data_util import convert_result_to_dataframe

logger = logging.getLogger(__name__)


class KLineDAO:
    """
    股票K线数据访问对象
    处理股票K线图数据的查询和相关计算
    """

    @classmethod
    async def fetch_stock_list(cls, page: int = 1, page_size: int = 20,
                               sort_by: str = 'seven_day_return',
                               sort_order: str = 'desc',
                               keyword: Optional[str] = None) -> Dict[str, Any]:
        """
        异步获取股票列表，支持分页、排序和搜索

        Args:
            page: 页码
            page_size: 每页大小
            sort_by: 排序字段
            sort_order: 排序方式('asc'或'desc')
            keyword: 搜索关键词

        Returns:
            Dict: 包含股票列表和总数的字典
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                cls._fetch_stock_list_sync,
                page,
                page_size,
                sort_by,
                sort_order,
                keyword
            )
        except Exception as e:
            logger.error(f"获取股票列表出错: {e}")
            raise

    @classmethod
    def _fetch_stock_list_sync(cls, page: int = 1, page_size: int = 20,
                               sort_by: str = 'seven_day_return',
                               sort_order: str = 'desc',
                               keyword: Optional[str] = None) -> Dict[str, Any]:
        """
        同步方法获取股票列表

        Args:
            page: 页码
            page_size: 每页大小
            sort_by: 排序字段
            sort_order: 排序方式('asc'或'desc')
            keyword: 搜索关键词

        Returns:
            Dict: 包含股票列表和总数的字典
        """
        try:
            # 先查询数据库中的最大日期
            max_date_query = """
            SELECT max(timestamps) as max_date
            FROM ods_stock.ll_stock_daily_sharing
            WHERE category = 'stock'
            """

            max_date_result = ck_util.query(max_date_query)
            if max_date_result.result_rows and max_date_result.result_rows[0][0]:
                # 获取数据库中的最大日期
                max_date = max_date_result.result_rows[0][0]
                end_date = max_date
                start_date = (max_date - timedelta(days=30)).strftime('%Y-%m-%d')
                seven_day_ago = (max_date - timedelta(days=7)).strftime('%Y-%m-%d')

            # 构建关键词查询条件
            keyword_condition = ""
            if keyword:
                keyword_condition = f"AND (s.SecuCode LIKE '%{keyword}%' OR s.SecuName LIKE '%{keyword}%')"

            # 查询股票列表，计算7日和30日收益率
            query = f"""
            WITH 
                -- 首先找出同时存在于两表中的股票代码
                valid_codes AS (
                    SELECT DISTINCT d.code
                    FROM ods_stock.ll_stock_daily_sharing d
                    INNER JOIN events_temp.lc_csiinduspe s ON d.code = s.SecuCode
                    WHERE d.category = 'stock'
                ),
                -- 只对有效代码计算最新日期
                latest_prices AS (
                    SELECT 
                        code,
                        toDate(max(timestamps)) as latest_date
                    FROM ods_stock.ll_stock_daily_sharing
                    WHERE timestamps >= toDate('{start_date}')
                      AND timestamps <= toDate('{end_date}')
                      AND category = 'stock'
                      AND code IN (SELECT code FROM valid_codes)
                    GROUP BY code
                ),
                -- 获取当前价格数据
                current_prices AS (
                    SELECT 
                        d.code,
                        d.close as current_price,
                        d.open,
                        d.high,
                        d.low,
                        d.ycp as pre_close,
                        d.vol as volume,
                        d.amount
                    FROM ods_stock.ll_stock_daily_sharing d
                    JOIN latest_prices l ON d.code = l.code AND toDate(d.timestamps) = l.latest_date
                    WHERE d.category = 'stock'
                ),
                -- 七日前价格数据
                seven_days_ago AS (
                    SELECT 
                        d.code,
                        d.close as price_7d_ago
                    FROM ods_stock.ll_stock_daily_sharing d
                    WHERE d.category = 'stock'
                      AND toDate(d.timestamps) = toDate('{seven_day_ago}')
                      AND code IN (SELECT code FROM valid_codes)
                ),
                -- 三十日前价格数据
                thirty_days_ago AS (
                    SELECT 
                        d.code,
                        d.close as price_30d_ago
                    FROM ods_stock.ll_stock_daily_sharing d
                    WHERE d.category = 'stock'
                      AND toDate(d.timestamps) = toDate('{start_date}')
                      AND code IN (SELECT code FROM valid_codes)
                )
            SELECT 
                c.code as code,
                s.SecuName as name,
                c.current_price as price,
                (c.current_price - c.pre_close) / c.pre_close * 100 as change_rate,
                c.volume,
                c.high,
                c.low,
                c.open,
                c.amount,
                c.pre_close,
                CASE 
                    WHEN sd.price_7d_ago IS NOT NULL AND sd.price_7d_ago != 0 
                    THEN (c.current_price - sd.price_7d_ago) / sd.price_7d_ago * 100 
                    ELSE NULL 
                END as seven_day_return,
                CASE 
                    WHEN td.price_30d_ago IS NOT NULL AND td.price_30d_ago != 0 
                    THEN (c.current_price - td.price_30d_ago) / td.price_30d_ago * 100 
                    ELSE NULL 
                END as thirty_day_return
            FROM current_prices c
            LEFT JOIN seven_days_ago sd ON c.code = sd.code
            LEFT JOIN thirty_days_ago td ON c.code = td.code
            INNER JOIN events_temp.lc_csiinduspe s ON c.code = s.SecuCode
            WHERE 1=1
            {keyword_condition}
            ORDER BY {sort_by} {sort_order}
            """

            # 计算总数的查询保持不变
            count_query = f"""
            SELECT 
                count(*) as total
            FROM (
                SELECT 
                    d.code
                FROM ods_stock.ll_stock_daily_sharing d
                INNER JOIN events_temp.lc_csiinduspe s ON d.code = s.SecuCode
                WHERE d.category = 'stock'
                  AND toDate(d.timestamps) = toDate('{end_date}')
                  {keyword_condition}
                GROUP BY d.code
            )
            """

            # 执行总数查询
            total_result = ck_util.query(count_query)
            # 修改：使用 result_rows 属性来访问结果
            total = total_result.result_rows[0][0] if total_result.result_rows else 0

            # 添加分页
            paginated_query = f"{query} LIMIT {page_size} OFFSET {(page - 1) * page_size}"

            # 执行分页查询
            result = ck_util.query(paginated_query)
            # 列名
            columns = ['code', 'name', 'price', 'change_rate', 'volume', 'high', 'low', 'open', 'pre_close',
                       'seven_day_return', 'thirty_day_return']

            # 将查询结果转换为DataFrame
            df = convert_result_to_dataframe(result, columns)

            # 处理 NaN 值
            df = df.replace({np.nan: None})

            # 将DataFrame转换为字典列表
            items = df.to_dict(orient='records')

            # 确保所有 numpy 类型都转换为 Python 原生类型
            for item in items:
                for key in item:
                    if pd.isna(item[key]):
                        item[key] = None
                    elif isinstance(item[key], (np.float64, np.int64)):
                        item[key] = item[key].item()
                # 确保code字段为字符串
                if item['code'] is None:
                    item['code'] = "111111"
                else:
                    item['code'] = str(item['code'])
            return {
                'items': items,
                'total': total
            }
        except Exception as e:
            logger.error(f"执行股票列表查询出错: {e}")
            raise

    @classmethod
    async def load_kline_data(cls, stock_code: str, time_range: str = 'day',
                              data_type: Optional[str] = None) -> Dict[str, Any]:
        """
        异步加载特定股票的K线图数据

        Args:
            stock_code: 股票代码
            time_range: 时间范围('day', 'week', 'month')
            data_type: 数据类型，若为'close'则只返回收盘价

        Returns:
            Dict: K线图数据
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                cls._load_kline_data_sync,
                stock_code,
                time_range,
                data_type
            )
        except Exception as e:
            logger.error(f"加载K线图数据出错: {e}")
            raise

    import re
    import math
    from typing import Dict, Any, Optional, List
    from datetime import datetime, date, timedelta
    import pandas as pd
    import logging

    logger = logging.getLogger(__name__)

    @classmethod
    def _load_kline_data_sync(cls, stock_code: str, time_range: str = 'day',
                              data_type: Optional[str] = None) -> Dict[str, Any]:
        """
        同步方法加载特定股票的K线图数据

        Args:
            stock_code: 股票代码
            time_range: 时间范围('day', 'week', 'month')
            data_type: 数据类型，若为'close'则只返回收盘价

        Returns:
            Dict: K线图数据
        """
        # 创建默认的空返回结构
        empty_result = {
            'categories': [],
            'values': [],
            'ma5': [],
            'ma10': [],
            'ma30': [],
            'volumes': []
        }

        # 验证股票代码格式
        if not re.match(r'^[A-Za-z0-9.]+$', stock_code):
            logger.error(f"无效的股票代码格式: {stock_code}")
            return empty_result

        try:
            # 查询最大日期
            max_date_query = """
                    SELECT max(timestamps) as max_date
                    FROM ods_stock.ll_stock_daily_sharing
                    WHERE category = 'stock'
                    """
            max_date_result = ck_util.query(max_date_query)

            # 安全地获取和处理最大日期
            if not max_date_result or not max_date_result.result_rows:
                logger.error("无法获取最大日期")
                return empty_result

            # 确保end_date是datetime对象
            end_date = max_date_result.result_rows[0][0]

            # 计算开始日期
            date_ranges = {
                'day': 90,
                'week': 180,
                'month': 365
            }
            days = date_ranges.get(time_range, 90)
            start_date = (end_date - timedelta(days=days)).strftime('%Y-%m-%d')

            # 使用ClickHouse支持的参数方式
            query = f"""
            SELECT 
                code,
                open,
                close,
                high,
                low,
                ycp,
                vol,
                timestamps as date
            FROM ods_stock.ll_stock_daily_sharing
            WHERE code = '{stock_code}'
              AND category = 'stock'
              AND timestamps >= toDate('{start_date}')
              AND timestamps <= toDate('{end_date}')
            ORDER BY timestamps ASC
            """

            result = ck_util.query(query)
            columns = ['code', 'open', 'close', 'high', 'low', 'ycp', 'vol', 'date']
            df = convert_result_to_dataframe(result, columns)

            # 确保数值列是数值类型
            for col in ['open', 'close', 'high', 'low', 'vol']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # 检查是否有数据
            if df.empty:
                logger.warning(f"未找到股票{stock_code}的数据")
                return empty_result

            # 如果只需要收盘价
            if data_type == 'close':
                return {
                    # 确保日期是字符串格式
                    'categories': [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in df['date']],
                    'close': df['close'].tolist()
                }

            # 计算K线图数据 - 确保日期是字符串
            categories = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in df['date']]

            # K线图数据格式为 [open, close, low, high]
            values = df.apply(lambda row: [
                float(row['open']) if not pd.isna(row['open']) else None,
                float(row['close']) if not pd.isna(row['close']) else None,
                float(row['low']) if not pd.isna(row['low']) else None,
                float(row['high']) if not pd.isna(row['high']) else None
            ], axis=1).tolist()

            # 计算MA5, MA10, MA30均线
            df['ma5'] = df['close'].rolling(window=5).mean().fillna(0)
            df['ma10'] = df['close'].rolling(window=10).mean().fillna(0)
            df['ma30'] = df['close'].rolling(window=30).mean().fillna(0)

            # 更安全的浮点数列表转换函数
            def safe_float_list(series):
                result = []
                for x in series:
                    try:
                        float_value = float(x)
                        if math.isnan(float_value) or math.isinf(float_value):
                            result.append(None)
                        else:
                            result.append(float_value)
                    except (TypeError, ValueError):
                        result.append(None)
                return result

            return {
                'categories': categories,  # 现在确保是字符串列表
                'values': values,
                'ma5': safe_float_list(df['ma5']),
                'ma10': safe_float_list(df['ma10']),
                'ma30': safe_float_list(df['ma30']),
                'volumes': safe_float_list(df['vol'])
            }

        except Exception as e:
            logger.error(f"执行K线图数据查询出错: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return empty_result

    @classmethod
    async def find_similar_stocks(cls, stock_code: str) -> List[Dict[str, Any]]:
        """
        异步查找与特定股票相似的股票

        Args:
            stock_code: 股票代码

        Returns:
            List[Dict]: 相似股票列表
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                cls._find_similar_stocks_sync,
                stock_code
            )
        except Exception as e:
            logger.error(f"查找相似股票出错: {e}")
            raise

    @classmethod
    def _find_similar_stocks_sync(cls, stock_code: str) -> List[Dict[str, Any]]:
        """
        同步方法查找与特定股票相似的股票

        Args:
            stock_code: 股票代码

        Returns:
            List[Dict]: 相似股票列表
        """
        try:
            # 获取目标股票最近90天的收盘价数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

            target_query = f"""
            SELECT 
                code,
                close,
                timestamps
            FROM ods_stock.ll_stock_daily_sharing
            WHERE code = '{stock_code}'
              AND category = 'stock'
              AND timestamps >= toDate('{start_date}')
              AND timestamps <= toDate('{end_date}')
            ORDER BY timestamps ASC
            """

            target_result = ck_util.query(target_query)
            target_df = convert_result_to_dataframe(target_result, ['code', 'close', 'timestamps'])

            if target_df.empty:
                logger.warning(f"未找到股票代码 {stock_code} 的数据")
                return []

            # 获取所有股票最近90天的收盘价数据
            all_stocks_query = f"""
            SELECT 
                d.code,
                s.SecuName as name,
                d.close,
                d.timestamps
            FROM ods_stock.ll_stock_daily_sharing d
            LEFT JOIN events_temp.lc_csiinduspe s ON d.code = s.SecuCode
            WHERE d.category = 'stock'
              AND d.timestamps >= toDate('{start_date}')
              AND d.timestamps <= toDate('{end_date}')
              AND d.code != '{stock_code}'
            ORDER BY d.code, d.timestamps ASC
            """

            all_stocks_result = ck_util.query(all_stocks_query)
            all_stocks_df = convert_result_to_dataframe(all_stocks_result, ['code', 'name', 'close', 'timestamps'])

            # 计算与目标股票的相似度
            similar_stocks = []

            # 数据透视表以获取每个股票的时间序列
            pivot_df = all_stocks_df.pivot(index='timestamps', columns='code', values='close')

            # 获取目标股票的时间序列
            target_series = pd.Series(target_df['close'].values, index=target_df['timestamps'])

            # 获取不重复的股票代码和名称
            stocks_info = all_stocks_df[['code', 'name']].drop_duplicates()

            # 计算相关系数
            for stock_code in pivot_df.columns:
                stock_series = pivot_df[stock_code].dropna()

                # 确保有足够的数据进行比较
                if len(stock_series) < 30:
                    continue

                # 对齐时间序列
                common_idx = stock_series.index.intersection(target_series.index)
                if len(common_idx) < 30:
                    continue

                stock_aligned = stock_series.loc[common_idx]
                target_aligned = target_series.loc[common_idx]

                # 计算相关系数
                correlation = stock_aligned.corr(target_aligned)

                # 计算相似度分数 (0-1之间，越接近1表示越相似)
                similarity = (correlation + 1) / 2

                if not np.isnan(similarity) and similarity > 0.7:  # 只保留相似度高于0.7的股票
                    stock_name = stocks_info.loc[stocks_info['code'] == stock_code, 'name'].iloc[0] if not \
                    stocks_info.loc[stocks_info['code'] == stock_code].empty else ''

                    # 计算7日和30日收益率
                    end_date_dt = datetime.now()
                    seven_day_ago = (end_date_dt - timedelta(days=7)).strftime('%Y-%m-%d')
                    thirty_day_ago = (end_date_dt - timedelta(days=30)).strftime('%Y-%m-%d')

                    returns_query = f"""
                    WITH 
                        latest AS (
                            SELECT 
                                close as latest_price
                            FROM ods_stock.ll_stock_daily_sharing
                            WHERE code = '{stock_code}'
                              AND category = 'stock'
                              AND timestamps <= toDate('{end_date}')
                            ORDER BY timestamps DESC
                            LIMIT 1
                        ),
                        seven_day AS (
                            SELECT 
                                close as price_7d_ago
                            FROM ods_stock.ll_stock_daily_sharing
                            WHERE code = '{stock_code}'
                              AND category = 'stock'
                              AND timestamps <= toDate('{seven_day_ago}')
                            ORDER BY timestamps DESC
                            LIMIT 1
                        ),
                        thirty_day AS (
                            SELECT 
                                close as price_30d_ago
                            FROM ods_stock.ll_stock_daily_sharing
                            WHERE code = '{stock_code}'
                              AND category = 'stock'
                              AND timestamps <= toDate('{thirty_day_ago}')
                            ORDER BY timestamps DESC
                            LIMIT 1
                        )
                    SELECT 
                        l.latest_price,
                        s.price_7d_ago,
                        t.price_30d_ago
                    FROM latest l, seven_day s, thirty_day t
                    """

                    returns_result = ck_util.query(returns_query)

                    seven_day_return = None
                    thirty_day_return = None

                    if returns_result:
                        latest_price, price_7d_ago, price_30d_ago = returns_result[0]

                        if price_7d_ago and price_7d_ago != 0:
                            seven_day_return = (latest_price - price_7d_ago) / price_7d_ago * 100

                        if price_30d_ago and price_30d_ago != 0:
                            thirty_day_return = (latest_price - price_30d_ago) / price_30d_ago * 100

                    similar_stocks.append({
                        'code': stock_code,
                        'name': stock_name,
                        'similarity': similarity,
                        'correlation': correlation,
                        'seven_day_return': seven_day_return,
                        'thirty_day_return': thirty_day_return
                    })

            # 按相似度降序排序
            similar_stocks.sort(key=lambda x: x['similarity'], reverse=True)

            # 取前10个最相似的股票
            return similar_stocks[:10]
        except Exception as e:
            logger.error(f"执行相似股票查询出错: {e}")
            raise