from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from fastdtw import fastdtw
from module_stock.dao.similar_dao import SimilarDao
from module_stock.entity.vo.similar_vo import *
import logging

logger = logging.getLogger(__name__)


class StockSimilarityService:
    """股票相似性计算服务"""

    def __init__(self):
        """初始化服务"""
        self.similar_dao = SimilarDao()

    async def calculate_similarity(self, request: StockSimilarityRequest) -> StockSimilarityResponse:
        """计算股票相似性

        Args:
            request: 包含计算参数的请求对象

        Returns:
            StockSimilarityResponse: 计算结果响应
        """
        try:
            # 1. 获取基准股票数据
            base_stock_data = await self.similar_dao.get_stock_data(
                request.stockCode,
                request.startDate,
                request.endDate,
            )
            print("base_stock_data.columns", base_stock_data.columns)
            # 2. 获取所有同板块股票列表用于比较

            section_stocks_list =await self.get_section_all_stock_code(request.stockCode, request.sectionLevel)
            all_stocks = await self.similar_dao.get_section_stock_info(section_stocks_list,request.startDate,request.endDate)
            # 检查数据框是否为空
            if all_stocks.empty:
                logger.warning("没有找到任何股票数据")
                return StockSimilarityResponse(similarStocks=[], llmAnalysis=None)
            # 3. 计算每只股票与基准股票的相似度
            similar_stocks = []
            unique_codes = all_stocks['code'].unique()
            for code in unique_codes:
                if code == request.stockCode:
                    continue  # 跳过基准股票自身

                # 获取当前股票的所有数据行
                stock_df = all_stocks[all_stocks['code'] == code]
                # 计算相似度
                similarity = self._calculate_stock_similarity(
                    base_stock_data,
                    stock_df,  # 现在传递的是DataFrame，而不是字典
                    request.indicators,
                    request.similarityMethod
                )
                # 获取股票名称（如果数据框中没有name列，您需要从其他地方获取）
                stock_info = await self.similar_dao.get_stock_info(code)
                stock_name = stock_info['name']

                similar_stocks.append({
                    "code": code,
                    "name": stock_name,
                    "similarity": similarity
                })
            # 4. 按相似度排序并截取指定数量
            similar_stocks.sort(key=lambda x: x['similarity'], reverse=True)
            similar_stocks = similar_stocks[:request.similarCount]

            #5. 获取性能比较数据
            performance_data = await self._get_performance_comparison(
                base_stock_data,
                [stock['code'] for stock in similar_stocks],
            )

            # 6. 如果请求使用LLM分析，则生成分析结果
            llm_analysis = None
            if request.useLLM:
                llm_analysis = self._generate_llm_analysis(
                    request.stockCode,
                    similar_stocks,
                    request.indicators
                )

            # 7. 构建响应对象
            response = StockSimilarityResponse(
                similarStocks=[
                    SimilarStock(
                        code=stock['code'],
                        name=stock['name'],
                        similarity=stock['similarity']
                    ) for stock in similar_stocks
                ],
                performanceData=performance_data,
                llmAnalysis=llm_analysis
            )

            return response

        except Exception as e:
            logger.error(f"Error calculating stock similarity: {e}")
            raise

    async def get_section_all_stock_code(self,stock_code, section_level):
        """
        根据当前股票代码获取相同版块下的其他股票代码，并将输入的股票代码添加到返回值列表中。
        :param section_level: 版块等级，1 表示当前具体等级分类下的股票，0 表示股票所在大版的股票。
        :param stock_code:
        :return: 包含输入股票代码以及符合条件的其他股票代码组成的列表。
        """
        stock_code_list = []
        lc_csiinduspe = await self.similar_dao.get_stock_nums(stock_code, section_level)
        if lc_csiinduspe.empty:
            return [stock_code]
        csi_indus_code = lc_csiinduspe['CSIIndusCode'].iloc[0]
        if csi_indus_code is None:
            return [stock_code]
        board = lc_csiinduspe['board'].iloc[0]
        first_industry_code = lc_csiinduspe['FirstIndustryCode'].iloc[0]
        secu_name = lc_csiinduspe['SecuName'].iloc[0]
        is_ST = 1 if any(secu_name.startswith(prefix) for prefix in ['ST', '*ST']) else 0

        if (first_industry_code == csi_indus_code) or (section_level == 1):
            temp_stock_code_list, _ = await self.similar_dao.get_stock(stock_code, csi_indus_code, board, 'CSIIndusCode',
                                                                       is_ST)
        else:
            temp_stock_code_list, _ = await self.similar_dao.get_stock(stock_code, first_industry_code, board,
                                                           'FirstIndustryCode', is_ST)

        stock_code_list = [stock_code] + temp_stock_code_list

        print(f"共找到{len(stock_code_list)}只股票")
        return stock_code_list
    def _calculate_stock_similarity(

            self,
            stock1: pd.DataFrame,
            stock2: pd.DataFrame,
            indicators: List[str],
            method: str
    ) -> float:
        """计算两只股票的相似度

        Args:
            stock1: 第一只股票数据
            stock2: 第二只股票数据
            indicators: 用于计算的指标列表
            method: 相似性计算方法

        Returns:
            float: 相似度得分
        """
        if 'timestamps' in stock2.columns:
            # 将该列转换为日期类型并设置为索引
            stock2['timestamps'] = pd.to_datetime(stock2['timestamps'])
            stock2.set_index('timestamps', inplace=True)
        # 找到两只股票共同的交易日
        common_dates = stock1.index.intersection(stock2.index)
        if len(common_dates) < 2:
            logger.warning("股票对的共同交易日少于2天，无法计算相似度")
            return 0.0

        stock1_aligned = stock1.loc[common_dates]
        stock2_aligned = stock2.loc[common_dates]
        # 根据指标选择和计算方法进行计算
        if method == "dtw":
            return self._calculate_dtw_similarity(stock1_aligned, stock2_aligned, indicators)
        elif method == "pearson":
            return self._calculate_pearson_similarity(stock1_aligned, stock2_aligned, indicators)
        elif method == "euclidean":
            return self._calculate_euclidean_similarity(stock1_aligned, stock2_aligned, indicators)
        elif method == "graphMatching":
            return self._calculate_dtw_similarity(stock1_aligned, stock2_aligned, indicators)
        elif method == "gnn":
            return self._calculate_dtw_similarity(stock1_aligned, stock2_aligned, indicators)
        else:
            logger.warning(f"不支持的相似性计算方法: {method}，使用dtw代替")
            return self._calculate_dtw_similarity(stock1_aligned, stock2_aligned, indicators)

    def _calculate_dtw_similarity(
            self,
            stock1: pd.DataFrame,
            stock2: pd.DataFrame,
            indicators: List[str]
    ) -> float:
        """使用DTW计算两只股票的相似度

        Args:
            stock1: 第一只股票数据
            stock2: 第二只股票数据
            indicators: 用于计算的指标列表

        Returns:
            float: 相似度得分
        """
        dtw_distances = []

        # 根据选择的指标计算DTW距离
        if "close" in indicators:
            distance, _ = fastdtw(stock1['close'].values, stock2['close'].values,
                                  dist=lambda x, y: ((x - y) ** 2) ** 0.5)
            dtw_distances.append(distance)

        if "high" in indicators:
            # 计算最高价涨幅
            stock1_high_change = (stock1['high'] - stock1['ycp']) / stock1['ycp']
            stock2_high_change = (stock2['high'] - stock2['ycp']) / stock2['ycp']
            distance, _ = fastdtw(stock1_high_change.values, stock2_high_change.values,
                                  dist=lambda x, y: ((x - y) ** 2) ** 0.5)
            dtw_distances.append(distance)

        if "low" in indicators:
            # 计算最低价涨幅
            stock1_low_change = (stock1['low'] - stock1['ycp']) / stock1['ycp']
            stock2_low_change = (stock2['low'] - stock2['ycp']) / stock2['ycp']
            distance, _ = fastdtw(stock1_low_change.values, stock2_low_change.values,
                                  dist=lambda x, y: ((x - y) ** 2) ** 0.5)
            dtw_distances.append(distance)

        if "turnover" in indicators:
            # 计算相对换手率
            stock1_turnover = stock1['vol'] / stock1['vol'].max()
            stock2_turnover = stock2['vol'] / stock2['vol'].max()
            distance, _ = fastdtw(stock1_turnover.values, stock2_turnover.values,
                                  dist=lambda x, y: ((x - y) ** 2) ** 0.5)
            dtw_distances.append(distance)

        # 如果没有选择任何指标，返回0
        if not dtw_distances:
            return 0.0

        # 计算平均DTW距离

        avg_dtw = np.mean(dtw_distances)
        # 转换为相似度得分（距离越小，相似度越高）
        similarity = 1 / (1 + avg_dtw)
        return similarity

    def _calculate_pearson_similarity(
            self,
            stock1: pd.DataFrame,
            stock2: pd.DataFrame,
            indicators: List[str]
    ) -> float:
        """使用皮尔逊相关系数计算两只股票的相似度

        Args:
            stock1: 第一只股票数据
            stock2: 第二只股票数据
            indicators: 用于计算的指标列表

        Returns:
            float: 相似度得分
        """
        correlations = []

        if "close" in indicators:
            corr = np.corrcoef(stock1['close'].values, stock2['close'].values)[0, 1]
            correlations.append(corr)

        if "high" in indicators:
            stock1_high_change = (stock1['high'] - stock1['ycp']) / stock1['ycp']
            stock2_high_change = (stock2['high'] - stock2['ycp']) / stock2['ycp']
            corr = np.corrcoef(stock1_high_change.values, stock2_high_change.values)[0, 1]
            correlations.append(corr)

        if "low" in indicators:
            stock1_low_change = (stock1['low'] - stock1['ycp']) / stock1['ycp']
            stock2_low_change = (stock2['low'] - stock2['ycp']) / stock2['ycp']
            corr = np.corrcoef(stock1_low_change.values, stock2_low_change.values)[0, 1]
            correlations.append(corr)

        if "turnover" in indicators:
            stock1_turnover = stock1['vol'] / stock1['vol'].max()
            stock2_turnover = stock2['vol'] / stock2['vol'].max()
            corr = np.corrcoef(stock1_turnover.values, stock2_turnover.values)[0, 1]
            correlations.append(corr)

        if not correlations:
            return 0.0

        # 平均相关系数
        avg_corr = np.mean(correlations)

        # 确保相关系数在[-1, 1]范围内
        avg_corr = max(min(avg_corr, 1.0), -1.0)

        # 转换为[0, 1]的相似度得分
        similarity = (avg_corr + 1) / 2

        return similarity

    def _calculate_euclidean_similarity(
            self,
            stock1: pd.DataFrame,
            stock2: pd.DataFrame,
            indicators: List[str]
    ) -> float:
        """使用欧氏距离计算两只股票的相似度

        Args:
            stock1: 第一只股票数据
            stock2: 第二只股票数据
            indicators: 用于计算的指标列表

        Returns:
            float: 相似度得分
        """
        distances = []

        if "close" in indicators:
            # 标准化收盘价
            stock1_close_norm = (stock1['close'] - stock1['close'].mean()) / stock1['close'].std()
            stock2_close_norm = (stock2['close'] - stock2['close'].mean()) / stock2['close'].std()
            dist = np.sqrt(np.sum((stock1_close_norm.values - stock2_close_norm.values) ** 2))
            distances.append(dist)

        if "high" in indicators:
            stock1_high_change = (stock1['high'] - stock1['ycp']) / stock1['ycp']
            stock2_high_change = (stock2['high'] - stock2['ycp']) / stock2['ycp']
            dist = np.sqrt(np.sum((stock1_high_change.values - stock2_high_change.values) ** 2))
            distances.append(dist)

        if "low" in indicators:
            stock1_low_change = (stock1['low'] - stock1['ycp']) / stock1['ycp']
            stock2_low_change = (stock2['low'] - stock2['ycp']) / stock2['ycp']
            dist = np.sqrt(np.sum((stock1_low_change.values - stock2_low_change.values) ** 2))
            distances.append(dist)

        if "turnover" in indicators:
            stock1_turnover = stock1['vol'] / stock1['vol'].max()
            stock2_turnover = stock2['vol'] / stock2['vol'].max()
            dist = np.sqrt(np.sum((stock1_turnover.values - stock2_turnover.values) ** 2))
            distances.append(dist)

        if not distances:
            return 0.0

        # 平均距离
        avg_dist = np.mean(distances)

        # 转换为相似度得分
        similarity = 1 / (1 + avg_dist)

        return similarity

    async def _get_performance_comparison(
            self,
            base_stock_data: pd.DataFrame,
            similar_stock_codes: List[str]
    ) -> PerformanceData:
        """获取基准股票和相似股票的性能对比数据

        Args:
            base_stock_data: 基准股票数据 DataFrame，index 是 timestamps，
                            列名有'code', 'open', 'close', 'high', 'low', 'ycp', 'vol'
            similar_stock_codes: 相似股票代码列表

        Returns:
            PerformanceData: 性能对比数据
        """
        # 提取基准股票代码和日期范围
        base_stock_code = base_stock_data['code'].iloc[0]
        start_date = base_stock_data.index.min()
        end_date = base_stock_data.index.max()

        # 获取基准股票信息
        base_stock_info = await self.similar_dao.get_stock_info(base_stock_code)

        # 获取所有日期
        dates = base_stock_data.index.tolist()

        # 标准化基准股票的收盘价，计算累计收益率
        base_stock_return = (base_stock_data['close'] / base_stock_data['close'].iloc[0] - 1) * 100

        # 准备股票数据
        stocks_data = []

        # 添加基准股票
        stocks_data.append(
            StockPerformanceData(
                code=base_stock_code,
                name=base_stock_info['name'],
                data=base_stock_return.tolist()
            )
        )

        # 添加相似股票
        for stock_code in similar_stock_codes:
            try:
                # 使用日期范围从开始到结束获取股票数据
                similar_stock_data = await self.similar_dao.get_stock_data(
                    stock_code,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                similar_stock_info = await self.similar_dao.get_stock_info(stock_code)

                # 只取与基准股票相同的日期
                common_dates = base_stock_data.index.intersection(similar_stock_data.index)

                if len(common_dates) > 0:
                    similar_stock_aligned = similar_stock_data.loc[common_dates]
                    similar_stock_return = (similar_stock_aligned['close'] / similar_stock_aligned['close'].iloc[
                        0] - 1) * 100

                    # 确保数据长度相同，缺失的填充NaN
                    full_return = pd.Series(index=dates)
                    for date in common_dates:
                        full_return[date] = similar_stock_return[date]

                    stocks_data.append(
                        StockPerformanceData(
                            code=stock_code,
                            name=similar_stock_info['name'],
                            data=full_return.fillna(method='ffill').fillna(0).tolist()
                        )
                    )
            except Exception as e:
                logger.error(f"Error processing performance data for stock {stock_code}: {e}")

        # 将时间戳转换为字符串格式，适合前端显示
        date_strings = [date.strftime('%Y-%m-%d') for date in dates]

        return PerformanceData(
            dates=date_strings,
            stocks=stocks_data
        )

    def _generate_llm_analysis(
            self,
            base_stock_code: str,
            similar_stocks: List[Dict[str, Any]],
            indicators: List[str]
    ) -> str:
        """生成大语言模型分析

        Args:
            base_stock_code: 基准股票代码
            similar_stocks: 相似股票列表
            indicators: 使用的指标

        Returns:
            str: 分析文本
        """
        # 在实际应用中，这里应该调用大语言模型API
        # 这里提供一个简单的模板生成
        base_stock_info = self.similar_dao.get_stock_info(base_stock_code)

        analysis = f"## {base_stock_info['name']}({base_stock_code})相似股票分析\n\n"
        analysis += f"基于{', '.join(indicators)}指标计算，发现以下股票与{base_stock_info['name']}走势相似：\n\n"

        for i, stock in enumerate(similar_stocks[:3], 1):
            stock_info = self.similar_dao.get_stock_info(stock['code'])
            analysis += f"{i}. **{stock['name']}({stock['code']})** - 相似度: {stock['similarity']:.2f}\n"
            analysis += f"   行业: {stock_info['industry']}\n"
            analysis += f"   这两支股票在近期表现出了{stock['similarity']:.0%}的相似度，建议关注。\n\n"

        analysis += f"总体而言，这些股票与{base_stock_info['name']}在所选择的技术指标上表现出较强的相似性，投资者可以参考这些相似股票的历史表现来辅助投资决策。"

        return analysis
