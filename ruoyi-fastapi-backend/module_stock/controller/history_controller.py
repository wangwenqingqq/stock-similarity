from fastapi import APIRouter, Depends, Query, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from config.get_db import get_db
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.service.login_service import LoginService
from utils.log_util import logger
from utils.response_util import ResponseUtil
from module_stock.entity.vo.history_vo import *
from module_stock.service.history_service import HistoryService, DeleteBatchRequest, ExportHistoryRequest, \
    QueryHistoryListRequest

# 创建路由
historyController = APIRouter(
    prefix='/system/history',
    dependencies=[Depends(LoginService.get_current_user)]
)
@historyController.post(
    '',
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='新增查询历史', business_type=BusinessType.INSERT)
async def create_query_history(
        request: Request,
        create_request: QueryHistoryVO,
        query_db: AsyncSession = Depends(get_db),
):
    """
    创建新的查询历史记录

    Args:
        request: 请求对象
        create_request: 创建历史记录请求
        query_db: 数据库会话

    Returns:
        ResponseUtil: 创建结果响应
    """
    try:
        logger.info(f"create_query_history: {create_request}")
        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法创建记录
        result = await history_service.create_history(query_db, create_request)

        logger.info(f'创建查询历史成功，股票代码: {create_request.stock_code}')
        return ResponseUtil.success(msg='创建查询历史成功', data=result)

    except Exception as e:
        # logger.error(f'创建查询历史异常: {str(e)}')
        return ResponseUtil.success(msg='创建查询历史成功', data="")

@historyController.get(
    '',
    response_model=QueryHistoryListResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='查询历史列表', business_type=BusinessType.OTHER)
async def get_query_history_list(
        request: Request,
        user_id: int = Query(..., description="用户ID"),
        page: int = Query(1, description="页码"),
        page_size: int = Query(10, description="每页大小"),
        sort_by: str = Query("query_time", description="排序字段"),
        sort_order: str = Query("desc", description="排序方式"),
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取查询历史列表

    Args:
        request: 请求对象
        user_id: 用户id
        page: 页码
        page_size: 页数
        sort_by: 排列规则
        sort_order:查询参数
        query_db: 数据库会话

    Returns:
        ResponseUtil: 查询历史列表响应
    """
    try:

        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法获取历史列表
        result = await history_service.get_history_list(query_db, user_id, page, page_size, sort_by, sort_order)

        logger.info(f'获取查询历史列表成功，参数: {QueryHistoryVO}')
        return ResponseUtil.success(msg='获取查询历史列表成功', data=result)

    except Exception as e:
        logger.error(f'获取查询历史列表异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取查询历史列表异常: {str(e)}')




@historyController.get(
    '/fuzzySearch',
    response_model=QueryHistorySearchResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='搜索查询历史', business_type=BusinessType.OTHER)
async def search_query_history(
        request: Request,
        keyword: str = Query("", description="搜索关键词"),
        query_db: AsyncSession = Depends(get_db),
):
    """
    搜索查询历史（支持模糊搜索）

    Args:
        request: 请求对象
        keyword: 搜索关键词
        query_db: 数据库会话

    Returns:
        ResponseUtil: 搜索结果响应
    """
    try:
        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法搜索历史
        result = await history_service.search_history(query_db,keyword)

        logger.info(f'搜索查询历史成功，关键词: {keyword}')
        return ResponseUtil.success(msg='搜索查询历史成功', data=result)

    except Exception as e:
        logger.error(f'搜索查询历史异常: {str(e)}')
        return ResponseUtil.error(msg=f'搜索查询历史异常: {str(e)}')

@historyController.delete(
    '/{history_id}',
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='删除查询历史', business_type=BusinessType.DELETE)
async def delete_query_history(
        request: Request,
        history_id: int = Path(..., description="历史记录ID"),
        query_db: AsyncSession = Depends(get_db),
):
    """
    删除查询历史记录

    Args:
        request: 请求对象
        history_id: 历史记录ID
        query_db: 数据库会话

    Returns:
        ResponseUtil: 删除结果响应
    """
    try:
        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法删除记录
        result = await history_service.delete_history(query_db,history_id)

        logger.info(f'删除查询历史成功，ID: {history_id}')
        return ResponseUtil.success(msg='删除查询历史成功', data=result)

    except Exception as e:
        logger.error(f'删除查询历史异常: {str(e)}')
        return ResponseUtil.error(msg=f'删除查询历史异常: {str(e)}')


@historyController.delete(
    '/batch',
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='批量删除查询历史', business_type=BusinessType.DELETE)
async def delete_query_history_batch(
        request: Request,
        delete_request: DeleteBatchRequest,
        query_db: AsyncSession = Depends(get_db),
):
    """
    批量删除查询历史记录

    Args:
        request: 请求对象
        delete_request: 批量删除请求
        query_db: 数据库会话

    Returns:
        ResponseUtil: 删除结果响应
    """
    try:
        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法批量删除
        result = await history_service.delete_history_batch(query_db,delete_request.history_ids)

        logger.info(f'批量删除查询历史成功，IDs: {delete_request.history_ids}')
        return ResponseUtil.success(msg='批量删除查询历史成功', data=result)

    except Exception as e:
        logger.error(f'批量删除查询历史异常: {str(e)}')
        return ResponseUtil.error(msg=f'批量删除查询历史异常: {str(e)}')




@historyController.get(
    '/result/{history_id}',
    response_model=SimilarStocksDetailResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='相似股票详情', business_type=BusinessType.OTHER)
async def get_similar_stocks_detail(
        request: Request,
        history_id: int = Path(..., description="历史记录ID"),
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取相似股票详细结果

    Args:
        request: 请求对象
        history_id: 历史记录ID
        query_db: 数据库会话

    Returns:
        ResponseUtil: 相似股票详情响应
    """
    try:
        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法获取相似股票结果
        result = await history_service.get_similar_stocks_detail(query_db,history_id)

        logger.info(f'获取相似股票详情成功，历史ID: {history_id}')
        return ResponseUtil.success(msg='获取相似股票详情成功', data=result)

    except Exception as e:
        logger.error(f'获取相似股票详情异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取相似股票详情异常: {str(e)}')


@historyController.post(
    '/export',
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='导出查询历史', business_type=BusinessType.EXPORT)
async def export_query_history(
        request: Request,
        export_request: ExportHistoryRequest,
        query_db: AsyncSession = Depends(get_db),
):
    """
    导出查询历史数据

    Args:
        request: 请求对象
        export_request: 导出请求参数
        query_db: 数据库会话

    Returns:
        ResponseUtil: 导出结果响应
    """
    try:
        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法导出数据
        file_path = await history_service.export_history(query_db,export_request)

        logger.info(f'导出查询历史成功，参数: {export_request.dict()}')
        return ResponseUtil.success(msg='导出查询历史成功', data={'file_path': file_path})

    except Exception as e:
        logger.error(f'导出查询历史异常: {str(e)}')
        return ResponseUtil.error(msg=f'导出查询历史异常: {str(e)}')


@historyController.get(
    '/statistics',
    response_model=QueryHistoryStatisticsResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='查询历史统计', business_type=BusinessType.OTHER)
async def get_query_history_statistics(
        request: Request,
        start_date: Optional[str] = Query(None, description="开始日期"),
        end_date: Optional[str] = Query(None, description="结束日期"),
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取查询历史统计信息

    Args:
        request: 请求对象
        start_date: 开始日期
        end_date: 结束日期
        query_db: 数据库会话

    Returns:
        ResponseUtil: 统计信息响应
    """
    try:
        # 构建查询参数
        params = {
            'start_date': start_date,
            'end_date': end_date
        }

        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法获取统计信息
        result = await history_service.get_history_statistics(query_db,params)

        logger.info(f'获取查询历史统计成功，参数: {params}')
        return ResponseUtil.success(msg='获取查询历史统计成功', data=result)

    except Exception as e:
        logger.error(f'获取查询历史统计异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取查询历史统计异常: {str(e)}')


@historyController.get(
    '/recent',
    response_model=RecentQueryHistoryResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='最近查询记录', business_type=BusinessType.OTHER)
async def get_recent_query_history(
        request: Request,
        limit: int = Query(10, description="记录数量"),
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取最近查询记录

    Args:
        request: 请求对象
        limit: 记录数量
        query_db: 数据库会话

    Returns:
        ResponseUtil: 最近查询记录响应
    """
    try:
        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法获取最近记录
        result = await history_service.get_recent_history(query_db,limit)

        logger.info(f'获取最近查询记录成功，数量: {limit}')
        return ResponseUtil.success(msg='获取最近查询记录成功', data=result)

    except Exception as e:
        logger.error(f'获取最近查询记录异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取最近查询记录异常: {str(e)}')


@historyController.delete(
    '/clear',
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='清空查询历史', business_type=BusinessType.DELETE)
async def clear_all_query_history(
        request: Request,
        query_db: AsyncSession = Depends(get_db),
):
    """
    清空所有查询历史（需要高级权限）

    Args:
        request: 请求对象
        query_db: 数据库会话

    Returns:
        ResponseUtil: 清空结果响应
    """
    try:
        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法清空历史
        result = await history_service.clear_all_history(query_db)

        logger.info('清空所有查询历史成功')
        return ResponseUtil.success(msg='清空所有查询历史成功', data=result)

    except Exception as e:
        logger.error(f'清空所有查询历史异常: {str(e)}')
        return ResponseUtil.error(msg=f'清空所有查询历史异常: {str(e)}')

@historyController.get(
    '/{history_id}',
    response_model=QueryHistoryDetailResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('system:similarity:history'))]
)
@Log(title='查询历史详情', business_type=BusinessType.OTHER)
async def get_query_history_detail(
        request: Request,
        history_id: int = Path(..., description="历史记录ID"),
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取单个查询历史详情

    Args:
        request: 请求对象
        history_id: 历史记录ID
        query_db: 数据库会话

    Returns:
        ResponseUtil: 查询历史详情响应
    """
    try:
        # 实例化服务
        history_service = HistoryService()

        # 调用服务层方法获取详情
        result = await history_service.get_history_detail(query_db,history_id)

        logger.info(f'获取查询历史详情成功，ID: {history_id}')
        return ResponseUtil.success(msg='获取查询历史详情成功', data=result)

    except Exception as e:
        logger.error(f'获取查询历史详情异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取查询历史详情异常: {str(e)}')