from module_stock.dao.stock_dao import StockDao
from module_admin.entity.vo.common_vo import CrudResponseModel

class StockService:
    @classmethod
    def get_stock_list_services(cls):
        try:
            stock_list = StockDao.get_stock_list()
            return CrudResponseModel(is_success=True, message='获取股票信息成功', data=stock_list)
        except Exception as e:
            return CrudResponseModel(is_success=False, message=f'获取股票信息失败，详细错误信息：{str(e)}')