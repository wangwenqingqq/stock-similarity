import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from entity.vo.kLine_vo import StockListResponse, KlineDataResponse, SimilarStockResponse
from dao.kLine_dao import StockKLineDAO

logger = logging.getLogger(__name__)


class TimeRangeRequest(BaseModel):
    """K线图时间范围请求"""
    timeRange: str = 'day'  # 'day', 'week', 'month'


class StockCodeRequest(BaseModel):
    """股票代码请求"""
    stockCode: str


class StockListRequest(BaseModel):
    """股票列表请求"""
    page: int = 1
    pageSize: int = 20
    sortBy: str = 'seven_day_return'
    sortOrder: str = 'desc'
    keyword: Optional[str] = None


class KLineService:
    """K线图数据服务类"""

    def __init__(self):
        """初始化服务"""
        self.kline_dao = StockKLineDAO()


    async def get_stock_list(self, request: StockListRequest) -> StockListResponse:
        """
        获取股票列表

        Args:
            request: 股票列表请求参数

        Returns:
            StockListResponse: 股票列表响应
        """
        try:
            # 调用DAO层获取股票列表
            result = await StockKLineDAO.fetch_stock_list(
                page=request.page,
                page_size=request.pageSize,
                sort_by=request.sortBy,
                sort_order=request.sortOrder,
                keyword=request.keyword
            )

            # 构建响应对象
            response = StockListResponse(
                items=result['items'],
                total=result['total']
            )

            return response
        except Exception as e:
            logger.error(f"获取股票列表出错: {e}")
            raise

    async def get_kline_data(self, stock_code: str, time_range: str = 'day',
                             data_type: Optional[str] = None) -> KlineDataResponse:
        """
        获取K线图数据

        Args:
            stock_code: 股票代码
            time_range: 时间范围，可选 'day', 'week', 'month'
            data_type: 数据类型，若为'close'则只返回收盘价数据

        Returns:
            KlineDataResponse: K线图数据响应
        """
        try:
            # 调用DAO层获取K线图数据
            kline_data = await StockKLineDAO.load_kline_data(
                stock_code=stock_code,
                time_range=time_range,
                data_type=data_type
            )

            # 获取股票基本信息
            stock_info = await self._get_stock_info(stock_code)

            # 构建响应对象
            response = KlineDataResponse(
                categories=kline_data.get('categories', []),
                values=kline_data.get('values', []),
                ma5=kline_data.get('ma5', []),
                ma10=kline_data.get('ma10', []),
                ma20=kline_data.get('ma20', []),
                volumes=kline_data.get('volumes', []),
                stockName=stock_info.get('name', ''),
                stockCode=stock_code
            )
            print("response in service", response)
            # 如果只请求收盘价数据
            if data_type == 'close':
                response.close = kline_data.get('close', [])

            return response
        except Exception as e:
            logger.error(f"获取K线图数据出错: {e}")
            raise

    async def find_similar_stocks(self, stock_code: str) -> List[SimilarStockResponse]:
        """
        查找相似股票

        Args:
            stock_code: 股票代码

        Returns:
            List[SimilarStockResponse]: 相似股票列表响应
        """
        try:
            # 调用DAO层查找相似股票
            similar_stocks = await StockKLineDAO.find_similar_stocks(stock_code)

            # 构建响应对象
            response = [
                SimilarStockResponse(
                    code=stock['code'],
                    name=stock['name'],
                    similarity=stock['similarity'],
                    correlation=stock.get('correlation', 0),
                    sevenDayReturn=stock.get('seven_day_return'),
                    thirtyDayReturn=stock.get('thirty_day_return')
                ) for stock in similar_stocks
            ]

            return response
        except Exception as e:
            logger.error(f"查找相似股票出错: {e}")
            raise

    # async def compare_stocks_performance(self, base_stock_code: str,
    #                                      compare_stock_codes: List[str]) -> Dict[str, Any]:
    #     """
    #     比较多只股票的性能表现
    #
    #     Args:
    #         base_stock_code: 基准股票代码
    #         compare_stock_codes: 比较股票代码列表
    #
    #     Returns:
    #         Dict: 性能比较数据
    #     """
    #     try:
    #         # 获取当前日期和一年前日期
    #         end_date = datetime.now().strftime('%Y-%m-%d')
    #         start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    #
    #         # 获取基准股票数据
    #         base_stock_data = await self._get_stock_historical_data(base_stock_code, start_date, end_date)
    #
    #         # 获取比较股票数据
    #         comparison_data = {}
    #         for code in compare_stock_codes:
    #             stock_data = await self._get_stock_historical_data(code, start_date, end_date)
    #             stock_info = await self._get_stock_info(code)
    #             comparison_data[code] = {
    #                 'name': stock_info.get('name', ''),
    #                 'data': stock_data
    #             }
    #
    #         # 计算相对收益率
    #         performance_data = self._calculate_relative_returns(base_stock_data, comparison_data)
    #
    #         return performance_data
    #     except Exception as e:
    #         logger.error(f"比较股票性能出错: {e}")
    #         raise

    # async def analyze_technical_indicators(self, stock_code: str,
    #                                        time_range: str = 'day') -> Dict[str, Any]:
    #     """
    #     分析股票技术指标
    #
    #     Args:
    #         stock_code: 股票代码
    #         time_range: 时间范围，可选 'day', 'week', 'month'
    #
    #     Returns:
    #         Dict: 技术指标分析结果
    #     """
    #     try:
    #         # 获取K线图数据
    #         kline_data = await StockKLineDAO.load_kline_data(
    #             stock_code=stock_code,
    #             time_range=time_range
    #         )
    #
    #         # 转换为DataFrame
    #         dates = kline_data.get('categories', [])
    #         close_prices = [v[1] for v in kline_data.get('values', [])]
    #
    #         df = pd.DataFrame({
    #             'date': dates,
    #             'close': close_prices
    #         })
    #
    #         # 计算技术指标
    #         technical_indicators = self._calculate_technical_indicators(df)
    #
    #         return technical_indicators
    #     except Exception as e:
    #         logger.error(f"分析技术指标出错: {e}")
    #         raise

    async def _get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        获取股票基本信息

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 股票基本信息
        """
        # 此处可扩展为从数据库获取更多股票基本信息
        # 目前简单实现，从股票列表中获取
        try:
            result = await StockKLineDAO.fetch_stock_list(
                page=1,
                page_size=1,
                keyword=stock_code
            )

            if result['items'] and len(result['items']) > 0:
                return result['items'][0]
            else:
                logger.warning(f"未找到股票代码 {stock_code} 的基本信息")
                return {'code': stock_code, 'name': ''}
        except Exception as e:
            logger.error(f"获取股票基本信息出错: {e}")
            return {'code': stock_code, 'name': ''}

    async def _get_stock_historical_data(self, stock_code: str,
                                         start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票历史数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 股票历史数据
        """
        # 这里简化实现，实际应该调用专门的DAO方法
        kline_data = await StockKLineDAO.load_kline_data(
            stock_code=stock_code,
            time_range='month'  # 使用月范围获取足够的历史数据
        )

        dates = kline_data.get('categories', [])
        closes = [v[1] for v in kline_data.get('values', [])]

        df = pd.DataFrame({
            'date': dates,
            'close': closes
        })

        # 过滤日期范围
        df['date'] = pd.to_datetime(df['date'])
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

        return df

    def _calculate_relative_returns(self, base_data: pd.DataFrame,
                                    comparison_data: Dict[str, Dict]) -> Dict[str, Any]:
        """
        计算相对收益率

        Args:
            base_data: 基准股票数据
            comparison_data: 比较股票数据

        Returns:
            Dict: 相对收益率结果
        """
        # 计算基准股票的基准收益率
        if base_data.empty:
            return {}

        base_returns = self._calculate_returns(base_data)

        # 计算各比较股票的相对收益率
        relative_returns = {
            'dates': base_returns['dates'].tolist(),
            'base': {
                'code': base_data['code'].iloc[0] if 'code' in base_data.columns else '',
                'name': base_data['name'].iloc[0] if 'name' in base_data.columns else '',
                'returns': base_returns['returns'].tolist()
            },
            'comparison': []
        }

        for code, stock_info in comparison_data.items():
            stock_data = stock_info['data']
            if not stock_data.empty:
                stock_returns = self._calculate_returns(stock_data)

                # 对齐日期
                merged_df = pd.merge(
                    pd.DataFrame({
                        'date': base_returns['dates'],
                        'base_return': base_returns['returns']
                    }),
                    pd.DataFrame({
                        'date': stock_returns['dates'],
                        'stock_return': stock_returns['returns']
                    }),
                    on='date',
                    how='inner'
                )

                if not merged_df.empty:
                    relative_returns['comparison'].append({
                        'code': code,
                        'name': stock_info['name'],
                        'returns': merged_df['stock_return'].tolist(),
                        'relativeDates': merged_df['date'].tolist()
                    })

        return relative_returns

    def _calculate_returns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算收益率

        Args:
            data: 股票数据

        Returns:
            Dict: 收益率结果
        """
        if data.empty:
            return {'dates': pd.Series(dtype='datetime64[ns]'), 'returns': pd.Series(dtype='float64')}

        # 确保日期字段为日期类型
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])

        # 计算日收益率
        data = data.sort_values('date')
        data['return'] = data['close'].pct_change()

        # 计算累计收益率
        data['cumulative_return'] = (1 + data['return']).cumprod() - 1

        return {
            'dates': data['date'],
            'returns': data['cumulative_return']
        }

    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算技术指标

        Args:
            data: 股票数据

        Returns:
            Dict: 技术指标结果
        """
        if data.empty:
            return {}

        # 计算RSI (相对强弱指标)
        def calculate_rsi(series, period=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        # 计算MACD (移动平均收敛散度)
        def calculate_macd(series, fast=12, slow=26, signal=9):
            ema_fast = series.ewm(span=fast, adjust=False).mean()
            ema_slow = series.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            return {
                'macd_line': macd_line,
                'signal_line': signal_line,
                'histogram': histogram
            }

        # 计算布林带
        def calculate_bollinger_bands(series, period=20, std_dev=2):
            middle_band = series.rolling(window=period).mean()
            std = series.rolling(window=period).std()
            upper_band = middle_band + (std * std_dev)
            lower_band = middle_band - (std * std_dev)
            return {
                'upper': upper_band,
                'middle': middle_band,
                'lower': lower_band
            }

        # 确保close列存在
        if 'close' not in data.columns:
            return {}

        # 计算各指标
        rsi = calculate_rsi(data['close'])
        macd = calculate_macd(data['close'])
        bollinger = calculate_bollinger_bands(data['close'])

        # 返回结果
        return {
            'dates': data['date'].tolist(),
            'rsi': rsi.dropna().tolist(),
            'macd': {
                'macd_line': macd['macd_line'].dropna().tolist(),
                'signal_line': macd['signal_line'].dropna().tolist(),
                'histogram': macd['histogram'].dropna().tolist()
            },
            'bollinger': {
                'upper': bollinger['upper'].dropna().tolist(),
                'middle': bollinger['middle'].dropna().tolist(),
                'lower': bollinger['lower'].dropna().tolist()
            }
        }