from redis import asyncio as aioredis
from redis.exceptions import AuthenticationError, TimeoutError, RedisError
from config.database import AsyncSessionLocal
from config.env import RedisConfig, SSHConfig
from module_admin.service.config_service import ConfigService
from module_admin.service.dict_service import DictDataService
from utils.log_util import logger
import sshtunnel
import atexit


class RedisUtil:
    """
    Redis相关方法
    """

    @classmethod
    async def create_redis_pool(cls) -> aioredis.Redis:
        """
        应用启动时初始化redis连接

        :return: Redis连接对象
        """
        logger.info('开始连接redis...')
        try:
            tunnel = sshtunnel.SSHTunnelForwarder(
                (SSHConfig.ssh_host, SSHConfig.ssh_port),
                ssh_username=SSHConfig.ssh_username,
                ssh_pkey=SSHConfig.ssh_key_path,
                remote_bind_address=(RedisConfig.redis_host, RedisConfig.redis_port),
                local_bind_address=('127.0.0.1', 0)  # 随机本地端口
            )
            tunnel.start()
            local_port = tunnel.local_bind_port

            redis_pool = aioredis.ConnectionPool(
                host='127.0.0.1',
                port=local_port,
                username=RedisConfig.redis_username,
                password=RedisConfig.redis_password,
                db=RedisConfig.redis_database,
                encoding='utf-8',
                decode_responses=True,
                socket_timeout=60,
                socket_connect_timeout=60
            )

            redis_client = aioredis.Redis(connection_pool=redis_pool)

            connection = await redis_client.ping()
            if connection:
                logger.info('redis连接成功')
            else:
                logger.error('redis连接失败')

            # 在程序退出时关闭隧道
            atexit.register(tunnel.close)

            return redis_client
        except AuthenticationError as e:
            logger.error(f'redis用户名或密码错误，详细错误信息：{e}')
            raise
        except TimeoutError as e:
            logger.error(f'redis连接超时，详细错误信息：{e}')
            raise
        except RedisError as e:
            logger.error(f'redis连接错误，详细错误信息：{e}')
            raise
        except Exception as e:
            logger.error(f'创建SSH隧道失败，详细错误信息：{e}')
            raise

    @classmethod
    async def close_redis_pool(cls, app):
        """
        应用关闭时关闭redis连接

        :param app: fastapi对象
        :return:
        """
        await app.state.redis.close()
        logger.info('关闭redis连接成功')

    @classmethod
    async def init_sys_dict(cls, redis):
        """
        应用启动时缓存字典表

        :param redis: redis对象
        :return:
        """
        async with AsyncSessionLocal() as session:
            await DictDataService.init_cache_sys_dict_services(session, redis)

    @classmethod
    async def init_sys_config(cls, redis):
        """
        应用启动时缓存参数配置表

        :param redis: redis对象
        :return:
        """
        async with AsyncSessionLocal() as session:
            await ConfigService.init_cache_sys_config_services(session, redis)
