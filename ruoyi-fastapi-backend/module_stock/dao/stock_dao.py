from clickhouse_driver import Client
from module_stock.entity.vo.stock_vo import StockModel

# Clickhouse配置
CK_HOST = '10.20.173.3'
CK_PORT = 8123
CK_USERNAME = 'default'
CK_PASSWORD = '123456'

class StockDao:
    #add
    @classmethod
    def get_stock_list(cls):
        client = Client(host=CK_HOST, port=CK_PORT, user=CK_USERNAME, password=CK_PASSWORD)
        query = "SELECT code, open, close, high, low, ycp, vol, timestamps FROM ods_stock.ll_stock_daily_sharing"
        result = client.execute(query)
        stock_list = []
        for row in result:
            stock = StockModel(
                code=row[0],
                open=row[1],
                close=row[2],
                high=row[3],
                low=row[4],
                ycp=row[5],
                vol=row[6],
                timestamps=row[7]
            )
            stock_list.append(stock)
        return stock_list