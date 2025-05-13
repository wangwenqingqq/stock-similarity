from fastapi import APIRouter, Depends, Form, Request, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel, Field

from config.enums import BusinessType
from config.get_db import get_db
from entity.vo.follow_vo import StockWatchlistResponse, StockListResponse, StockSearchResponse, StockDetailResponse, \
    StockWatchlistAddResponse, StockWatchlistRemoveResponse, StockWatchlistClearResponse, StockMarketOverviewResponse
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.service.login_service import LoginService
from utils.log_util import logger
from utils.response_util import ResponseUtil
from module_stock.service.follow_service import StockFollowService
from module_stock.entity.vo.stock_vo import *

# 创建路由
followController = APIRouter(
    prefix='/system/show',
    dependencies=[Depends(LoginService.get_current_user)]
)


class StockAddToWatchlistRequest(BaseModel):
    """股票添加到关注列表请求模型"""
    stock_code: str = Field(..., description="股票代码")


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
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取股票列表，支持分页、搜索和状态筛选

    Args:
        request: 请求对象
        page: 页码，默认为1
        size: 每页数量，默认为10
        keyword: 搜索关键词，可选
        status: 股票状态，可选
        query_db: 数据库会话

    Returns:
        ResponseUtil: 股票列表响应
    """
    try:
        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法获取股票列表
        result = await follow_service.get_stock_list(page, size, keyword, status)

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
        query_db: AsyncSession = Depends(get_db),
):
    """
    根据关键词搜索股票

    Args:
        request: 请求对象
        keyword: 搜索关键词
        query_db: 数据库会话

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
    '/{code}',
    response_model=StockDetailResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('stock:detail:query'))]
)
@Log(title='获取股票详情', business_type=BusinessType.OTHER)
async def get_stock_detail(
        request: Request,
        code: str = Path(..., description="股票代码"),
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取指定股票的详细信息

    Args:
        request: 请求对象
        code: 股票代码
        query_db: 数据库会话

    Returns:
        ResponseUtil: 股票详情响应
    """
    try:
        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法获取股票详情
        result = await follow_service.get_stock_detail(code)

        if not result:
            logger.warning(f'股票不存在，代码: {code}')
            return ResponseUtil.error(msg='股票不存在')

        logger.info(f'获取股票详情成功，代码: {code}')
        return ResponseUtil.success(msg='获取股票详情成功', data=result)
    except Exception as e:
        logger.error(f'获取股票详情异常，股票代码: {code}, 错误: {str(e)}')
        return ResponseUtil.error(msg=f'获取股票详情异常: {str(e)}')


@followController.get(
    '/watchlist',
    response_model=StockWatchlistResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('stock:watchlist:query'))]
)
@Log(title='获取用户关注的股票列表', business_type=BusinessType.OTHER)
async def get_user_watchlist(
        request: Request,
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取当前登录用户关注的股票列表

    Args:
        request: 请求对象
        query_db: 数据库会话

    Returns:
        ResponseUtil: 用户关注的股票列表响应
    """
    try:
        # 获取当前用户ID
        user_id = request.state.user_info.get('userId', '')
        if not user_id:
            logger.warning('未获取到有效的用户ID')
            return ResponseUtil.error(msg='未获取到有效的用户ID')

        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法获取用户关注列表
        result = await follow_service.get_user_watchlist(user_id)

        logger.info(f'获取用户关注列表成功，用户ID: {user_id}')
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
        query_db: AsyncSession = Depends(get_db),
):
    """
    将股票添加到用户关注列表

    Args:
        request: 请求对象
        stock_request: 添加股票请求
        query_db: 数据库会话

    Returns:
        ResponseUtil: 添加结果响应
    """
    try:
        # 获取当前用户ID
        user_id = request.state.user_info.get('userId', '')
        if not user_id:
            logger.warning('未获取到有效的用户ID')
            return ResponseUtil.error(msg='未获取到有效的用户ID')

        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法添加股票到关注列表
        result = await follow_service.add_to_watchlist(user_id, stock_request.stockCode)

        if result["success"]:
            logger.info(f'添加股票到关注列表成功，用户ID: {user_id}, 股票代码: {stock_request.stockCode}')
            return ResponseUtil.success(msg=result["message"])
        else:
            logger.warning(
                f'添加股票到关注列表失败，用户ID: {user_id}, 股票代码: {stock_request.stockCode}, 原因: {result["message"]}')
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
        query_db: AsyncSession = Depends(get_db),
):
    """
    从用户关注列表中移除股票

    Args:
        request: 请求对象
        stock_code: 股票代码（路径参数）
        query_db: 数据库会话

    Returns:
        ResponseUtil: 移除结果响应
    """
    try:
        # 获取当前用户ID
        user_id = request.state.user_info.get('userId', '')
        if not user_id:
            logger.warning('未获取到有效的用户ID')
            return ResponseUtil.error(msg='未获取到有效的用户ID')

        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法从关注列表移除股票
        result = await follow_service.remove_from_watchlist(user_id, stock_code)

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
        query_db: AsyncSession = Depends(get_db),
):
    """
    清空用户关注列表

    Args:
        request: 请求对象
        query_db: 数据库会话

    Returns:
        ResponseUtil: 清空结果响应
    """
    try:
        # 获取当前用户ID
        user_id = request.state.user_info.get('userId', '')
        if not user_id:
            logger.warning('未获取到有效的用户ID')
            return ResponseUtil.error(msg='未获取到有效的用户ID')

        # 实例化服务
        follow_service = StockFollowService()

        # 调用服务层方法清空关注列表
        result = await follow_service.clear_watchlist(user_id)

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
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取市场概览，包括主要指数信息

    Args:
        request: 请求对象
        query_db: 数据库会话

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