import clickhouse_connect
from config.env import ClickHouseConfig
from queue import Queue

CK_HOST = ClickHouseConfig.ck_host
CK_PORT = ClickHouseConfig.ck_port
CK_USER_NAME = ClickHouseConfig.ck_username
CK_PWD = ClickHouseConfig.ck_password

class ClickHousePool:
    def __init__(self, maxsize=10):
        self.pool = Queue(maxsize)
        for _ in range(maxsize):
            client = clickhouse_connect.get_client(
                host=CK_HOST,
                port=CK_PORT,
                username=CK_USER_NAME,
                password=CK_PWD
            )
            self.pool.put(client)

    def get_client(self):
        return self.pool.get()

    def release_client(self, client):
        self.pool.put(client)

# 创建全局池
ch_pool = ClickHousePool(maxsize=10)

def query(sql: str):
    client = ch_pool.get_client()
    try:
        result = client.query(sql)
        return result
    finally:
        ch_pool.release_client(client)

def insert(db: str, table: str, data: list, column_names: list, column_types: list = None):
    client = ch_pool.get_client()
    try:
        client.insert(table=table, database=db, data=data, column_names=column_names, column_type_names=column_types)
    finally:
        ch_pool.release_client(client)

def insert_df(db: str, table: str, df, column_names: list, column_types: list = None):
    client = ch_pool.get_client()
    try:
        client.insert_df(table=table, database=db, df=df, column_names=column_names, column_type_names=column_types)
    finally:
        ch_pool.release_client(client)