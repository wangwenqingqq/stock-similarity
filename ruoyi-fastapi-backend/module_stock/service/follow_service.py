from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from dao.follow_dao import FollowDAO

# 配置日志记录器
logger = logging.getLogger(__name__)


class StockFollowService:
    """
    股票服务类
    负责处理与股票相关的业务逻辑，是DAO层与控制层之间的桥梁
    """

    async def get_stock_list(
            self,
            db: AsyncSession,
            page: int = 1,
            size: int = 10,
            keyword: Optional[str] = None,
            status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取股票列表

        Args:
            db: 数据库会话
            page: 页码，默认为1
            size: 每页数量，默认为10
            keyword: 搜索关键词，可选
            status: 股票状态，可选

        Returns:
            Dict[str, Any]: 包含股票列表和分页信息的字典
        """
        try:
            stocks, total = await FollowDAO.get_stock_list(page, size, keyword, status)

            # 格式化数据
            for stock in stocks:
                if 'change' in stock and stock['change'] is not None:
                    stock['change'] = round(stock['change'], 2)

            result = {
                "list": stocks,
                "pagination": {
                    "current": page,
                    "pageSize": size,
                    "total": total
                }
            }

            return result
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise

    async def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索股票

        Args:
            keyword: 搜索关键词

        Returns:
            List[Dict[str, Any]]: 符合条件的股票列表
        """
        try:
            if not keyword or len(keyword.strip()) == 0:
                return []

            stocks = await FollowDAO.search_stocks(keyword.strip())

            # 格式化数据
            for stock in stocks:
                if 'change' in stock and stock['change'] is not None:
                    stock['change'] = round(stock['change'], 2)

            return stocks
        except Exception as e:
            logger.error(f"搜索股票失败，关键词: {keyword}, 错误: {e}")
            raise

    async def get_stock_detail(self, code: str) -> Dict[str, Any]:
        """
        获取股票详细信息

        Args:
            code: 股票代码

        Returns:
            Dict[str, Any]: 股票详细信息
        """
        try:
            if not code:
                logger.warning("股票代码为空")
                return {}

            stock = await FollowDAO.get_stock_detail(code)

            if not stock:
                logger.warning(f"未找到股票，代码: {code}")
                return {}

            # 格式化数据
            if 'change' in stock and stock['change'] is not None:
                stock['change'] = round(stock['change'], 2)

            # 获取历史数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

            history_data = await FollowDAO.get_stock_history(code, start_date, end_date)

            # 转换历史数据为前端需要的格式
            history = []
            if not history_data.empty:
                for _, row in history_data.iterrows():
                    history.append({
                        "date": row['timestamps'].strftime('%Y-%m-%d') if 'timestamps' in row else '',
                        "open": float(row['open']) if 'open' in row else 0,
                        "close": float(row['close']) if 'close' in row else 0,
                        "high": float(row['high']) if 'high' in row else 0,
                        "low": float(row['low']) if 'low' in row else 0,
                        "volume": int(row['vol']) if 'vol' in row else 0
                    })

            # 合并结果
            result = {**stock, "history": history}
            return result
        except Exception as e:
            logger.error(f"获取股票详情失败，股票代码: {code}, 错误: {e}")
            raise

    async def get_user_watchlist(self, db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户关注的股票列表

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            List[Dict[str, Any]]: 用户关注的股票列表
        """
        try:
            if not user_id:
                logger.warning("用户ID为空")
                return []

            stocks = await FollowDAO.get_user_watchlist(db, user_id)

            # 格式化数据
            for stock in stocks:
                if 'change' in stock and stock['change'] is not None:
                    stock['change'] = round(stock['change'], 2)

            return stocks
        except Exception as e:
            logger.error(f"获取用户关注列表失败，用户ID: {user_id}, 错误: {e}")
            raise

    async def add_to_watchlist(self, db: AsyncSession, user_id: str, stock_code: str) -> Dict[str, Any]:
        """
        将股票添加到用户关注列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            stock_code: 股票代码

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            if not user_id or not stock_code:
                logger.warning(f"用户ID或股票代码为空，用户ID: {user_id}, 股票代码: {stock_code}")
                return {"success": False, "message": "参数不能为空"}

            # 添加到关注列表
            result = await FollowDAO.add_to_watchlist(db, user_id, stock_code)

            if result:
                return {"success": True, "message": "添加成功"}
            else:
                return {"success": False, "message": "股票已在关注列表中"}
        except Exception as e:
            logger.error(f"添加股票到关注列表失败，用户ID: {user_id}, 股票代码: {stock_code}, 错误: {e}")
            return {"success": False, "message": f"添加失败: {str(e)}"}

    async def remove_from_watchlist(self, db: AsyncSession, user_id: str, stock_code: str) -> Dict[str, Any]:
        """
        从用户关注列表中移除股票

        Args:
            db: 数据库会话
            user_id: 用户ID
            stock_code: 股票代码

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            if not user_id or not stock_code:
                logger.warning(f"用户ID或股票代码为空，用户ID: {user_id}, 股票代码: {stock_code}")
                return {"success": False, "message": "参数不能为空"}

            # 从关注列表移除
            result = await FollowDAO.remove_from_watchlist(db, user_id, stock_code)
            return {"success": True, "message": "移除成功"}
        except Exception as e:
            logger.error(f"从关注列表移除股票失败，用户ID: {user_id}, 股票代码: {stock_code}, 错误: {e}")
            return {"success": False, "message": f"移除失败: {str(e)}"}

    async def clear_watchlist(self, db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        清空用户关注列表

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            if not user_id:
                logger.warning("用户ID为空")
                return {"success": False, "message": "用户ID不能为空"}

            # 清空关注列表
            result = await FollowDAO.clear_watchlist(db, user_id)
            return {"success": True, "message": "关注列表已清空"}
        except Exception as e:
            logger.error(f"清空关注列表失败，用户ID: {user_id}, 错误: {e}")
            return {"success": False, "message": f"清空失败: {str(e)}"}

    @classmethod
    async def get_market_overview(cls) -> Dict[str, Any]:
        """
        获取市场概览

        Returns:
            Dict[str, Any]: 市场概览数据
        """
        try:
            # 获取今日日期
            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

            # 查询上证指数
            sh_index = await FollowDAO.get_stock_detail('000001.SH')

            # 查询深证成指
            sz_index = await FollowDAO.get_stock_detail('399001.SZ')

            # 查询创业板指
            cyb_index = await FollowDAO.get_stock_detail('399006.SZ')

            # 汇总结果
            result = {
                "date": today,
                "indexes": [
                    {
                        "name": "上证指数",
                        "code": "000001.SH",
                        "current": sh_index.get('close', 0) if sh_index else 0,
                        "change": round(sh_index.get('change', 0), 2) if sh_index else 0
                    },
                    {
                        "name": "深证成指",
                        "code": "399001.SZ",
                        "current": sz_index.get('close', 0) if sz_index else 0,
                        "change": round(sz_index.get('change', 0), 2) if sz_index else 0
                    },
                    {
                        "name": "创业板指",
                        "code": "399006.SZ",
                        "current": cyb_index.get('close', 0) if cyb_index else 0,
                        "change": round(cyb_index.get('change', 0), 2) if cyb_index else 0
                    }
                ]
            }

            return result
        except Exception as e:
            logger.error(f"获取市场概览失败: {e}")
            return {
                "date": datetime.now().strftime('%Y-%m-%d'),
                "indexes": []
            }