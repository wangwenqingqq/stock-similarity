import clickhouse_connect
from entity.do.stock_do import StockInfo
from config.env import ClickHouseConfig
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

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
            # 创建clickhouse_connect客户端
            client = clickhouse_connect.get_client(
                host=ClickHouseConfig.ck_host,
                port=ClickHouseConfig.ck_port,  # 使用HTTP端口
                username=ClickHouseConfig.ck_username,
                password=ClickHouseConfig.ck_password,
                connect_timeout=ClickHouseConfig.ck_connect_timeout
            )

            # 先检查表是否存在
            check_query = "SHOW TABLES FROM ods_stock"
            tables_result = client.query(check_query)
            tables = tables_result.result_rows
            logger.info(f"Available tables in ods_stock: {tables}")

            # 然后检查表中是否有数据
            count_query = "SELECT COUNT() FROM ods_stock.ll_stock_daily_sharing"
            count_result = client.query(count_query)
            count = count_result.result_rows[0][0]
            logger.info(f"Record count in ll_stock_daily_sharing: {count}")

            # 原始查询
            query = "SELECT code, open, close, high, low, ycp, vol, timestamps FROM ods_stock.ll_stock_daily_sharing LIMIT 10"
            logger.info(f"Executing query: {query}")
            result = client.query(query)
            rows = result.result_rows
            logger.info(f"Query result (first few records): {rows[:5] if rows else '[]'}")

            # 原来的处理逻辑
            stock_list = []
            for row in rows:
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