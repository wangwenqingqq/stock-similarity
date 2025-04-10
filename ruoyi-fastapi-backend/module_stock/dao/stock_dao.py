from clickhouse_driver import Client

from entity.do.stock_do import StockInfo
from config.env import ClickHouseSettings
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

settings = ClickHouseSettings()
logger = logging.getLogger(__name__)


class StockDao:
    @classmethod
    async def get_stock_list(cls):
        try:
            # 使用线程池执行同步数据库操作
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_stock_list_sync)
        except Exception as e:
            logger.error(f"Failed to get stock list: {e}")
            return []

    # 修改 StockDao 类的查询方法，添加更多调试信息
    @classmethod
    def _get_stock_list_sync(cls):
        try:
            with Client(
                    host=settings.ck_host,
                    port=settings.ck_port,
                    user=settings.ck_username,
                    password=settings.ck_password,
                    connect_timeout=settings.ck_connect_timeout,
                    send_receive_timeout=settings.ck_send_receive_timeout
            ) as client:
                # 先检查表是否存在
                check_query = "SHOW TABLES FROM ods_stock"
                tables = client.execute(check_query)
                logger.info(f"Available tables in ods_stock: {tables}")

                # 然后检查表中是否有数据
                count_query = "SELECT COUNT() FROM ods_stock.ll_stock_daily_sharing"
                count = client.execute(count_query)
                logger.info(f"Record count in ll_stock_daily_sharing: {count}")

                # 原始查询
                query = "SELECT code, open, close, high, low, ycp, vol, timestamps FROM ods_stock.ll_stock_daily_sharing LIMIT 10"
                logger.info(f"Executing query: {query}")
                result = client.execute(query)
                logger.info(f"Query result (first few records): {result[:5] if result else '[]'}")

                # 原来的处理逻辑
                stock_list = []
                for row in result:
                    stock = StockInfo(
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

                logger.info(f"Processed {len(stock_list)} stock records")
                return stock_list
        except Exception as e:
            logger.error(f"Error in _get_stock_list_sync: {e}")
            # 捕获更详细的异常信息
            import traceback
            logger.error(traceback.format_exc())
            return []