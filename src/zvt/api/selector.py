# -*- coding: utf-8 -*-
import pandas as pd
from sqlalchemy import or_

from zvt.api.kdata import default_adjust_type, get_kdata_schema
from zvt.contract import IntervalLevel
from zvt.domain import DragonAndTiger, Stock1dHfqKdata
from zvt.utils import to_pd_timestamp, next_date

# 500亿
BIG_CAP = 50000000000
# 150亿
MIDDLE_CAP = 15000000000
# 40亿
SMALL_CAP = 4000000000


def get_dragon_and_tigger_player(start_timestamp, end_timestamp=None, direction="in"):
    assert direction in ("in", "out")

    filters = None
    if direction == "in":
        filters = [DragonAndTiger.change_pct > 0]
        columns = ["dep1", "dep2", "dep3"]
    elif direction == "out":
        filters = [DragonAndTiger.change_pct > 0]
        columns = ["dep_1", "dep_2", "dep_3"]

    df = DragonAndTiger.query_data(start_timestamp=start_timestamp, end_timestamp=end_timestamp, filters=filters)
    counts = []
    for col in columns:
        counts.append(df[[col, f"{col}_rate"]].groupby(col).count().sort_values(f"{col}_rate", ascending=False))
    return counts


def get_big_players(start_timestamp, end_timestamp=None, count=40):
    dep1, dep2, dep3 = get_dragon_and_tigger_player(start_timestamp=start_timestamp, end_timestamp=end_timestamp)
    # 榜1前40
    top1 = dep1.index.tolist()[:count]

    # 榜2前40
    bang2 = dep2.index.tolist()[:count]
    top2 = list(set(bang2) - set(top1))

    # 榜3前40
    bang3 = dep3.index.tolist()[:count]
    top3 = list(set(bang3) - set(top1) - set(top2))

    return top1 + top2 + top3


def get_player_performance(start_timestamp, end_timestamp=None, days=5, player="机构专用", provider="em"):
    filters = [or_(DragonAndTiger.dep1 == player, DragonAndTiger.dep2 == player, DragonAndTiger.dep3 == player)]
    df = DragonAndTiger.query_data(
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        filters=filters,
        index=["entity_id", "timestamp"],
        provider=provider,
    )
    df = df[~df.index.duplicated(keep="first")]
    records = []
    for entity_id, timestamp in df.index:
        end_date = next_date(timestamp, days + round(days * 2 / 5 + 30))
        kdata = Stock1dHfqKdata.query_data(
            entity_id=entity_id,
            start_timestamp=timestamp,
            end_timestamp=end_date,
            provider=provider,
            index="timestamp",
        )
        end_index = min(days, len(kdata) - 1)
        close = kdata["close"]
        change_pct = (close[end_index] - close[0]) / close[0]
        records.append({"entity_id": entity_id, "timestamp": timestamp, f"change_pct": change_pct})
    return pd.DataFrame.from_records(records)


def get_player_success_rate(
    start_timestamp,
    end_timestamp=None,
    intervals=(5, 10, 20, 60, 90),
    players=("机构专用", "东方财富证券股份有限公司拉萨团结路第二证券营业部"),
    provider="em",
):
    records = []
    for player in players:
        record = {"player": player}
        for days in intervals:
            df = get_player_performance(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                days=days,
                player=player,
                provider=provider,
            )
            rate = len(df[df["change_pct"] > 0]) / len(df)
            record[f"rate_{days}"] = rate
        records.append(record)
    return pd.DataFrame.from_records(records, index="player")


def get_entity_list_by_cap(timestamp, cap_start, cap_end, entity_type="stock", provider=None, adjust_type=None):
    if not adjust_type:
        adjust_type = default_adjust_type(entity_type=entity_type)

    kdata_schema = get_kdata_schema(entity_type, level=IntervalLevel.LEVEL_1DAY, adjust_type=adjust_type)
    df = kdata_schema.query_data(
        provider=provider,
        filters=[kdata_schema.timestamp == to_pd_timestamp(timestamp)],
        index="entity_id",
    )
    df["cap"] = df["turnover"] / df["turnover_rate"]
    df_result = df.copy()
    if cap_start:
        df_result = df_result.loc[(df["cap"] >= cap_start)]
    if cap_end:
        df_result = df_result.loc[(df["cap"] <= cap_end)]
    return df_result.index.tolist()


def get_big_cap_stock(timestamp, provider="em"):
    return get_entity_list_by_cap(
        timestamp=timestamp, cap_start=BIG_CAP, cap_end=None, entity_type="stock", provider=provider
    )


def get_middle_cap_stock(timestamp, provider="em"):
    return get_entity_list_by_cap(
        timestamp=timestamp, cap_start=MIDDLE_CAP, cap_end=BIG_CAP, entity_type="stock", provider=provider
    )


def get_small_cap_stock(timestamp, provider="em"):
    return get_entity_list_by_cap(
        timestamp=timestamp, cap_start=SMALL_CAP, cap_end=MIDDLE_CAP, entity_type="stock", provider=provider
    )


def get_mini_cap_stock(timestamp, provider="em"):
    return get_entity_list_by_cap(
        timestamp=timestamp, cap_start=None, cap_end=SMALL_CAP, entity_type="stock", provider=provider
    )


def get_mini_and_small_stock(timestamp, provider="em"):
    return get_entity_list_by_cap(
        timestamp=timestamp, cap_start=None, cap_end=MIDDLE_CAP, entity_type="stock", provider=provider
    )


def get_middle_and_big_stock(timestamp, provider="em"):
    return get_entity_list_by_cap(
        timestamp=timestamp, cap_start=MIDDLE_CAP, cap_end=None, entity_type="stock", provider=provider
    )


if __name__ == "__main__":
    # target_date = get_latest_kdata_date(provider="em", entity_type="stock", adjust_type=AdjustType.hfq)
    # big = get_big_cap_stock(timestamp=target_date)
    # print(len(big))
    # print(big)
    # middle = get_middle_cap_stock(timestamp=target_date)
    # print(len(middle))
    # print(middle)
    # small = get_small_cap_stock(timestamp=target_date)
    # print(len(small))
    # print(small)
    # mini = get_mini_cap_stock(timestamp=target_date)
    # print(len(mini))
    # print(mini)
    df = get_player_performance(start_timestamp="2022-01-01")
    print(df)
# the __all__ is generated
__all__ = [
    "get_dragon_and_tigger_player",
    "get_big_players",
    "get_player_performance",
    "get_player_success_rate",
    "get_entity_list_by_cap",
    "get_big_cap_stock",
    "get_middle_cap_stock",
    "get_small_cap_stock",
    "get_mini_cap_stock",
    "get_mini_and_small_stock",
    "get_middle_and_big_stock",
]
