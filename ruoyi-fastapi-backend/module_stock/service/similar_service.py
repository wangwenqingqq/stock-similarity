from typing import List, Dict, Any, Optional

import networkx as nx
import pandas as pd
import numpy as np
from fastdtw import fastdtw

from entity.vo.kLine_vo import StockBase
from module_stock.dao.similar_dao import SimilarDao
from module_stock.entity.vo.similar_vo import *
import logging
import statsmodels.tsa.stattools as ts
import random
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
                return StockSimilarityResponse(similarStocks=[],performanceData=[])
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
            #5. 获取性能比较数据
            performance_data = await self._get_performance_comparison(
                base_stock_data,
                [stock['code'] for stock in similar_stocks],
            )
            # 6. 构建响应对象
            response = StockSimilarityResponse(
                similarStocks=[
                    SimilarStock(
                        code=stock['code'],
                        name=stock['name'],
                        similarity=stock['similarity']
                    ) for stock in similar_stocks
                ],
                performanceData=performance_data,
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
        elif method == "shape":
            return self._calculate_shape_similarity(stock1_aligned, stock2_aligned, indicators)
        elif method == "position":
            return self._calculate_position_similarity(stock1_aligned, stock2_aligned, indicators)
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
            stock1_close_change = (stock1['close'] - stock1['ycp']) / stock1['ycp']
            stock2_close_change = (stock2['close'] - stock2['ycp']) / stock2['ycp']
            distance, _ = fastdtw(stock1_close_change.values, stock2_close_change.values,
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
            stock1_close_change = (stock1['close'] - stock1['ycp']) / stock1['ycp']
            stock2_close_change = (stock2['close'] - stock2['ycp']) / stock2['ycp']
            _, p_val, _ = ts.coint(stock1_close_change.values, stock2_close_change.values)
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
        similarity = 1/(1+avg_p_val)
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
        try:
            # 1. 数据预处理优化
            if len(stock1) <= 25 or len(stock2) <= 25:
                return 0.0

            # 2. 一次性转换所有数值列
            numeric_cols = ['close', 'high', 'low', 'ycp', 'vol']
            for df in [stock1, stock2]:
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

            # 3. 预计算所有指标的变化率
            changes = {}
            for df, prefix in [(stock1, '1'), (stock2, '2')]:
                changes[f'close_{prefix}'] = (df['close'] - df['ycp']) / df['ycp']
                changes[f'high_{prefix}'] = (df['high'] - df['ycp']) / df['ycp']
                changes[f'low_{prefix}'] = (df['low'] - df['ycp']) / df['ycp']
                changes[f'turnover_{prefix}'] = df['vol'] / df['vol'].max()

            # 4. 使用向量化操作计算相关系数
            pearson_values = []
            for indicator in indicators:
                if indicator == "close":
                    corr = np.corrcoef(changes['close_1'], changes['close_2'])[0, 1]
                elif indicator == "high":
                    corr = np.corrcoef(changes['high_1'], changes['high_2'])[0, 1]
                elif indicator == "low":
                    corr = np.corrcoef(changes['low_1'], changes['low_2'])[0, 1]
                elif indicator == "turnover":
                    corr = np.corrcoef(changes['turnover_1'], changes['turnover_2'])[0, 1]
                
                if not np.isnan(corr):
                    pearson_values.append(corr)

            # 5. 计算最终相似度
            if not pearson_values:
                return 0.0

            avg_pearson = np.mean(pearson_values)
            return max(0.0, avg_pearson) if avg_pearson > 0 else 0.0

        except Exception as e:
            logger.error(f"计算皮尔逊相关系数时出错: {e}")
            return 0.0

    def _calculate_euclidean_similarity(
            self,
            stock1: pd.DataFrame,
            stock2: pd.DataFrame,
            indicators: List[str]
    ) -> float:
        """使用欧氏距离计算两只股票的相似度"""
        # 首先确保所有数值列都是float类型
        numeric_cols = ['close', 'high', 'low', 'ycp', 'vol']
        for col in numeric_cols:
            if col in stock1.columns:
                stock1[col] = stock1[col].astype(float)
            if col in stock2.columns:
                stock2[col] = stock2[col].astype(float)

        distances = []

        if "close" in indicators:
            # 标准化收盘价
            stock1_close_change = (stock1['close'] - stock1['ycp']) / stock1['ycp']
            stock2_close_change = (stock2['close'] - stock2['ycp']) / stock2['ycp']
            dist = np.sqrt(np.sum((stock1_close_change.values - stock2_close_change.values) ** 2))
            distances.append(dist)

        # 其余代码保持不变...

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
        G = nx.Graph()
        # 首先确保所有数值列都是float类型
        numeric_cols = ['close', 'high', 'low', 'ycp', 'vol']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].astype(float)
        # 确保df有一个副本以避免修改原始数据
        df = df.copy()

        # 预先计算相对换手率，如果需要且有相关数据
        if "turnover" in indicators and 'vol' in df.columns:
            max_vol = df['vol'].max()
            if max_vol != 0:
                df['relative_turnover'] = df['vol'].apply(lambda x: x / max_vol)
            else:
                df['relative_turnover'] = df['vol'].apply(lambda x: float('0'))

        # 为每个交易日创建节点，只包含指定的指标特征
        for idx, row in df.iterrows():
            node_features = {'date': idx}

            # 根据指定的指标添加对应的特征，但要确保列存在
            if "close" in indicators and 'close' in df.columns:
                close_change = (row['close'] - row['ycp']) / row['ycp'] if row['ycp'] != 0 else float('0')
                node_features['close_change'] = close_change
            if "high" in indicators and 'high' in df.columns and 'ycp' in df.columns:
                # 计算最高价涨幅
                high_change = (row['high'] - row['ycp']) / row['ycp'] if row['ycp'] != 0 else float('0')
                node_features['high_change'] = high_change

            if "low" in indicators and 'low' in df.columns and 'ycp' in df.columns:
                # 计算最低价涨幅
                low_change = (row['low'] - row['ycp']) / row['ycp'] if row['ycp'] != 0 else float('0')
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
            edge_weight = float('0')
            edge_count = 0

            # 根据指定的指标计算边的权重，检查特征是否存在
            if "close" in indicators and 'close_change' in G.nodes[current_date] and 'close_change' in G.nodes[next_date]:
                close_diff = abs(G.nodes[next_date]['close_change'] - G.nodes[current_date]['close_change'])
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
                edge_weight = edge_weight / float(str(edge_count))
            else:
                edge_weight = float('0')  # 如果没有共同特征，设置权重为0

            G.add_edge(current_date, next_date, weight=edge_weight)
        return G

    def _calculate_mcs_similarity(self, G1: nx.Graph, G2: nx.Graph, indicators: List[str]) -> float:
        """
        计算两个图之间的最大公共子图相似度，添加性能限制和内存保护
        """
        # 如果任一图为空，则返回0
        if G1.number_of_nodes() == 0 or G2.number_of_nodes() == 0:
            return 0.0

        # 添加节点数量限制
        MAX_NODES = 100  # 设置最大节点数限制
        if G1.number_of_nodes() > MAX_NODES or G2.number_of_nodes() > MAX_NODES:
            logger.warning(f"图节点数超过限制: G1={G1.number_of_nodes()}, G2={G2.number_of_nodes()}")
            # 如果节点数过多，使用简化的相似度计算方法
            return self._calculate_simplified_similarity(G1, G2, indicators)

        try:
            # 1. 构建产品图，使用更高效的数据结构
            product_graph = nx.Graph()
            node_pairs = []

            # 2. 预计算节点特征，减少重复计算
            node_features = {}
            for node1 in G1.nodes():
                for node2 in G2.nodes():
                    # 检查两个节点是否有相同的特征集
                    compatible = True
                    for indicator in indicators:
                        if not self._check_node_compatibility(G1.nodes[node1], G2.nodes[node2], indicator):
                            compatible = False
                            break

                    if compatible:
                        node_pairs.append((node1, node2))

            # 3. 批量添加节点
            for node_pair in node_pairs:
                product_graph.add_node(node_pair)

            # 4. 优化边添加过程
            for i, (node1_a, node2_a) in enumerate(node_pairs):
                for node1_b, node2_b in node_pairs[i+1:]:
                    if self._check_edge_compatibility(G1, G2, node1_a, node2_a, node1_b, node2_b):
                        weight_sim = self._calculate_edge_similarity(G1, G2, node1_a, node2_a, node1_b, node2_b)
                        if weight_sim > 0.0001:
                            product_graph.add_edge((node1_a, node2_a), (node1_b, node2_b), weight=weight_sim)

            # 5. 使用改进的贪婪算法寻找最大团
            max_clique = self._find_max_clique(product_graph)

            # 6. 计算相似度
            mcs_size = len(max_clique)
            g1_size = G1.number_of_nodes()
            g2_size = G2.number_of_nodes()

            # 使用Tanimoto系数计算相似度
            similarity = float(mcs_size) / (float(g1_size) + float(g2_size) - float(mcs_size))
            return float(similarity)

        except Exception as e:
            logger.error(f"计算最大公共子图相似度时出错: {e}")
            return 0.0

    def _check_node_compatibility(self, node1_features, node2_features, indicator):
        """检查两个节点的特征是否兼容"""
        if indicator == "close":
            return 'close_change' in node1_features and 'close_change' in node2_features
        elif indicator == "high":
            return 'high_change' in node1_features and 'high_change' in node2_features
        elif indicator == "low":
            return 'low_change' in node1_features and 'low_change' in node2_features
        elif indicator == "turnover":
            return 'relative_turnover' in node1_features and 'relative_turnover' in node2_features
        return False

    def _check_edge_compatibility(self, G1, G2, node1_a, node2_a, node1_b, node2_b):
        """检查边是否兼容"""
        return (G1.has_edge(node1_a, node1_b) and G2.has_edge(node2_a, node2_b))

    def _calculate_edge_similarity(self, G1, G2, node1_a, node2_a, node1_b, node2_b):
        """计算边相似度"""
        weight1 = G1[node1_a][node1_b]['weight']
        weight2 = G2[node2_a][node2_b]['weight']
        return 1.0 - abs(weight1 - weight2)

    def _find_max_clique(self, graph):
        """使用改进的贪婪算法寻找最大团"""
        if not graph.nodes():
            return []

        # 按度数排序节点
        nodes_by_degree = sorted(graph.nodes(),
                               key=lambda n: graph.degree(n),
                               reverse=True)

        max_clique = []
        for node in nodes_by_degree:
            if all(graph.has_edge(node, clique_node) for clique_node in max_clique):
                max_clique.append(node)

        return max_clique

    def _calculate_simplified_similarity(self, G1: nx.Graph, G2: nx.Graph, indicators: List[str]) -> float:
        """
        当图规模过大时使用的简化相似度计算方法
        """
        try:
            # 1. 随机采样节点
            sample_size = min(50, min(G1.number_of_nodes(), G2.number_of_nodes()))
            G1_nodes = random.sample(list(G1.nodes()), sample_size)
            G2_nodes = random.sample(list(G2.nodes()), sample_size)

            # 2. 计算节点特征相似度
            feature_similarities = []
            for indicator in indicators:
                if indicator == "close":
                    feature_similarities.append(self._calculate_feature_similarity(G1, G2, G1_nodes, G2_nodes, 'close_change'))
                elif indicator == "high":
                    feature_similarities.append(self._calculate_feature_similarity(G1, G2, G1_nodes, G2_nodes, 'high_change'))
                elif indicator == "low":
                    feature_similarities.append(self._calculate_feature_similarity(G1, G2, G1_nodes, G2_nodes, 'low_change'))
                elif indicator == "turnover":
                    feature_similarities.append(self._calculate_feature_similarity(G1, G2, G1_nodes, G2_nodes, 'relative_turnover'))

            # 3. 返回平均相似度
            return sum(feature_similarities) / len(feature_similarities) if feature_similarities else 0.0

        except Exception as e:
            logger.error(f"计算简化相似度时出错: {e}")
            return 0.0

    def _calculate_feature_similarity(self, G1, G2, G1_nodes, G2_nodes, feature_name):
        """计算特定特征的相似度"""
        try:
            values1 = [G1.nodes[node][feature_name] for node in G1_nodes if feature_name in G1.nodes[node]]
            values2 = [G2.nodes[node][feature_name] for node in G2_nodes if feature_name in G2.nodes[node]]
            
            if not values1 or not values2:
                return 0.0

            # 计算特征值的统计相似度
            mean1, mean2 = np.mean(values1), np.mean(values2)
            std1, std2 = np.std(values1), np.std(values2)
            
            if std1 == 0 or std2 == 0:
                return 0.0

            # 使用统计特征的相似度
            mean_sim = 1.0 / (1.0 + abs(mean1 - mean2))
            std_sim = 1.0 / (1.0 + abs(std1 - std2))
            
            return (mean_sim + std_sim) / 2.0

        except Exception as e:
            logger.error(f"计算特征相似度时出错: {e}")
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
        logger.warning("==== 进入图编辑距离相似度计算 ====")
        # 获取两个图的共同节点
        common_dates = set(G1.nodes()) & set(G2.nodes())
        if not common_dates:
            return 0.0
        logger.warning(f"共同节点数: {len(common_dates)}")

        # 为每个指标单独计算相似度
        similarity_scores = []

        # 对于每个指标，首先检查所有共同节点是否都有该特征
        # 计算"close"指标的相似度
        if "close" in indicators:
            close_nodes = [date for date in common_dates if 'close_change' in G1.nodes[date] and 'close_change' in G2.nodes[date]]
            if close_nodes:
                close_diff_total = float('0')
                for date in close_nodes:
                    node1 = G1.nodes[date]
                    node2 = G2.nodes[date]
                    # 计算收盘价差异
                    close_diff = abs(node1['close_change'] - node2['close_change'])

                    close_diff_total += close_diff

                # 计算平均差异并转换为相似度分数
                if len(close_nodes) > 0:
                    avg_close_diff = close_diff_total / float(len(close_nodes))
                    close_similarity = 1.0 / (1.0 + avg_close_diff)  # 距离越大相似度越小，但不会直接为0
                    logger.warning(f"close指标: 平均差异={avg_close_diff}, 相似度={close_similarity}")
                    # 确保结果在0-1之间
                    close_similarity = max(min(close_similarity, float('1')), float('0'))
                    similarity_scores.append(close_similarity)

        # 计算"high"指标的相似度
        if "high" in indicators:
            high_nodes = [date for date in common_dates if
                          'high_change' in G1.nodes[date] and 'high_change' in G2.nodes[date]]
            if high_nodes:
                high_diff_total = float('0')
                for date in high_nodes:
                    node1 = G1.nodes[date]
                    node2 = G2.nodes[date]
                    # 计算最高价涨幅差异
                    high_diff = abs(node1['high_change'] - node2['high_change'])
                    high_diff_total += high_diff

                # 计算平均差异并转换为相似度分数
                if len(high_nodes) > 0:
                    avg_high_diff = high_diff_total / float(str(len(high_nodes)))
                    high_similarity = float('1') / (float('1') + avg_high_diff)  # 使用倒数转换为相似度
                    logger.warning(f"high指标: 平均差异={avg_high_diff}, 相似度={high_similarity}")
                    # 确保结果在0-1之间
                    high_similarity = max(min(high_similarity, float('1')), float('0'))
                    similarity_scores.append(high_similarity)

        # 计算"low"指标的相似度
        if "low" in indicators:
            low_nodes = [date for date in common_dates if
                         'low_change' in G1.nodes[date] and 'low_change' in G2.nodes[date]]
            if low_nodes:
                low_diff_total = float('0')
                for date in low_nodes:
                    node1 = G1.nodes[date]
                    node2 = G2.nodes[date]
                    # 计算最低价涨幅差异
                    low_diff = abs(node1['low_change'] - node2['low_change'])
                    low_diff_total += low_diff

                # 计算平均差异并转换为相似度分数
                if len(low_nodes) > 0:
                    avg_low_diff = low_diff_total / float(str(len(low_nodes)))
                    low_similarity = float('1') / (float('1') + avg_low_diff)  # 使用倒数转换为相似度
                    logger.warning(f"low指标: 平均差异={avg_low_diff}, 相似度={low_similarity}")
                    # 确保结果在0-1之间
                    low_similarity = max(min(low_similarity, float('1')), float('0'))
                    similarity_scores.append(low_similarity)

        # 计算"turnover"指标的相似度
        if "turnover" in indicators:
            turnover_nodes = [date for date in common_dates if
                              'relative_turnover' in G1.nodes[date] and 'relative_turnover' in G2.nodes[date]]
            if turnover_nodes:
                turnover_diff_total = float('0')
                for date in turnover_nodes:
                    node1 = G1.nodes[date]
                    node2 = G2.nodes[date]
                    # 计算相对换手率差异
                    turnover_diff = abs(node1['relative_turnover'] - node2['relative_turnover'])
                    turnover_diff_total += turnover_diff

                # 计算平均差异并转换为相似度分数
                if len(turnover_nodes) > 0:
                    avg_turnover_diff = turnover_diff_total / float(str(len(turnover_nodes)))
                    turnover_similarity = float('1') - avg_turnover_diff  # 直接转换为相似度
                    logger.warning(f"turnover指标: 平均差异={avg_turnover_diff}, 相似度={turnover_similarity}")
                    # 确保结果在0-1之间
                    turnover_similarity = max(min(turnover_similarity, float('1')), float('0'))
                    similarity_scores.append(turnover_similarity)

        # 计算边相似度，仅当有共同边时
        common_edges = set()
        try:
            # 获取两个图的所有边
            G1_edges = [(min(u, v), max(u, v)) for u, v in G1.edges()]
            G2_edges = [(min(u, v), max(u, v)) for u, v in G2.edges()]

            # 找到共同的边
            common_edges = set(G1_edges) & set(G2_edges)
            logger.warning(f"共同边数: {len(common_edges)}")
        except Exception as e:
            logger.warning(f"计算边相似度时出错: {e}")

        # 只有当存在共同边时才计算边相似度
        if common_edges:
            edge_diff_total = float('0')
            edge_count = 0

            for edge in common_edges:
                try:
                    # 确保边存在于两个图中
                    if G1.has_edge(*edge) and G2.has_edge(*edge):
                        weight1 = G1.get_edge_data(*edge).get('weight', float('0'))
                        weight2 = G2.get_edge_data(*edge).get('weight', float('0'))
                        edge_diff = abs(weight1 - weight2)
                        edge_diff_total += edge_diff
                        edge_count += 1
                except Exception as e:
                    logger.warning(f"处理边 {edge} 时出错: {e}")
                    continue

            if edge_count > 0:
                avg_edge_diff = edge_diff_total / float(edge_count)
                edge_similarity = 1.0 / (1.0 + avg_edge_diff)  # 距离越大相似度越小，但不会直接为0
                logger.warning(f"边相似度: 平均差异={avg_edge_diff}, 相似度={edge_similarity}")
                # 确保结果在0-1之间
                edge_similarity = max(min(edge_similarity, float('1')), float('0'))
                similarity_scores.append(edge_similarity)

        # 如果没有任何相似度分数，返回0
        if not similarity_scores:
            return 0.0

        # 计算所有相似度分数的平均值作为最终相似度
        final_similarity = sum(similarity_scores) / float(len(similarity_scores))

        # 确保结果在0-1之间并返回
        final_similarity = max(min(final_similarity, float('1')), float('0'))
        logger.warning(f"所有分数: {similarity_scores}")
        logger.warning(f"最终相似度: {final_similarity}")
        return float(final_similarity)  # 将float转换为float返回

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

    def _calculate_shape_similarity(
            self,
            stock1: pd.DataFrame,
            stock2: pd.DataFrame,
            indicators: List[str]
    ) -> float:
        """使用K线形状（上影线、实体、下影线）计算两只股票的相似度

        Args:
            stock1: 第一只股票数据
            stock2: 第二只股票数据
            indicators: 用于计算的指标列表（未用到，可保留）

        Returns:
            float: 相似度得分
        """
        # 权重设置
        upper_weight = 0.33
        body_weight = 0.34
        lower_weight = 0.33
        # 首先确保所有数值列都是float类型
        numeric_cols = ['close', 'high', 'low', 'ycp','open']
        for col in numeric_cols:
            if col in stock1.columns:
                stock1[col] = stock1[col].astype(float)
            if col in stock2.columns:
                stock2[col] = stock2[col].astype(float)
        # 对齐日期
        common_dates = stock1.index.intersection(stock2.index)
        if len(common_dates) < 2:
            logger.warning("股票对的共同交易日少于2天，无法计算形状相似度")
            return 0.0

        stock1_aligned = stock1.loc[common_dates]
        stock2_aligned = stock2.loc[common_dates]

        # 计算上影线、实体、下影线长度序列
        def calc_shape_parts(df):
            # 上影线
            upper = np.where(
                df['open'] > df['close'],
                (df['high'] - df['open']) / (df['ycp'] * 0.1),
                (df['high'] - df['close']) / (df['ycp'] * 0.1)
            )
            # 下影线
            lower = np.where(
                df['open'] > df['close'],
                (df['close'] - df['low']) / (df['ycp'] * 0.1),
                (df['open'] - df['low']) / (df['ycp'] * 0.1)
            )
            # 实体
            body = np.abs(df['open'] - df['close']) / (df['ycp'] * 0.1)
            return upper, body, lower

        upper1, body1, lower1 = calc_shape_parts(stock1_aligned)
        upper2, body2, lower2 = calc_shape_parts(stock2_aligned)

        # 计算各部分的总和
        sum_upper1, sum_upper2 = np.sum(upper1), np.sum(upper2)
        sum_body1, sum_body2 = np.sum(body1), np.sum(body2)
        sum_lower1, sum_lower2 = np.sum(lower1), np.sum(lower2)

        # 相似度计算函数
        def part_similarity(sum1, sum2):
            if sum1 == 0 and sum2 == 0:
                return 1.0
            if (sum1 == 0 and sum2 != 0) or (sum1 != 0 and sum2 == 0):
                return 0.0
            return min(sum1, sum2) / max(sum1, sum2)

        upper_sim = part_similarity(sum_upper1, sum_upper2)
        body_sim = part_similarity(sum_body1, sum_body2)
        lower_sim = part_similarity(sum_lower1, sum_lower2)

        # 加权总相似度
        similarity = upper_weight * upper_sim + body_weight * body_sim + lower_weight * lower_sim
        return float(similarity)

    def _calculate_position_similarity(
            self,
            stock1: pd.DataFrame,
            stock2: pd.DataFrame,
            indicators: List[str]
    ) -> float:
        """
        使用位置序列计算两只股票的相似度

        位置定义：
        - 第一天位置为1
        - 之后的位置为 (收盘价-作收价)/(作收价*0.1)

        两个序列的位置相似性 = 较小的所有天数的位置和 / 较大的所有天数位置和
        如果有且只有一个位置和为0，则相似度为0；如果两个都是0，则相似度为1。

        Args:
            stock1: 第一只股票数据
            stock2: 第二只股票数据
            indicators: 用于计算的指标列表（未用到，可保留）

        Returns:
            float: 相似度得分
        """
        numeric_cols = ['close','ycp']
        for col in numeric_cols:
            if col in stock1.columns:
                stock1[col] = stock1[col].astype(float)
            if col in stock2.columns:
                stock2[col] = stock2[col].astype(float)
        # 对齐日期
        common_dates = stock1.index.intersection(stock2.index)
        if len(common_dates) < 2:
            logger.warning("股票对的共同交易日少于2天，无法计算位置相似度")
            return 0.0

        stock1_aligned = stock1.loc[common_dates]
        stock2_aligned = stock2.loc[common_dates]

        # 计算位置序列
        def calc_position(df):
            pos = np.zeros(len(df))
            pos[0] = 1  # 第一天为1
            if len(df) > 1:
                # 从第二天开始
                pos[1:] = (df['close'].values[1:] - df['ycp'].values[1:]) / (df['ycp'].values[1:] * 0.1)
            return pos

        pos1 = calc_position(stock1_aligned)
        pos2 = calc_position(stock2_aligned)

        sum_pos1 = np.sum(pos1)
        sum_pos2 = np.sum(pos2)

        # 相似度计算
        if sum_pos1 == 0 and sum_pos2 == 0:
            return 1.0
        if (sum_pos1 == 0 and sum_pos2 != 0) or (sum_pos1 != 0 and sum_pos2 == 0):
            return 0.0
        similarity = min(sum_pos1, sum_pos2) / max(sum_pos1, sum_pos2)
        return float(similarity)

    async def search_history(self, keyword: str) -> List[StockBase]:
        """
        搜索查询历史（支持模糊搜索）

        Args:
            keyword: 搜索关键词

        Returns:
            List[StockBase]: 搜索结果响应
        """
        try:
            # 调用DAO层搜索历史
            results = await SimilarDao.search_history(keyword)

            # 构建响应对象列表
            response = []
            for row in results:
                # 假设 row 是 dict 或有 code/name 属性
                stock = StockBase(
                    code=row.get("code", "") if isinstance(row, dict) else getattr(row, "code", ""),
                    name=row.get("name", "") if isinstance(row, dict) else getattr(row, "name", "")
                )
                response.append(stock)

            return response
        except Exception as e:
            logger.error(f"搜索查询历史出错: {e}")
            raise