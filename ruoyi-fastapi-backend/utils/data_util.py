import pandas as pd


# 将查询结果转换为 Pandas DataFrame，并返回指定列
# 修改 convert_result_to_dataframe 方法
def convert_result_to_dataframe(result, columns_to_return):
    if not result.result_rows:
        print("警告：result.result_rows 为空，返回空 DataFrame")
        return pd.DataFrame(columns=columns_to_return)

    # 使用查询返回的实际列名
    df = pd.DataFrame(result.result_rows, columns=result.column_names)

    # 打印列名以调试
    print(f"实际列名: {list(df.columns)}")
    print(f"期望列名: {columns_to_return}")

    # 检查 timestamps 列是否存在，如果存在则转换
    if 'timestamps' in df.columns:
        try:
            df['timestamps'] = pd.to_datetime(df['timestamps'])
        except ValueError as e:
            print(f"转换 timestamps 列时出错：{e}")
            pass

    # 检查所有期望的列是否都存在
    missing_columns = [col for col in columns_to_return if col not in df.columns]
    if missing_columns:
        print(f"警告：以下列不存在于查询结果中: {missing_columns}")

        # 创建一个包含所有期望列的新 DataFrame
        new_df = pd.DataFrame(columns=columns_to_return)

        # 将存在的列复制到新 DataFrame
        for col in columns_to_return:
            if col in df.columns:
                new_df[col] = df[col]
            else:
                new_df[col] = None  # 或者设置默认值

        return new_df
    else:
        return df[columns_to_return]
# def convert_result_to_dataframe(result, columns_to_return):
#     df = pd.DataFrame(result.result_rows, columns=result.column_names)
#     return df[columns_to_return]
# def convert_result_to_dataframe(result, columns_to_return):
#
#
#     if not result.result_rows:
#         print("警告：result.result_rows 为空，返回空 DataFrame")
#         return pd.DataFrame(columns=columns_to_return) #返回具有正确列名的空df
#
#     if 'timestamps' not in result.column_names:
#         print("错误：'timestamps' 不在 result.column_names 中")
#         # 1. 如果确定数据库中有 timestamps 列，尝试方案一(见下文)
#         # 2. 如果不确定，或者想直接使用 result.column_names，尝试方案二 (见下文)
#         return pd.DataFrame(columns=columns_to_return) #返回具有正确列名的空df
#
#
#     df = pd.DataFrame(result.result_rows, columns=result.column_names)
#
#     # 确保 timestamps 列存在，并且是字符串类型，然后再转换
#     if 'timestamps' in df.columns:
#         try:
#             df['timestamps'] = pd.to_datetime(df['timestamps'])
#         except ValueError as e:
#             print(f"转换 timestamps 列时出错：{e}")
#             # 在这里可以添加更详细的错误处理，例如检查 timestamps 列的数据类型和值
#             # 或者尝试其他转换方法
#             pass #不做处理
#     else:
#       print("timestamps 列不存在于 DataFrame")
#
#
#     return df[columns_to_return]


def convert_columns_to_float(dataframe, columns):
    for col in columns:
        if col in dataframe.columns:
            dataframe[col] = dataframe[col].astype(float)
    return dataframe


def reset_df_index(df):
    df.reset_index(inplace=True)
    df.index = range(len(df))
    return df
