import pandas as pd
from pydantic import BaseModel
from datetime import date
from typing import List


class ExtractRecord(BaseModel):
    """停牌复牌股票时间"""
    # 证券id 字符串类型
    securityId: str
    # 文章id
    article_id: str
    # 停牌时间 日期类型
    TStime: date
    # 复牌时间 日期类型
    TRtime: date


def to_object_single(row):
    return ExtractRecord(
        securityId=row['security_id'],
        article_id=row['article_id'],
        TStime=row['TStime'].date() if pd.notna(row['TStime']) else None,
        TRtime=row['TRtime'].date() if pd.notna(row['TRtime']) else None
    )


def df_to_objects(df: pd.DataFrame) -> List[ExtractRecord]:
    objects = []
    for _, row in df.iterrows():
        record = ExtractRecord(
            securityId=row['security_id'],
            article_id=row['article_id'],
            TStime=row['TStime_value'].date() if pd.notna(row['TStime_value']) else None,
            TRtime=row['TRtime_value'].date() if pd.notna(row['TRtime_value']) else None
        )
        objects.append(record)
    return objects
