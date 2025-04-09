from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from pydantic_validation_decorator import ValidateFields
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from config.get_db import get_db
from entity.vo.stock_vo import StockPageQueryModel
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.login_service import LoginService
from module_stock.service.stock_service import StockService
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil

stockController = APIRouter(prefix='/system/stockInfo', dependencies=[Depends(LoginService.get_current_user)])


@stockController.get(
    '/list', response_model=PageResponseModel, dependencies=[Depends(CheckUserInterfaceAuth('stock:info:list'))]
)
@Log(title='股票信息', business_type=BusinessType.OTHER)
async def get_stock_info_list(
        request: Request,
        stock_page_query: StockPageQueryModel = Depends(StockPageQueryModel.as_query),
        query_db: AsyncSession = Depends(get_db),
):
    try:
        # 获取股票列表数据
        response = await StockService.get_stock_list_services()
        print(f"CrudResponseModel结构: {response}")
        print(f"response.result类型: {type(response.result)}")
        print(f"response.result内容: {response.result}")
        # 检查服务层返回的结果
        if response.is_success:
            logger.info('获取股票信息列表成功')
            # 如果 response 是 BaseModel 类型，可以直接传给 model_content
            return ResponseUtil.success(msg='获取股票信息列表成功', data=response.result)
        else:
            logger.error(f'获取股票信息列表失败: {response.message}')
            # 使用 failure 而不是 fail
            return ResponseUtil.failure(msg=response.message)

    except Exception as e:
        logger.error(f'获取股票信息列表异常: {str(e)}')
        return ResponseUtil.error(msg=f'获取股票信息列表异常: {str(e)}')