from datetime import datetime

from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from config.get_db import get_db
from config.get_clickhouse import get_clickhouse_client
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.login_service import LoginService
from module_stock.service.stock_service import StockService
from module_stock.entity.vo.stock_vo import StockModel, StockPageQueryModel, DeleteStockModel
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil

stockController = APIRouter(prefix='/api/system/stockInfo', dependencies=[Depends(LoginService.get_current_user)])
#add
@stockController.get(
    '/list', response_model=PageResponseModel, dependencies=[Depends(CheckUserInterfaceAuth('stock:list'))]
)
async def get_stock_list(
    request: Request,
    stock_page_query: StockPageQueryModel = Depends(StockPageQueryModel.as_query),
    query_db: AsyncSession = Depends(get_db),
):
    """
    获取股票信息列表（分页）
    """
    stock_page_query_result = await StockService.get_stock_list_services(
        query_db, stock_page_query, is_page=True
    )
    logger.info('获取股票信息列表成功')
    return ResponseUtil.success(model_content=stock_page_query_result)

@stockController.post('', dependencies=[Depends(CheckUserInterfaceAuth('stock:add'))])
@Log(title='股票信息管理', business_type=BusinessType.INSERT)
async def add_stock(
    request: Request,
    add_stock: StockModel,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    添加股票信息
    """
    add_stock.create_by = current_user.user.user_name
    add_stock.create_time = datetime.now()
    add_stock.update_by = current_user.user.user_name
    add_stock.update_time = datetime.now()
    add_stock_result = await StockService.add_stock_services(query_db, add_stock)
    logger.info(add_stock_result.message)
    return ResponseUtil.success(msg=add_stock_result.message)

@stockController.put('', dependencies=[Depends(CheckUserInterfaceAuth('stock:edit'))])
@Log(title='股票信息管理', business_type=BusinessType.UPDATE)
async def edit_stock(
    request: Request,
    edit_stock: StockModel,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    编辑股票信息
    """
    edit_stock.update_by = current_user.user.user_name
    edit_stock.update_time = datetime.now()
    edit_stock_result = await StockService.edit_stock_services(query_db, edit_stock)
    logger.info(edit_stock_result.message)
    return ResponseUtil.success(msg=edit_stock_result.message)

@stockController.delete('/{stock_ids}', dependencies=[Depends(CheckUserInterfaceAuth('stock:remove'))])
@Log(title='股票信息管理', business_type=BusinessType.DELETE)
async def delete_stock(
    request: Request,
    stock_ids: str,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    删除股票信息
    """
    delete_stock = DeleteStockModel(stockIds=stock_ids)
    delete_stock_result = await StockService.delete_stock_services(query_db, delete_stock)
    logger.info(delete_stock_result.message)
    return ResponseUtil.success(msg=delete_stock_result.message)

@stockController.get(
    '/{stock_id}', response_model=StockModel, dependencies=[Depends(CheckUserInterfaceAuth('stock:query'))]
)
async def query_detail_stock(
    request: Request,
    stock_id: int,
    query_db: AsyncSession = Depends(get_db),
):
    """
    查询股票信息详情
    """
    stock_detail_result = await StockService.stock_detail_services(query_db, stock_id)
    logger.info(f'获取stock_id为{stock_id}的信息成功')
    return ResponseUtil.success(data=stock_detail_result)

@stockController.post('/export', dependencies=[Depends(CheckUserInterfaceAuth('stock:export'))])
@Log(title='股票信息管理', business_type=BusinessType.EXPORT)
async def export_stock_list(
    request: Request,
    stock_page_query: StockPageQueryModel = Form(),
    query_db: AsyncSession = Depends(get_db),
):
    """
    导出股票信息列表
    """
    stock_query_result = await StockService.get_stock_list_services(
        query_db, stock_page_query, is_page=False
    )
    stock_export_result = await StockService.export_stock_list_services(stock_query_result)
    logger.info('导出成功')
    return ResponseUtil.streaming(data=bytes2file_response(stock_export_result))