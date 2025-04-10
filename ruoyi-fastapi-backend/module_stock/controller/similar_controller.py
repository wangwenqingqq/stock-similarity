from datetime import datetime
import numpy as np
from fastapi import APIRouter, Depends, Form, Request
from fastdtw import fastdtw
from pydantic_validation_decorator import ValidateFields
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from config.get_db import get_db
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.login_service import LoginService
from utils.log_util import logger
from utils.response_util import ResponseUtil
from module_stock.dao.similar_dao import SimilarDao
from module_stock.entity.vo.similar_vo import *
from module_stock.service.similar_service import StockSimilarityService

# 创建路由
similarController = APIRouter(
    prefix='/system/stockSimilarity',
    dependencies=[Depends(LoginService.get_current_user)]
)


@similarController.post(
    '/calculate',
    response_model=StockSimilarityResponse,
    dependencies=[Depends(CheckUserInterfaceAuth('stock:similarity:calculate'))]
)
@Log(title='股票相似性计算', business_type=BusinessType.OTHER)
async def calculate_stock_similarity(
        request: Request,
        similarity_request: StockSimilarityRequest,
        query_db: AsyncSession = Depends(get_db),
):
    """
    计算股票相似性

    Args:
        request: 请求对象
        similarity_request: 相似性计算请求
        query_db: 数据库会话

    Returns:
        ResponseUtil: 计算结果响应
    """
    try:
        # 实例化服务
        similarity_service = StockSimilarityService()

        # 调用服务层方法计算相似性
        response = similarity_service.calculate_similarity(similarity_request)

        logger.info('股票相似性计算成功')
        return ResponseUtil.success(msg='股票相似性计算成功', data=response)

    except Exception as e:
        logger.error(f'股票相似性计算异常: {str(e)}')
        return ResponseUtil.error(msg=f'股票相似性计算异常: {str(e)}')


@similarController.get(
    '/methods',
    dependencies=[Depends(CheckUserInterfaceAuth('stock:similarity:methods'))]
)
@Log(title='获取相似性计算方法', business_type=BusinessType.OTHER)
async def get_similarity_methods(
        request: Request,
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取可用的相似性计算方法

    Args:
        request: 请求对象
        query_db: 数据库会话

    Returns:
        ResponseUtil: 计算方法列表
    """
    try:
        # 返回支持的相似性计算方法
        methods = [
            {"code": "dtw", "name": "动态时间规整(DTW)",
             "description": "处理时间序列数据的算法，允许比较不同长度或速度的时间序列"},
            {"code": "pearson", "name": "皮尔逊相关系数", "description": "衡量两个变量之间线性相关程度的指标"},
            {"code": "euclidean", "name": "欧氏距离", "description": "计算两个点之间的直线距离"}
        ]

        logger.info('获取相似性计算方法成功')
        return ResponseUtil.success(msg='获取相似性计算方法成功', data=methods)

    except Exception as e:
        logger.error(f'获取相似性计算方法异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取相似性计算方法异常: {str(e)}')


@similarController.get(
    '/indicators',
    dependencies=[Depends(CheckUserInterfaceAuth('stock:similarity:indicators'))]
)
@Log(title='获取相似性计算指标', business_type=BusinessType.OTHER)
async def get_similarity_indicators(
        request: Request,
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取可用于相似性计算的指标

    Args:
        request: 请求对象
        query_db: 数据库会话

    Returns:
        ResponseUtil: 指标列表
    """
    try:
        # 返回支持的相似性计算指标
        indicators = [
            {"code": "close", "name": "收盘价", "description": "股票当日收盘价"},
            {"code": "high", "name": "最高价", "description": "股票当日最高价"},
            {"code": "low", "name": "最低价", "description": "股票当日最低价"},
            {"code": "turnover", "name": "换手率", "description": "股票当日成交量占流通股本的比例"}
        ]

        logger.info('获取相似性计算指标成功')
        return ResponseUtil.success(msg='获取相似性计算指标成功', data=indicators)

    except Exception as e:
        logger.error(f'获取相似性计算指标异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取相似性计算指标异常: {str(e)}')


@similarController.get(
    '/performanceComparison',
    dependencies=[Depends(CheckUserInterfaceAuth('stock:similarity:performance'))]
)
@Log(title='获取性能比较数据', business_type=BusinessType.OTHER)
async def get_performance_comparison(
        request: Request,
        base_stock_code: str,
        similar_stock_codes: str,
        start_date: str,
        end_date: str,
        query_db: AsyncSession = Depends(get_db),
):
    """
    获取基准股票与相似股票的性能比较数据

    Args:
        request: 请求对象
        base_stock_code: 基准股票代码
        similar_stock_codes: 相似股票代码列表(逗号分隔)
        start_date: 开始日期
        end_date: 结束日期
        query_db: 数据库会话

    Returns:
        ResponseUtil: 性能比较数据
    """
    try:
        # 实例化服务
        similarity_service = StockSimilarityService()

        # 解析相似股票代码列表
        similar_codes = similar_stock_codes.split(',')

        # 调用服务层方法获取性能比较数据
        performance_data = similarity_service._get_performance_comparison(
            base_stock_code,
            similar_codes,
            start_date,
            end_date
        )

        logger.info('获取性能比较数据成功')
        return ResponseUtil.success(msg='获取性能比较数据成功', data=performance_data)

    except Exception as e:
        logger.error(f'获取性能比较数据异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取性能比较数据异常: {str(e)}')


@similarController.post(
    '/llmAnalysis',
    dependencies=[Depends(CheckUserInterfaceAuth('stock:similarity:llm'))]
)
@Log(title='生成LLM分析', business_type=BusinessType.OTHER)
async def generate_llm_analysis(
        request: Request,
        base_stock_code: str = Form(...),
        similar_stocks: str = Form(...),
        indicators: str = Form(...),
        query_db: AsyncSession = Depends(get_db),
):
    """
    为股票相似性结果生成LLM分析

    Args:
        request: 请求对象
        base_stock_code: 基准股票代码
        similar_stocks: JSON格式的相似股票列表
        indicators: 使用的指标列表(逗号分隔)
        query_db: 数据库会话

    Returns:
        ResponseUtil: LLM分析结果
    """
    try:
        import json

        # 实例化服务
        similarity_service = StockSimilarityService()

        # 解析相似股票列表和指标
        similar_stocks_list = json.loads(similar_stocks)
        indicators_list = indicators.split(',')

        # 调用服务层方法生成LLM分析
        analysis = similarity_service._generate_llm_analysis(
            base_stock_code,
            similar_stocks_list,
            indicators_list
        )

        logger.info('生成LLM分析成功')
        return ResponseUtil.success(msg='生成LLM分析成功', data={"analysis": analysis})

    except Exception as e:
        logger.error(f'生成LLM分析异常: {str(e)}')
        return ResponseUtil.error(msg=f'生成LLM分析异常: {str(e)}')