import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request, Query
from config.enums import RedisInitKeyConfig
from entity.vo.kLine_vo import StockListResponse, KlineDataResponse, SimilarStockResponse
from dao.kLine_dao import KLineDAO

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
        self.kline_dao = KLineDAO()


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
            result = await KLineDAO.fetch_stock_list(
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

    async def get_kline_data(self, request,stock_code: str, time_range: str = 'day',
                             data_type: Optional[str] = None) -> KlineDataResponse:
        """
        获取K线图数据

        Args:
            request: 前端请求
            stock_code: 股票代码
            time_range: 时间范围，可选 'day', 'week', 'month'
            data_type: 数据类型，若为'close'则只返回收盘价数据

        Returns:
            KlineDataResponse: K线图数据响应
        """
        try:
              # 构建Redis键名
            redis_key = f"{RedisInitKeyConfig.STOCK_KLINE.key}:{stock_code}:{time_range}"
            
            # 尝试从Redis获取数据
            cached_data = await request.app.state.redis.get(redis_key)
            
            if cached_data:
                # 如果Redis中有数据，直接返回
                kline_data = json.loads(cached_data)
            else:
                # 如果Redis中没有数据，从数据库获取
                kline_data = await KLineDAO.load_kline_data(
                    stock_code=stock_code,
                    time_range=time_range,
                    data_type=data_type
                )
                
                # 将数据存入Redis，设置过期时间（例如1小时）
                await request.app.state.redis.set(
                    redis_key,
                    json.dumps(kline_data),
                    ex=3600  # 1小时过期
                )

            # 获取股票基本信息
            stock_info = await self._get_stock_info(stock_code)

            # 构建响应对象
            response = KlineDataResponse(
                categories=kline_data.get('categories', []),
                values=kline_data.get('values', []),
                ma5=kline_data.get('ma5', []),
                ma10=kline_data.get('ma10', []),
                ma30=kline_data.get('ma30', []),
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
            similar_stocks = await KLineDAO.find_similar_stocks(stock_code)

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
            result = await KLineDAO.fetch_stock_list(
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
        kline_data = await KLineDAO.load_kline_data(
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
# async def update_kline_cache(self, request: Request, stock_code: str, time_range: str):
#     """
#     更新K线数据缓存
#     """
#     try:
#         # 从数据库获取最新数据
#         kline_data = await KLineDAO.load_kline_data(
#             stock_code=stock_code,
#             time_range=time_range
#         )
#
#         # 更新Redis缓存
#         redis_key = f"{RedisInitKeyConfig.STOCK_KLINE.key}:{stock_code}:{time_range}"
#         await request.app.state.redis.set(
#             redis_key,
#             json.dumps(kline_data),
#             ex=3600  # 1小时过期
#         )
#
#         return True
#     except Exception as e:
#         logger.error(f"更新K线数据缓存出错: {e}")
#         return False