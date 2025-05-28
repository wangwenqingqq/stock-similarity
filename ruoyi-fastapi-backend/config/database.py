from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from urllib.parse import quote_plus
from config.env import DataBaseConfig, SSHConfig
import sshtunnel
import asyncio
from utils.log_util import logger

# 创建SSH隧道
def create_ssh_tunnel():
    """创建 SSH 隧道"""
    try:
        tunnel = sshtunnel.SSHTunnelForwarder(
            (SSHConfig.ssh_host, SSHConfig.ssh_port),
            ssh_username=SSHConfig.ssh_username,
            ssh_pkey=SSHConfig.ssh_key_path,
            remote_bind_address=(DataBaseConfig.db_host, DataBaseConfig.db_port),
            local_bind_address=('127.0.0.1', 0)  # 随机本地端口
        )
        tunnel.start()
        return tunnel
    except Exception as e:
        logger.error(f"SSH 隧道创建失败: {str(e)}")
        logger.error(f"使用的 SSH 密钥路径: {SSHConfig.ssh_key_path}")
        logger.error(f"目标地址: {DataBaseConfig.db_host}:{DataBaseConfig.db_port}")
        logger.error(f"跳板机地址: {SSHConfig.ssh_host}:{SSHConfig.ssh_port}")
        raise

# 创建SSH隧道
tunnel = create_ssh_tunnel()
local_port = tunnel.local_bind_port

# 使用本地端口创建数据库URL
ASYNC_SQLALCHEMY_DATABASE_URL = (
    f'mysql+asyncmy://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}@'
    f'127.0.0.1:{local_port}/{DataBaseConfig.db_database}'
)
if DataBaseConfig.db_type == 'postgresql':
    ASYNC_SQLALCHEMY_DATABASE_URL = (
        f'postgresql+asyncpg://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}@'
        f'127.0.0.1:{local_port}/{DataBaseConfig.db_database}'
    )

async_engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    echo=DataBaseConfig.db_echo,
    max_overflow=DataBaseConfig.db_max_overflow,
    pool_size=DataBaseConfig.db_pool_size,
    pool_recycle=DataBaseConfig.db_pool_recycle,
    pool_timeout=DataBaseConfig.db_pool_timeout,
)
AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=async_engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass

# 在程序退出时关闭隧道
import atexit
atexit.register(tunnel.close)
