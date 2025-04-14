from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from config.get_db import get_db
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.service.login_service import LoginService
from utils.log_util import logger
from utils.response_util import ResponseUtil
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
        response = await similarity_service.calculate_similarity(similarity_request)

        logger.info('股票相似性计算成功')
        return ResponseUtil.success(msg='股票相似性计算成功', data=response)

    except Exception as e:
        logger.error(f'股票相似性计算异常: {str(e)}')
        return ResponseUtil.error(msg=f'股票相似性计算异常: {str(e)}')

