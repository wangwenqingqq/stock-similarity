from fastapi import APIRouter, Depends, Request, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from config.get_db import get_db
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.service.login_service import LoginService
from utils.log_util import logger
from utils.response_util import ResponseUtil
from module_stock.service.kLine_service import KLineService, StockListRequest

# 创建路由
klineController = APIRouter(
    prefix='/system/return',
    dependencies=[Depends(LoginService.get_current_user)]
)


@klineController.get(
    '/list',
    dependencies=[Depends(CheckUserInterfaceAuth('stock:kline:list'))]
)
@Log(title='股票列表查询', business_type=BusinessType.OTHER)
async def fetch_stock_list(
        request: Request,
        page: int = Query(1, description="页码"),
        page_size: int = Query(20, description="每页大小"),
        sort_by: str = Query("seven_day_return", description="排序字段"),
        sort_order: str = Query("desc", description="排序方式"),
        keyword: Optional[str] = Query(None, description="搜索关键词"),
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取股票列表，支持分页、排序和搜索

    Args:
        request: 请求对象
        page: 页码
        page_size: 每页大小
        sort_by: 排序字段
        sort_order: 排序方式
        keyword: 搜索关键词
        query_db: 数据库会话

    Returns:
        ResponseUtil: 股票列表响应
    """
    try:
        # 实例化服务
        kline_service = KLineService()

        # 构建请求参数
        list_request = StockListRequest(
            page=page,
            pageSize=page_size,
            sortBy=sort_by,
            sortOrder=sort_order,
            keyword=keyword
        )

        # 调用服务层方法获取股票列表
        response = await kline_service.get_stock_list(list_request)

        logger.info('获取股票列表成功')
        return ResponseUtil.success(msg='获取股票列表成功', data=response)

    except Exception as e:
        logger.error(f'获取股票列表异常: {str(e)[:500]}')
        return ResponseUtil.error(msg=f'获取股票列表异常: {str(e)}')


@klineController.get(
    '/kline/{stock_code}',
    dependencies=[Depends(CheckUserInterfaceAuth('stock:kline:data'))]
)
@Log(title='K线图数据查询', business_type=BusinessType.OTHER)
async def load_kline_data(
        request: Request,
        stock_code: str,
        time_range: str = Query("day", description="时间范围: day, week, month"),
        data_type: Optional[str] = Query(None, description="数据类型，若为'close'则只返回收盘价"),
        query_db: AsyncSession = Depends(get_db),
):
    """
    加载特定股票的K线图数据

    Args:
        request: 请求对象
        stock_code: 股票代码
        time_range: 时间范围
        data_type: 数据类型
        query_db: 数据库会话

    Returns:
        ResponseUtil: K线图数据响应
    """
    try:
        # 实例化服务
        kline_service = KLineService()

        # 调用服务层方法获取K线图数据
        response = await kline_service.get_kline_data(
            stock_code=stock_code,
            time_range=time_range,
            data_type=data_type
        )
        print("response in controller",response)
        logger.info(f'获取股票 {stock_code} K线图数据成功')
        return ResponseUtil.success(msg='获取K线图数据成功', data=response)

    except Exception as e:
        logger.error(f'获取K线图数据异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取K线图数据异常: {str(e)}')


@klineController.get(
    '/similar/{stock_code}',
    dependencies=[Depends(CheckUserInterfaceAuth('stock:kline:similar'))]
)
@Log(title='相似股票查询', business_type=BusinessType.OTHER)
async def find_similar_stocks(
        request: Request,
        stock_code: str,
        query_db: AsyncSession = Depends(get_db),
):
    """
    查找与特定股票相似的股票

    Args:
        request: 请求对象
        stock_code: 股票代码
        query_db: 数据库会话

    Returns:
        ResponseUtil: 相似股票列表响应
    """
    try:
        # 实例化服务
        kline_service = KLineService()

        # 调用服务层方法查找相似股票
        response = await kline_service.find_similar_stocks(stock_code)

        logger.info(f'查找与股票 {stock_code} 相似的股票成功')
        return ResponseUtil.success(msg='查找相似股票成功', data=response)

    except Exception as e:
        logger.error(f'查找相似股票异常: {str(e)}')
        return ResponseUtil.error(msg=f'查找相似股票异常: {str(e)}')


# @klineController.get(
#     '/compare',
#     dependencies=[Depends(CheckUserInterfaceAuth('stock:kline:compare'))]
# )
# @Log(title='股票性能比较', business_type=BusinessType.OTHER)
# async def compare_stocks_performance(
#         request: Request,
#         base_stock_code: str = Query(..., description="基准股票代码"),
#         compare_stock_codes: List[str] = Query(..., description="比较股票代码列表"),
#         query_db: AsyncSession = Depends(get_db),
# ):
#     """
#     比较多只股票的性能表现
#
#     Args:
#         request: 请求对象
#         base_stock_code: 基准股票代码
#         compare_stock_codes: 比较股票代码列表
#         query_db: 数据库会话
#
#     Returns:
#         ResponseUtil: 性能比较数据响应
#     """
#     try:
#         # 实例化服务
#         kline_service = KLineService()
#
#         # 调用服务层方法比较股票性能
#         response = await kline_service.compare_stocks_performance(
#             base_stock_code=base_stock_code,
#             compare_stock_codes=compare_stock_codes
#         )
#
#         logger.info('股票性能比较成功')
#         return ResponseUtil.success(msg='股票性能比较成功', data=response)
#
#     except Exception as e:
#         logger.error(f'股票性能比较异常: {str(e)}')
#         return ResponseUtil.error(msg=f'股票性能比较异常: {str(e)}')


# @klineController.get(
#     '/technical/{stock_code}',
#     dependencies=[Depends(CheckUserInterfaceAuth('stock:kline:technical'))]
# )
# @Log(title='股票技术指标分析', business_type=BusinessType.OTHER)
# async def analyze_technical_indicators(
#         request: Request,
#         stock_code: str,
#         time_range: str = Query("day", description="时间范围: day, week, month"),
#         query_db: AsyncSession = Depends(get_db),
# ):
#     """
#     分析股票技术指标，包括RSI、MACD、布林带等
#
#     Args:
#         request: 请求对象
#         stock_code: 股票代码
#         time_range: 时间范围
#         query_db: 数据库会话
#
#     Returns:
#         ResponseUtil: 技术指标分析结果响应
#     """
#     try:
#         # 实例化服务
#         kline_service = KLineService()
#
#         # 调用服务层方法分析技术指标
#         response = await kline_service.analyze_technical_indicators(
#             stock_code=stock_code,
#             time_range=time_range
#         )
#
#         logger.info(f'股票 {stock_code} 技术指标分析成功')
#         return ResponseUtil.success(msg='技术指标分析成功', data=response)
#
#     except Exception as e:
#         logger.error(f'技术指标分析异常: {str(e)}')
#         return ResponseUtil.error(msg=f'技术指标分析异常: {str(e)}')