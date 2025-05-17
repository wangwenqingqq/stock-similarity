from fastapi import APIRouter, Depends, Form, Request, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from config.get_db import get_db
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.service.login_service import LoginService
from utils.log_util import logger
from utils.response_util import ResponseUtil
from module_stock.service.follow_service import StockFollowService
from module_stock.entity.vo.follow_vo import *
# 创建路由
followController = APIRouter(
    prefix='/system/show',
    dependencies=[Depends(LoginService.get_current_user)]
)




@followController.get(
    '/list',
    response_model=StockListResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('stock:list:query'))]
)
@Log(title='获取股票列表', business_type=BusinessType.OTHER)
async def get_stock_list(
        request: Request,
        page: int = Query(1, description="页码", ge=1),
        size: int = Query(10, description="每页数量", ge=1, le=100),
        keyword: Optional[str] = Query(None, description="搜索关键词"),
        status: Optional[str] = Query(None, description="股票状态"),
        db: AsyncSession = Depends(get_db),
):
    """
    获取股票列表，支持分页、搜索和状态筛选

    Args:
        request: 请求对象
        page: 页码，默认为1
        size: 每页数量，默认为10
        keyword: 搜索关键词，可选
        status: 股票状态，可选
        db: 数据库会话

    Returns:
        ResponseUtil: 股票列表响应
    """
    try:
        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法获取股票列表
        result = await follow_service.get_stock_list(db, page, size, keyword, status)

        logger.info('获取股票列表成功')
        return ResponseUtil.success(msg='获取股票列表成功', data=result)
    except Exception as e:
        logger.error(f'获取股票列表异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取股票列表异常: {str(e)}')


@followController.get(
    '/search',
    response_model=StockSearchResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('stock:search:query'))]
)
@Log(title='搜索股票', business_type=BusinessType.OTHER)
async def search_stocks(
        request: Request,
        keyword: str = Query(..., description="搜索关键词"),
        db: AsyncSession = Depends(get_db),
):
    """
    根据关键词搜索股票

    Args:
        request: 请求对象
        keyword: 搜索关键词
        db: 数据库会话

    Returns:
        ResponseUtil: 搜索结果响应
    """
    try:
        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法搜索股票
        result = await follow_service.search_stocks(keyword)

        logger.info('搜索股票成功')
        return ResponseUtil.success(msg='搜索股票成功', data=result)
    except Exception as e:
        logger.error(f'搜索股票异常: {str(e)}')
        return ResponseUtil.error(msg=f'搜索股票异常: {str(e)}')


@followController.get(
    '/watchlist',
    response_model=StockWatchlistResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('stock:watchlist:query'))]
)
@Log(title='获取用户关注的股票列表', business_type=BusinessType.OTHER)
async def get_user_watchlist(
        request: Request,
        userId: Optional[str] = Query(None, description="用户ID"),
        db: AsyncSession = Depends(get_db),
):
    """
    获取当前登录用户关注的股票列表

    Args:
        request: 请求对象
        userId: 查询参数中的用户ID
        db: 数据库会话

    Returns:
        ResponseUtil: 用户关注的股票列表响应
    """
    try:
        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法获取用户关注列表
        result = await follow_service.get_user_watchlist(db, userId)

        logger.info(f'获取用户关注列表成功，用户ID: {userId}')
        return ResponseUtil.success(msg='获取用户关注列表成功', data=result)
    except Exception as e:
        logger.error(f'获取用户关注列表异常，错误: {str(e)}')
        return ResponseUtil.error(msg=f'获取用户关注列表异常: {str(e)}')


@followController.post(
    '/watchlist',
    response_model=StockWatchlistAddResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('stock:watchlist:add'))]
)
@Log(title='添加股票到关注列表', business_type=BusinessType.INSERT)
async def add_to_watchlist(
        request: Request,
        stock_request: StockAddToWatchlistRequest,
        db: AsyncSession = Depends(get_db),
):
    """
    将股票添加到用户关注列表

    Args:
        request: 请求对象
        stock_request: 添加股票请求
        db: 数据库会话

    Returns:
        ResponseUtil: 添加结果响应
    """
    try:
        # 优先从请求体获取用户ID，如果没有则尝试从请求状态获取
        user_id = stock_request.user_id

        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法添加股票到关注列表
        result = await follow_service.add_to_watchlist(db, user_id, stock_request.stock_code)

        if result["success"]:
            logger.info(f'添加股票到关注列表成功，用户ID: {user_id}, 股票代码: {stock_request.stock_code}')
            return ResponseUtil.success(msg=result["message"])
        else:
            logger.warning(
                f'添加股票到关注列表失败，用户ID: {user_id}, 股票代码: {stock_request.stock_code}, 原因: {result["message"]}')
            return ResponseUtil.error(msg=result["message"])
    except Exception as e:
        logger.error(f'添加股票到关注列表异常，错误: {str(e)}')
        return ResponseUtil.error(msg=f'添加股票到关注列表异常: {str(e)}')


@followController.delete(
    '/watchlist/{stock_code}',
    response_model=StockWatchlistRemoveResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('stock:watchlist:remove'))]
)
@Log(title='从关注列表中移除股票', business_type=BusinessType.DELETE)
async def remove_from_watchlist(
        request: Request,
        stock_code: str = Path(..., description="股票代码"),
        userId: Optional[str] = Query(None, description="用户ID"),
        db: AsyncSession = Depends(get_db),
):
    """
    从用户关注列表中移除股票

    Args:
        request: 请求对象
        stock_code: 股票代码（路径参数）
        user_id: 查询参数中的用户ID
        db: 数据库会话

    Returns:
        ResponseUtil: 移除结果响应
    """
    try:
        # 优先从查询参数获取用户ID，如果没有则尝试从请求状态获取
        user_id = userId

        if not user_id:
            logger.warning('未获取到有效的用户ID')
            return ResponseUtil.error(msg='未获取到有效的用户ID')

        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法从关注列表移除股票
        result = await follow_service.remove_from_watchlist(db, user_id, stock_code)

        if result["success"]:
            logger.info(f'从关注列表移除股票成功，用户ID: {user_id}, 股票代码: {stock_code}')
            return ResponseUtil.success(msg=result["message"])
        else:
            logger.warning(
                f'从关注列表移除股票失败，用户ID: {user_id}, 股票代码: {stock_code}, 原因: {result["message"]}')
            return ResponseUtil.error(msg=result["message"])
    except Exception as e:
        logger.error(f'从关注列表移除股票异常，股票代码: {stock_code}, 错误: {str(e)}')
        return ResponseUtil.error(msg=f'从关注列表移除股票异常: {str(e)}')


@followController.delete(
    '/watchlist',
    response_model=StockWatchlistClearResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('stock:watchlist:clear'))]
)
@Log(title='清空关注列表', business_type=BusinessType.CLEAN)
async def clear_watchlist(
        request: Request,
        user_id: Optional[str] = Query(None, description="用户ID"),
        db: AsyncSession = Depends(get_db),
):
    """
    清空用户关注列表

    Args:
        request: 请求对象
        user_id: 查询参数中的用户ID
        db: 数据库会话

    Returns:
        ResponseUtil: 清空结果响应
    """
    try:
        # 优先从查询参数获取用户ID，如果没有则尝试从请求状态获取
        user_id = user_id or request.state.user_info.get('userId', '') if hasattr(request.state, 'user_info') else ''

        if not user_id:
            logger.warning('未获取到有效的用户ID')
            return ResponseUtil.error(msg='未获取到有效的用户ID')

        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法清空关注列表
        result = await follow_service.clear_watchlist(db, user_id)

        if result["success"]:
            logger.info(f'清空关注列表成功，用户ID: {user_id}')
            return ResponseUtil.success(msg=result["message"])
        else:
            logger.warning(f'清空关注列表失败，用户ID: {user_id}, 原因: {result["message"]}')
            return ResponseUtil.error(msg=result["message"])
    except Exception as e:
        logger.error(f'清空关注列表异常，错误: {str(e)}')
        return ResponseUtil.error(msg=f'清空关注列表异常: {str(e)}')


@followController.get(
    '/market/overview',
    response_model=StockMarketOverviewResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('stock:market:overview'))]
)
@Log(title='获取市场概览', business_type=BusinessType.OTHER)
async def get_market_overview(
        request: Request,
        db: AsyncSession = Depends(get_db),
):
    """
    获取市场概览，包括主要指数信息

    Args:
        request: 请求对象
        db: 数据库会话

    Returns:
        ResponseUtil: 市场概览响应
    """
    try:
        # 调用服务层方法获取市场概览
        result = await StockFollowService.get_market_overview()

        logger.info('获取市场概览成功')
        return ResponseUtil.success(msg='获取市场概览成功', data=result)
    except Exception as e:
        logger.error(f'获取市场概览异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取市场概览异常: {str(e)}')