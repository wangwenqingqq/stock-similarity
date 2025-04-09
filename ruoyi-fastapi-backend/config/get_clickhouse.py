from clickhouse_driver import Client
from config.env import ClickHouseSettings

settings = ClickHouseSettings()

def get_clickhouse_client():
    """
    获取 ClickHouse 客户端连接
    """
    client = Client(
        host=settings.ck_host,
        port=settings.ck_port,
        user=settings.ck_username,
        password=settings.ck_password
    )
    return client