import clickhouse_connect

from config.env import ClickHouseConfig

CK_HOST = ClickHouseConfig.ck_host
CK_PORT = ClickHouseConfig.ck_port
CK_USER_NAME = ClickHouseConfig.ck_username
CK_PWD = ClickHouseConfig.ck_password
client = clickhouse_connect.get_client(host=CK_HOST, port=CK_PORT, username=CK_USER_NAME, password=CK_PWD)


# conn = connect(host=CK_HOST, port=CK_PORT, username=CK_USER_NAME, password=CK_PWD)
# client = conn.cursor()

def query(sql: str):
    result = client.query(sql)
    return result


def insert(db: str, table: str, data: list, column_names: list, column_types: list = None):
    client.insert(table=table, database=db, data=data, column_names=column_names, column_type_names=column_types);


def insert_df(db: str, table: str, df, column_names: list, column_types: list = None):
    client.insert_df(table=table, database=db, df=df, column_names=column_names, column_type_names=column_types);
