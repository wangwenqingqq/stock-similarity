from typing import List, Dict, Any, Optional

import networkx as nx
import pandas as pd
import numpy as np
from fastdtw import fastdtw
from module_stock.dao.similar_dao import SimilarDao
from module_stock.entity.vo.similar_vo import *
import logging
import statsmodels.tsa.stattools as ts
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
            # 如果请求的相似性方法是图匹配或者最大公共子图
            if request.similarityMethod in ["graphEditing", "maxCommonSubgraph"]:
                # 构建基础股票的图
                base_stock_graph = self._create_price_graph(base_stock_data, request.indicators)

                for code in unique_codes:
                    if code == request.stockCode:
                        continue  # 跳过基准股票自身

                    # 获取当前细分行业股票的所有数据行
                    stock_df = all_stocks[all_stocks['code'] == code]

                    # 构建比较股票的图
                    stock_graph = self._create_price_graph(stock_df, request.indicators)

                    # 根据方法选择相应的相似度计算函数
                    if request.similarityMethod == "maxCommonSubgraph":
                        similarity = self._calculate_mcs_similarity(base_stock_graph, stock_graph, request.indicators)
                    else:  # graphMatching
                        similarity = self._calculate_graph_similarity(base_stock_graph, stock_graph, request.indicators)

                    # 获取股票名称
                    stock_info = await self.similar_dao.get_stock_info(code)
                    stock_name = stock_info['name']

                    similar_stocks.append({
                        "code": code,
                        "name": stock_name,
                        "similarity": float(similarity)  # 确保转换为float类型
                    })
            else:
                # 使用其他相似度计算方法
                for code in unique_codes:
                    if code == request.stockCode:
                        continue  # 跳过基准股票自身

                    # 获取当前股票的所有数据行
                    stock_df = all_stocks[all_stocks['code'] == code]

                    # 计算相似度
                    similarity = self._calculate_stock_similarity(
                        base_stock_data,
                        stock_df,
                        request.indicators,
                        request.similarityMethod
                    )

                    # 获取股票名称
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
            print("similar_stocks[]", similar_stocks)
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
        elif method == "coIntegration":
            return self._calculate_cointegration_similarity(stock1_aligned, stock2_aligned, indicators)
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

    def _calculate_cointegration_similarity(
            self,
            stock1: pd.DataFrame,
            stock2: pd.DataFrame,
            indicators: List[str]
    ) -> float:
        """使用协整性检验计算两只股票的相似度

        Args:
            stock1: 第一只股票数据
            stock2: 第二只股票数据
            indicators: 用于计算的指标列表

        Returns:
            float: 相似度得分
        """
        p_values = []

        # 检查数据长度是否足够
        if len(stock1) <= 25 or len(stock2) <= 25:
            return 0.0

        # 根据选择的指标计算协整性p值
        if "close" in indicators:
            _, p_val, _ = ts.coint(stock1['close'].values, stock2['close'].values)
            p_values.append(p_val)

        if "high" in indicators:
            # 计算最高价涨幅
            stock1_high_change = (stock1['high'] - stock1['ycp']) / stock1['ycp']
            stock2_high_change = (stock2['high'] - stock2['ycp']) / stock2['ycp']
            _, p_val, _ = ts.coint(stock1_high_change.values, stock2_high_change.values)
            p_values.append(p_val)

        if "low" in indicators:
            # 计算最低价涨幅
            stock1_low_change = (stock1['low'] - stock1['ycp']) / stock1['ycp']
            stock2_low_change = (stock2['low'] - stock2['ycp']) / stock2['ycp']
            _, p_val, _ = ts.coint(stock1_low_change.values, stock2_low_change.values)
            p_values.append(p_val)

        if "turnover" in indicators:
            # 计算相对换手率
            stock1_turnover = stock1['vol'] / stock1['vol'].max()
            stock2_turnover = stock2['vol'] / stock2['vol'].max()
            _, p_val, _ = ts.coint(stock1_turnover.values, stock2_turnover.values)
            p_values.append(p_val)

        # 如果没有选择任何指标，返回0
        if not p_values:
            return 0.0

        # 计算平均p值
        avg_p_val = np.mean(p_values)

        # 转换为相似度得分（p值越小，协整性越强，相似度越高）
        # 使用1-p值作为相似度，但限制在0到1之间
        similarity = max(0, min(1, 1 - avg_p_val))
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
        pearson_values = []

        # 检查数据长度是否足够
        if len(stock1) <= 25 or len(stock2) <= 25:
            return 0.0

        # 根据选择的指标计算皮尔逊相关系数
        if "close" in indicators:
            pearson = np.corrcoef(stock1['close'].values, stock2['close'].values)[0, 1]
            pearson_values.append(pearson)

        if "high" in indicators:
            # 计算最高价涨幅
            stock1_high_change = (stock1['high'] - stock1['ycp']) / stock1['ycp']
            stock2_high_change = (stock2['high'] - stock2['ycp']) / stock2['ycp']
            pearson = np.corrcoef(stock1_high_change.values, stock2_high_change.values)[0, 1]
            pearson_values.append(pearson)

        if "low" in indicators:
            # 计算最低价涨幅
            stock1_low_change = (stock1['low'] - stock1['ycp']) / stock1['ycp']
            stock2_low_change = (stock2['low'] - stock2['ycp']) / stock2['ycp']
            pearson = np.corrcoef(stock1_low_change.values, stock2_low_change.values)[0, 1]
            pearson_values.append(pearson)

        if "turnover" in indicators:
            # 计算相对换手率
            stock1_turnover = stock1['vol'] / stock1['vol'].max()
            stock2_turnover = stock2['vol'] / stock2['vol'].max()
            pearson = np.corrcoef(stock1_turnover.values, stock2_turnover.values)[0, 1]
            pearson_values.append(pearson)

        # 如果没有选择任何指标，返回0
        if not pearson_values:
            return 0.0

        # 计算平均皮尔逊相关系数
        avg_pearson = np.mean(pearson_values)

        # 处理可能的NaN值
        if np.isnan(avg_pearson):
            return 0.0

        # 转换为相似度得分（相关系数越接近1，相似度越高）
        # 皮尔逊相关系数范围为[-1,1]，这里直接使用相关系数的绝对值作为相似度
        similarity = abs(avg_pearson)
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

    def _create_price_graph(self, df: pd.DataFrame, indicators: List[str]) -> nx.Graph:
        """
        将单个股票的K线数据转换为图结构，根据指定的指标创建节点特征

        Args:
            df: 包含K线数据的DataFrame，以timestamps为索引
            indicators: 用于构建图的指标列表

        Returns:
            nx.Graph: NetworkX图对象
        """
        from decimal import Decimal, getcontext
        getcontext().prec = 10
        G = nx.Graph()

        # 确保df有一个副本以避免修改原始数据
        df = df.copy()

        # 将相关列转换为Decimal类型，只转换存在的列
        cols_to_convert = []
        for col in ['close', 'high', 'low', 'vol', 'ycp']:
            if col in df.columns:
                cols_to_convert.append(col)

        for col in cols_to_convert:
            df[col] = df[col].apply(lambda x: Decimal(str(x)))

        # 预先计算相对换手率，如果需要且有相关数据
        if "turnover" in indicators and 'vol' in df.columns:
            max_vol = df['vol'].max()
            if max_vol != 0:
                df['relative_turnover'] = df['vol'].apply(lambda x: x / max_vol)
            else:
                df['relative_turnover'] = df['vol'].apply(lambda x: Decimal('0'))

        # 为每个交易日创建节点，只包含指定的指标特征
        for idx, row in df.iterrows():
            node_features = {'date': idx}

            # 根据指定的指标添加对应的特征，但要确保列存在
            if "close" in indicators and 'close' in df.columns:
                node_features['close'] = row['close']

            if "high" in indicators and 'high' in df.columns and 'ycp' in df.columns:
                # 计算最高价涨幅
                high_change = (row['high'] - row['ycp']) / row['ycp'] if row['ycp'] != 0 else Decimal('0')
                node_features['high_change'] = high_change

            if "low" in indicators and 'low' in df.columns and 'ycp' in df.columns:
                # 计算最低价涨幅
                low_change = (row['low'] - row['ycp']) / row['ycp'] if row['ycp'] != 0 else Decimal('0')
                node_features['low_change'] = low_change

            if "turnover" in indicators and 'relative_turnover' in df.columns:
                node_features['relative_turnover'] = row['relative_turnover']

            G.add_node(idx, **node_features)

        # 创建边连接相邻的交易日
        dates = list(df.index)
        for i in range(len(dates) - 1):
            current_date = dates[i]
            next_date = dates[i + 1]

            # 初始化边权重
            edge_weight = Decimal('0')
            edge_count = 0

            # 根据指定的指标计算边的权重，检查特征是否存在
            if "close" in indicators and 'close' in G.nodes[current_date] and 'close' in G.nodes[next_date]:
                close_diff = abs(G.nodes[next_date]['close'] - G.nodes[current_date]['close'])
                edge_weight += close_diff
                edge_count += 1

            if "high" in indicators and 'high_change' in G.nodes[current_date] and 'high_change' in G.nodes[next_date]:
                high_diff = abs(G.nodes[next_date]['high_change'] - G.nodes[current_date]['high_change'])
                edge_weight += high_diff
                edge_count += 1

            if "low" in indicators and 'low_change' in G.nodes[current_date] and 'low_change' in G.nodes[next_date]:
                low_diff = abs(G.nodes[next_date]['low_change'] - G.nodes[current_date]['low_change'])
                edge_weight += low_diff
                edge_count += 1

            if "turnover" in indicators and 'relative_turnover' in G.nodes[current_date] and 'relative_turnover' in \
                    G.nodes[next_date]:
                turnover_diff = abs(
                    G.nodes[next_date]['relative_turnover'] - G.nodes[current_date]['relative_turnover'])
                edge_weight += turnover_diff
                edge_count += 1

            # 计算平均边权重，确保不同指标数量下的权重可比
            if edge_count > 0:
                edge_weight = edge_weight / Decimal(str(edge_count))
            else:
                edge_weight = Decimal('0')  # 如果没有共同特征，设置权重为0

            G.add_edge(current_date, next_date, weight=edge_weight)

        return G

    def _calculate_mcs_similarity(self, G1: nx.Graph, G2: nx.Graph, indicators: List[str]) -> float:
        """
        计算两个图之间的最大公共子图相似度

        Args:
            G1: 第一个图
            G2: 第二个图
            indicators: 用于计算相似度的指标列表

        Returns:
            float: 相似度得分，范围在0-1之间，1表示完全相似
        """
        from decimal import Decimal, getcontext
        getcontext().prec = 10

        # 如果任一图为空，则返回0
        if G1.number_of_nodes() == 0 or G2.number_of_nodes() == 0:
            return 0.0

        try:
            # 1. 构建产品图
            product_graph = nx.Graph()

            # 2. 为每个指标分别添加节点和边
            for node1 in G1.nodes():
                for node2 in G2.nodes():
                    # 检查两个节点是否有相同的特征集
                    compatible = True
                    for indicator in indicators:
                        if indicator == "close" and 'close' in G1.nodes[node1] and 'close' in G2.nodes[node2]:
                            continue
                        elif indicator == "high" and 'high_change' in G1.nodes[node1] and 'high_change' in G2.nodes[
                            node2]:
                            continue
                        elif indicator == "low" and 'low_change' in G1.nodes[node1] and 'low_change' in G2.nodes[node2]:
                            continue
                        elif indicator == "turnover" and 'relative_turnover' in G1.nodes[
                            node1] and 'relative_turnover' in G2.nodes[node2]:
                            continue
                        else:
                            if indicator in indicators and (
                                    (indicator == "close" and (
                                            'close' not in G1.nodes[node1] or 'close' not in G2.nodes[node2])) or
                                    (indicator == "high" and (
                                            'high_change' not in G1.nodes[node1] or 'high_change' not in G2.nodes[
                                        node2])) or
                                    (indicator == "low" and (
                                            'low_change' not in G1.nodes[node1] or 'low_change' not in G2.nodes[
                                        node2])) or
                                    (indicator == "turnover" and (
                                            'relative_turnover' not in G1.nodes[node1] or 'relative_turnover' not in
                                            G2.nodes[node2]))
                            ):
                                compatible = False
                                break

                    if compatible:
                        product_graph.add_node((node1, node2))

            # 3. 为产品图添加边
            for (node1_a, node2_a) in product_graph.nodes():
                for (node1_b, node2_b) in product_graph.nodes():
                    if (node1_a != node1_b) and (node2_a != node2_b):
                        # 检查原图中是否存在对应的边
                        if G1.has_edge(node1_a, node1_b) and G2.has_edge(node2_a, node2_b):
                            # 计算边权重相似度
                            weight_sim = 1.0 - abs(G1[node1_a][node1_b]['weight'] - G2[node2_a][node2_b]['weight'])
                            if weight_sim > 0.5:  # 只有当边权重相似度大于阈值时才添加边
                                product_graph.add_edge((node1_a, node2_a), (node1_b, node2_b), weight=weight_sim)

            # 4. 使用近似算法寻找最大团（对应于最大公共子图）
            # 这里使用一个简单的贪婪算法
            remaining_nodes = set(product_graph.nodes())
            max_clique = []

            # 按度数排序节点
            nodes_by_degree = sorted(product_graph.nodes(),
                                     key=lambda n: product_graph.degree(n),
                                     reverse=True)

            for node in nodes_by_degree:
                if all(product_graph.has_edge(node, clique_node) for clique_node in max_clique):
                    max_clique.append(node)

            # 5. 计算相似度
            mcs_size = len(max_clique)
            g1_size = G1.number_of_nodes()
            g2_size = G2.number_of_nodes()

            # 使用Tanimoto系数计算相似度
            similarity = Decimal(str(mcs_size)) / (
                        Decimal(str(g1_size)) + Decimal(str(g2_size)) - Decimal(str(mcs_size)))

            return float(similarity)

        except Exception as e:
            logger.error(f"计算最大公共子图相似度时出错: {e}")
            return 0.0
    def _calculate_graph_similarity(self, G1: nx.Graph, G2: nx.Graph, indicators: List[str]) -> float:
        """
        计算两个图之间的相似度，基于图编辑距离的价格轨迹相似度，
        根据指定的指标单独计算相似度，然后综合得出最终相似度

        Args:
            G1: 第一个图
            G2: 第二个图
            indicators: 用于计算相似度的指标列表

        Returns:
            float: 相似度得分，范围在0-1之间，1表示完全相似
        """
        from decimal import Decimal, getcontext
        getcontext().prec = 10
        # 获取两个图的共同节点
        common_dates = set(G1.nodes()) & set(G2.nodes())
        if not common_dates:
            return 0.0

        # 为每个指标单独计算相似度
        similarity_scores = []

        # 对于每个指标，首先检查所有共同节点是否都有该特征
        # 计算"close"指标的相似度
        if "close" in indicators:
            close_nodes = [date for date in common_dates if 'close' in G1.nodes[date] and 'close' in G2.nodes[date]]
            if close_nodes:
                close_diff_total = Decimal('0')
                for date in close_nodes:
                    node1 = G1.nodes[date]
                    node2 = G2.nodes[date]
                    # 计算收盘价差异
                    close_diff = abs(node1['close'] - node2['close'])
                    # 归一化
                    max_close = max(abs(node1['close']), abs(node2['close']))
                    if max_close > 0:
                        close_diff /= max_close
                    close_diff_total += close_diff

                # 计算平均差异并转换为相似度分数
                if len(close_nodes) > 0:
                    avg_close_diff = close_diff_total / Decimal(str(len(close_nodes)))
                    close_similarity = Decimal('1') - avg_close_diff
                    # 确保结果在0-1之间
                    close_similarity = max(min(close_similarity, Decimal('1')), Decimal('0'))
                    similarity_scores.append(close_similarity)

        # 计算"high"指标的相似度
        if "high" in indicators:
            high_nodes = [date for date in common_dates if
                          'high_change' in G1.nodes[date] and 'high_change' in G2.nodes[date]]
            if high_nodes:
                high_diff_total = Decimal('0')
                for date in high_nodes:
                    node1 = G1.nodes[date]
                    node2 = G2.nodes[date]
                    # 计算最高价涨幅差异
                    high_diff = abs(node1['high_change'] - node2['high_change'])
                    high_diff_total += high_diff

                # 计算平均差异并转换为相似度分数
                if len(high_nodes) > 0:
                    avg_high_diff = high_diff_total / Decimal(str(len(high_nodes)))
                    high_similarity = Decimal('1') / (Decimal('1') + avg_high_diff)  # 使用倒数转换为相似度
                    # 确保结果在0-1之间
                    high_similarity = max(min(high_similarity, Decimal('1')), Decimal('0'))
                    similarity_scores.append(high_similarity)

        # 计算"low"指标的相似度
        if "low" in indicators:
            low_nodes = [date for date in common_dates if
                         'low_change' in G1.nodes[date] and 'low_change' in G2.nodes[date]]
            if low_nodes:
                low_diff_total = Decimal('0')
                for date in low_nodes:
                    node1 = G1.nodes[date]
                    node2 = G2.nodes[date]
                    # 计算最低价涨幅差异
                    low_diff = abs(node1['low_change'] - node2['low_change'])
                    low_diff_total += low_diff

                # 计算平均差异并转换为相似度分数
                if len(low_nodes) > 0:
                    avg_low_diff = low_diff_total / Decimal(str(len(low_nodes)))
                    low_similarity = Decimal('1') / (Decimal('1') + avg_low_diff)  # 使用倒数转换为相似度
                    # 确保结果在0-1之间
                    low_similarity = max(min(low_similarity, Decimal('1')), Decimal('0'))
                    similarity_scores.append(low_similarity)

        # 计算"turnover"指标的相似度
        if "turnover" in indicators:
            turnover_nodes = [date for date in common_dates if
                              'relative_turnover' in G1.nodes[date] and 'relative_turnover' in G2.nodes[date]]
            if turnover_nodes:
                turnover_diff_total = Decimal('0')
                for date in turnover_nodes:
                    node1 = G1.nodes[date]
                    node2 = G2.nodes[date]
                    # 计算相对换手率差异
                    turnover_diff = abs(node1['relative_turnover'] - node2['relative_turnover'])
                    turnover_diff_total += turnover_diff

                # 计算平均差异并转换为相似度分数
                if len(turnover_nodes) > 0:
                    avg_turnover_diff = turnover_diff_total / Decimal(str(len(turnover_nodes)))
                    turnover_similarity = Decimal('1') - avg_turnover_diff  # 直接转换为相似度
                    # 确保结果在0-1之间
                    turnover_similarity = max(min(turnover_similarity, Decimal('1')), Decimal('0'))
                    similarity_scores.append(turnover_similarity)

        # 计算边相似度，仅当有共同边时
        common_edges = set()
        try:
            # 获取两个图的所有边
            G1_edges = [(min(u, v), max(u, v)) for u, v in G1.edges()]
            G2_edges = [(min(u, v), max(u, v)) for u, v in G2.edges()]

            # 找到共同的边
            common_edges = set(G1_edges) & set(G2_edges)
        except Exception as e:
            logger.warning(f"计算边相似度时出错: {e}")

        # 只有当存在共同边时才计算边相似度
        if common_edges:
            edge_diff_total = Decimal('0')
            edge_count = 0

            for edge in common_edges:
                try:
                    # 确保边存在于两个图中
                    if G1.has_edge(*edge) and G2.has_edge(*edge):
                        weight1 = G1.get_edge_data(*edge).get('weight', Decimal('0'))
                        weight2 = G2.get_edge_data(*edge).get('weight', Decimal('0'))
                        edge_diff = abs(weight1 - weight2)
                        edge_diff_total += edge_diff
                        edge_count += 1
                except Exception as e:
                    logger.warning(f"处理边 {edge} 时出错: {e}")
                    continue

            if edge_count > 0:
                avg_edge_diff = edge_diff_total / Decimal(str(edge_count))
                edge_similarity = Decimal('1') - avg_edge_diff
                # 确保结果在0-1之间
                edge_similarity = max(min(edge_similarity, Decimal('1')), Decimal('0'))
                similarity_scores.append(edge_similarity)

        # 如果没有任何相似度分数，返回0
        if not similarity_scores:
            return 0.0

        # 计算所有相似度分数的平均值作为最终相似度
        final_similarity = sum(similarity_scores) / Decimal(str(len(similarity_scores)))

        # 确保结果在0-1之间并返回
        final_similarity = max(min(final_similarity, Decimal('1')), Decimal('0'))
        return float(final_similarity)  # 将Decimal转换为float返回

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
