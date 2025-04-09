from clickhouse_driver import Client
from config.env import ClickHouseSettings

settings = ClickHouseSettings()
#add
def get_clickhouse_client():
    """
    获取 ClickHouse 客户端连接
    """
    client = Client(
        host=settings.ch_host,
        port=settings.ch_port,
        user=settings.ch_user,
        password=settings.ch_password,
        database=settings.ch_database
    )
    return client