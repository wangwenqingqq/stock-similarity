import clickhouse_connect
from config.env import ClickHouseConfig
from queue import Queue
import time
import sshtunnel


CK_HOST = ClickHouseConfig.ck_host
CK_PORT = ClickHouseConfig.ck_port
CK_USER_NAME = ClickHouseConfig.ck_username
CK_PASSWORD = ClickHouseConfig.ck_password  # 添加密码配置
CK_CONNECT_TIMEOUT = 30     
CK_SEND_RECEIVE_TIMEOUT = 30 
CK_COMPRESSION = ClickHouseConfig.ck_compression

# SSH 跳板机配置
SSH_HOST = 'isrc.iscas.ac.cn'  # 跳板机地址
SSH_PORT = 5022  # 跳板机 SSH 端口
SSH_USERNAME = 'xuran'  # 跳板机用户名
SSH_KEY_PATH = r'C:\Users\isrc\.ssh\id_rsa'  # 使用原始字符串避免转义问题


def create_ssh_tunnel():
    """创建 SSH 隧道"""
    try:
        tunnel = sshtunnel.SSHTunnelForwarder(
            (SSH_HOST, SSH_PORT),
            ssh_username=SSH_USERNAME,
            ssh_pkey=SSH_KEY_PATH,
            remote_bind_address=(CK_HOST, CK_PORT),
            local_bind_address=('127.0.0.1', 0)  # 随机本地端口
        )
        tunnel.start()
        return tunnel
    except Exception as e:
        print(f"SSH 隧道创建失败: {str(e)}")
        print(f"使用的 SSH 密钥路径: {SSH_KEY_PATH}")
        print(f"目标地址: {CK_HOST}:{CK_PORT}")
        print(f"跳板机地址: {SSH_HOST}:{SSH_PORT}")
        raise


def create_client_with_retry(max_retries=3, retry_delay=5):
    """创建带重试的 ClickHouse 客户端"""
    tunnel = create_ssh_tunnel()
    local_port = tunnel.local_bind_port

    for attempt in range(max_retries):
        try:
            client = clickhouse_connect.get_client(
                host='127.0.0.1',  # 使用本地地址
                port=local_port,  # 使用隧道本地端口
                username=CK_USER_NAME,
                password=CK_PASSWORD,  # 添加密码
                connect_timeout=CK_CONNECT_TIMEOUT,
                send_receive_timeout=CK_SEND_RECEIVE_TIMEOUT,
                compression=CK_COMPRESSION
            )
            return client, tunnel
        except Exception as e:
            if attempt == max_retries - 1:  # 最后一次尝试
                tunnel.close()
                raise e
            print(f"连接尝试 {attempt + 1} 失败，{retry_delay} 秒后重试...")
            time.sleep(retry_delay)


class ClickHousePool:
    def __init__(self, maxsize=10):
        self.pool = Queue(maxsize)
        self.tunnels = []  # 保存所有隧道连接
        for _ in range(maxsize):
            client, tunnel = create_client_with_retry()
            self.pool.put(client)
            self.tunnels.append(tunnel)

    def get_client(self):
        return self.pool.get()

    def release_client(self, client):
        self.pool.put(client)

    def close(self):
        """关闭所有隧道连接"""
        for tunnel in self.tunnels:
            try:
                tunnel.close()
            except:
                pass


# 创建全局池
try:
    ch_pool = ClickHousePool(maxsize=10)
except Exception as e:
    print(f"初始化 ClickHouse 连接池失败: {str(e)}")
    raise


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


# 在程序退出时关闭连接池
import atexit

atexit.register(ch_pool.close)
