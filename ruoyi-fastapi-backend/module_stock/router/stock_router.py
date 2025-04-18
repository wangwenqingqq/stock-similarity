from fastapi import APIRouter
from module_stock.service.stock_service import StockService
#add
stock_router = APIRouter(prefix='/api/system/stockInfo')

@stock_router.get('/list')
def get_stock_list():
    return StockService.get_stock_list_services()
