import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession

from entity.vo.history_vo import *
from dao.history_dao import HistoryDAO
from dao.result_dao import ResultDAO

logger = logging.getLogger(__name__)


class QueryHistoryListRequest(BaseModel):
    """查询历史列表请求"""
    user_id: int = Field(None, alias="userId")
    page: int = 1
    pageSize: int = 10
    sortBy: str = 'query_time'
    sortOrder: str = 'desc'


class DeleteBatchRequest(BaseModel):
    """批量删除请求"""
    historyIds: List[int]


class ExportHistoryRequest(BaseModel):
    """导出历史请求"""
    stockCode: Optional[str] = None
    stockName: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    format: str = 'excel'


class HistoryStatisticsRequest(BaseModel):
    """历史统计请求"""
    startDate: Optional[str] = None
    endDate: Optional[str] = None


class HistoryService:
    """股票相似性查询历史服务类"""

    def __init__(self):
        """初始化服务"""
        self.history_dao = HistoryDAO()
        self.result_dao = ResultDAO()

    async def create_history(self, db: AsyncSession, request: QueryHistoryVO) -> Dict[str, Any]:
        """
        创建新的查询历史记录

        Args:
            db: 数据库会话
            request: 创建历史记录请求参数

        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            # 调用DAO层创建历史记录
            history_id = await HistoryDAO.create_history(
                db,
                user_id=request.user_id,
                stock_code=request.stock_code,  # 改为 stock_code
                stock_name=request.stock_name,  # 改为 stock_name
                start_date=request.start_date,  # 改为 start_date
                end_date=request.end_date,  # 改为 end_date
                indicators=request.indicators,
                method=request.method,
                compare_scope=request.compare_scope,  # 改为 compare_scope
                similar_count=int(request.similar_count),  # 改为 similar_count
                remark=request.remark,
                status=int(request.status),
                similar_results = request.similar_results
            )

            # 获取创建的历史记录详情
            history = await HistoryDAO.get_history_by_id(db, history_id)

            return {
                'id': history_id,
                'stock_code': history['stock_code'],
                'stock_name': history['stock_name'],
                'query_time': history['query_time']
            }
        except Exception as e:
            logger.error(f"创建查询历史记录出错: {e}")
            raise

    async def get_history_list(self, db: AsyncSession, user_id, page,page_size,sort_by,sort_order) -> QueryHistoryListResponse:
        """
        获取查询历史列表

        Args:
            db: 数据库会话
            user_id: 用户id
            page: 页码
            page_size: 页数
            sort_by: 排列规则
            sort_order:查询参数
            db: 数据库会话

        Returns:
            QueryHistoryListResponse: 查询历史列表响应
        """
        try:
            # 调用DAO层获取历史列表
            result = await HistoryDAO.fetch_history_list(
                db,
                user_id=user_id,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order
            )

            # 构建响应对象
            response = QueryHistoryListResponse(
                items=result['items'],
                total=result['total'],
                page=page,
                pageSize=page_size,
            )

            return response
        except Exception as e:
            logger.error(f"获取查询历史列表出错: {e}")
            raise

    async def get_history_detail(self, db: AsyncSession, history_id: int) -> QueryHistoryDetailResponse:
        """
        获取查询历史详情

        Args:
            db:数据库会话
            history_id: 历史记录ID

        Returns:
            QueryHistoryDetailResponse: 历史详情响应
        """
        try:
            # 调用DAO层获取历史详情
            history = await HistoryDAO.get_history_by_id(db,history_id)

            if not history:
                raise ValueError(f"历史记录不存在: {history_id}")

            # 获取相关的相似股票结果
            results = await ResultDAO.get_results_by_history_id(db,history_id)

            # 构建响应对象
            response = QueryHistoryDetailResponse(
                id=history['id'],
                stock_code=history['stock_code'],
                stock_name=history['stock_name'],
                query_time=history['query_time'],
                start_date=history['start_date'],
                end_date=history['end_date'],
                indicators=history['indicators'],
                method=history['method'],
                compare_scope=history['compare_scope'],
                similar_count=history['similar_count'],
            )

            return response
        except Exception as e:
            logger.error(f"获取查询历史详情出错: {e}")
            raise

    async def delete_history(self,db: AsyncSession, history_id: int) -> bool:
        """
        删除查询历史记录

        Args:
            db:数据库会话
            history_id: 历史记录ID

        Returns:
            bool: 是否成功
        """
        try:
            # 先删除关联的结果记录
            await ResultDAO.delete_by_history_id(db,history_id)

            # 删除历史记录
            success = await HistoryDAO.delete_history(history_id)

            return success
        except Exception as e:
            logger.error(f"删除查询历史出错: {e}")
            raise

    async def delete_history_batch(self,db: AsyncSession,history_ids: List[int]) -> Dict[str, int]:
        """
        批量删除查询历史记录

        Args:
            db:数据库会话
            history_ids: 历史记录ID列表

        Returns:
            Dict: 删除结果
        """
        try:
            # 先删除关联的结果记录
            await ResultDAO.delete_by_history_ids(db,history_ids)

            # 批量删除历史记录
            deleted_count = await HistoryDAO.delete_history_batch(db,history_ids)

            return {
                'deletedCount': deleted_count,
                'requestedCount': len(history_ids)
            }
        except Exception as e:
            logger.error(f"批量删除查询历史出错: {e}")
            raise

    async def search_history(self, db: AsyncSession,keyword: str) -> QueryHistorySearchResponse:
        """
        搜索查询历史（支持模糊搜索）

        Args:
            db:数据库会话
            keyword: 搜索关键词

        Returns:
            QueryHistorySearchResponse: 搜索结果响应
        """
        try:
            # 调用DAO层搜索历史
            results = await HistoryDAO.search_history(db,keyword)

            # 构建响应对象
            response = QueryHistorySearchResponse(
                items=results,
                keyword=keyword,
                total=len(results)
            )

            return response
        except Exception as e:
            logger.error(f"搜索查询历史出错: {e}")
            raise

    async def get_similar_stocks_detail(self,db: AsyncSession, history_id: int) -> SimilarStocksDetailResponse:
        """
        获取相似股票详细结果

        Args:
            db:数据库会话
            history_id: 历史记录ID

        Returns:
            SimilarStocksDetailResponse: 相似股票详情响应
        """
        try:
            # 获取历史记录基本信息
            history = await HistoryDAO.get_history_by_id(db,history_id)

            if not history:
                raise ValueError(f"历史记录不存在: {history_id}")

            # 获取相似股票结果
            results = await ResultDAO.get_results_by_history_id(history_id)

            # 构建响应对象
            response = SimilarStocksDetailResponse(
                historyId=history_id,
                stock_code=history['stock_code'],
                stock_name=history['stock_name'],
                queryTime=history['query_time'],
                results=results
            )

            return response
        except Exception as e:
            logger.error(f"获取相似股票详情出错: {e}")
            raise

    async def export_history(self,db: AsyncSession, request: ExportHistoryRequest) -> str:
        """
        导出查询历史数据

        Args:
            db:数据库会话
            request: 导出请求参数

        Returns:
            str: 文件路径
        """
        try:
            # 获取数据
            history_data = await HistoryDAO.fetch_history_list(
                page=1,
                page_size=10000,  # 导出时不分页
            )

            # 转换为DataFrame
            df_data = []
            for history in history_data['items']:
                # 获取该历史记录的所有结果
                results = await ResultDAO.get_results_by_history_id(db,history['id'])

                for result in results:
                    df_data.append({
                        '查询时间': history['query_time'],
                        '股票代码': history['stock_code'],
                        '股票名称': history['stock_name'],
                        '时间段': f"{history['start_date']} 至 {history['end_date']}",
                        '指标': ','.join(history.get('indicators', [])),
                        '计算方法': history.get('method'),
                        '相似股票代码': result['stock_code'],
                        '相似股票名称': result['stock_name'],
                        '相似度': result['similarity'],
                        '收益率': result['return_rate']
                    })

            df = pd.DataFrame(df_data)

            # 生成Excel文件
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='查询历史', index=False)

            # 保存文件
            filename = f"query_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path = await self._save_export_file(output.getvalue(), filename)

            return file_path
        except Exception as e:
            logger.error(f"导出查询历史出错: {e}")
            raise

    async def get_history_statistics(self, db: AsyncSession,request: HistoryStatisticsRequest) -> QueryHistoryStatisticsResponse:
        """
        获取查询历史统计信息

        Args:
            db: 数据库会话
            request: 统计请求参数

        Returns:
            QueryHistoryStatisticsResponse: 统计信息响应
        """
        try:
            # 调用DAO层获取统计信息
            statistics = await HistoryDAO.get_history_statistics(
                db,
                start_date=request.startDate,
                end_date=request.endDate
            )

            # 获取热门股票
            hot_stocks = await HistoryDAO.get_hot_stocks(
                db,
                start_date=request.startDate,
                end_date=request.endDate,
                limit=10
            )

            # 构建响应对象
            response = QueryHistoryStatisticsResponse(
                totalCount=statistics['total_count'],
                dateRange=f"{request.startDate or '开始'} 至 {request.endDate or '现在'}",
                hotStocks=hot_stocks,
                dailyCounts=statistics.get('daily_counts', []),
                methodDistribution=statistics.get('method_distribution', {})
            )

            return response
        except Exception as e:
            logger.error(f"获取查询历史统计出错: {e}")
            raise

    async def get_recent_history(self, db: AsyncSession,limit: int = 10) -> RecentQueryHistoryResponse:
        """
        获取最近查询记录

        Args:
            db: 数据库会话
            limit: 记录数量

        Returns:
            RecentQueryHistoryResponse: 最近查询记录响应
        """
        try:
            # 调用DAO层获取最近记录
            recent_history = await HistoryDAO.get_recent_history(db,limit)

            # 构建响应对象
            response = RecentQueryHistoryResponse(
                items=recent_history,
                limit=limit
            )

            return response
        except Exception as e:
            logger.error(f"获取最近查询记录出错: {e}")
            raise

    async def clear_all_history(self, db: AsyncSession) -> Dict[str, Any]:
        """
        清空所有查询历史

        Returns:
            Dict: 清空结果
        """
        try:
            # 获取总数
            statistics = await HistoryDAO.get_history_statistics(db)
            total_count = statistics.get('total_count', 0)

            # 清空所有记录
            await ResultDAO.delete_all(db)
            await HistoryDAO.delete_all(db)

            return {
                'clearedCount': total_count,
                'success': True
            }
        except Exception as e:
            logger.error(f"清空所有查询历史出错: {e}")
            raise

    async def _save_export_file(self, file_data: bytes, filename: str) -> str:
        """
        保存导出文件

        Args:
            file_data: 文件数据
            filename: 文件名

        Returns:
            str: 文件路径
        """
        # 这里应该实现实际的文件保存逻辑
        # 可能保存到本地文件系统、对象存储等
        file_path = f"/exports/{filename}"
        # 实际保存逻辑...
        return file_path