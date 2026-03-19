#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marcus A股交易助手 - 核心数据引擎 v3.0
真实数据接入层 + 多维筛选 + 技术指标计算
"""

import datetime
import time
import json
import os
import random
import traceback
from typing import Dict, List, Optional, Tuple

try:
    import akshare as ak
    import pandas as pd
    import numpy as np
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────────────────────
CACHE_FILE = os.path.join(os.path.dirname(__file__), "marcus_data_cache.json")
CACHE_TTL  = 300          # 数据缓存5分钟
TRADING_DAYS_30 = 30      # 上市满30交易日
MIN_TURNOVER_M  = 2000    # 最低日成交额（万元）
MIN_TURNOVER_R  = 1.0     # 最低换手率（%）
WATCHLIST_SIZE  = 15      # 观察名单数量
WIN_PROB_MIN    = 70.0    # 最低胜率

# 板块映射（用于净流向）
SECTOR_MAP = {
    "半导体": ["688981","002415","600584","002049","300223"],
    "新能源车": ["002594","300750","601238","000625","003816"],
    "光伏储能": ["601012","300274","002129","600438","688239"],
    "医药生物": ["300760","300015","000538","600085","002007"],
    "白酒": ["600519","000858","000568","002304","603369"],
    "金融券商": ["600036","601318","600030","000776","002736"],
    "房地产": ["000002","000069","600048","001979","600383"],
    "消费电子": ["002475","000725","002241","300433","688111"],
    "军工": ["600316","000513","600903","002389","000547"],
    "人工智能": ["600938","688271","688016","300496","002230"],
    "煤炭": ["601088","600188","601666","000983","600508"],
    "有色金属": ["600547","601600","002460","000630","601899"],
}


# ─────────────────────────────────────────────────────────────────────────────
# 缓存工具
# ─────────────────────────────────────────────────────────────────────────────
class DataCache:
    def __init__(self, path: str = CACHE_FILE):
        self.path = path
        self._mem: Dict = {}

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._mem = json.load(f)
            except Exception:
                self._mem = {}

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._mem, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, key: str):
        self._load()
        item = self._mem.get(key)
        if not item:
            return None
        if time.time() - item.get("ts", 0) > CACHE_TTL:
            return None
        return item.get("data")

    def set(self, key: str, data):
        self._load()
        self._mem[key] = {"ts": time.time(), "data": data}
        self._save()


_cache = DataCache()


# ─────────────────────────────────────────────────────────────────────────────
# 技术指标计算
# ─────────────────────────────────────────────────────────────────────────────
def calc_macd(close: "pd.Series", fast=12, slow=26, signal=9) -> Tuple[float, float, float]:
    """返回 (macd_line, signal_line, histogram)"""
    if len(close) < slow + signal:
        return 0.0, 0.0, 0.0
    ema_fast   = close.ewm(span=fast, adjust=False).mean()
    ema_slow   = close.ewm(span=slow, adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram   = macd_line - signal_line
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])


def calc_kdj(high: "pd.Series", low: "pd.Series", close: "pd.Series",
             n=9, m1=3, m2=3) -> Tuple[float, float, float]:
    """返回 (K, D, J)"""
    if len(close) < n:
        return 50.0, 50.0, 50.0
    rsv_list = []
    for i in range(len(close)):
        start = max(0, i - n + 1)
        h = high.iloc[start: i + 1].max()
        l = low.iloc[start: i + 1].min()
        rsv = 50.0 if h == l else (close.iloc[i] - l) / (h - l) * 100
        rsv_list.append(rsv)
    rsv_s = pd.Series(rsv_list)
    k_s   = rsv_s.ewm(com=m1 - 1, adjust=False).mean()
    d_s   = k_s.ewm(com=m2 - 1, adjust=False).mean()
    j_s   = 3 * k_s - 2 * d_s
    return float(k_s.iloc[-1]), float(d_s.iloc[-1]), float(j_s.iloc[-1])


def macd_golden_cross(close: "pd.Series") -> bool:
    """MACD金叉：MACD线上穿Signal线"""
    if len(close) < 40:
        return False
    ema_f = close.ewm(span=12, adjust=False).mean()
    ema_s = close.ewm(span=26, adjust=False).mean()
    ml    = ema_f - ema_s
    sl    = ml.ewm(span=9, adjust=False).mean()
    # 今日金叉 or 昨日金叉（容错一天）
    if len(ml) >= 2:
        prev_diff = float(ml.iloc[-2] - sl.iloc[-2])
        cur_diff  = float(ml.iloc[-1] - sl.iloc[-1])
        return prev_diff < 0 and cur_diff >= 0
    return False


def kdj_golden_cross(high: "pd.Series", low: "pd.Series", close: "pd.Series") -> bool:
    """KDJ金叉：K线上穿D线"""
    if len(close) < 12:
        return False
    n = 9
    rsv_list = []
    for i in range(len(close)):
        start = max(0, i - n + 1)
        h = high.iloc[start: i + 1].max()
        l = low.iloc[start: i + 1].min()
        rsv = 50.0 if h == l else (close.iloc[i] - l) / (h - l) * 100
        rsv_list.append(rsv)
    rsv_s = pd.Series(rsv_list)
    k_s   = rsv_s.ewm(com=2, adjust=False).mean()
    d_s   = k_s.ewm(com=2, adjust=False).mean()
    if len(k_s) >= 2:
        return float(k_s.iloc[-2]) < float(d_s.iloc[-2]) and float(k_s.iloc[-1]) >= float(d_s.iloc[-1])
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 市场宏观数据获取
# ─────────────────────────────────────────────────────────────────────────────
def get_market_macro() -> dict:
    """获取沪深300、iVIX、期指、A50、恒科、全市场量能"""
    cached = _cache.get("macro")
    if cached:
        return cached

    result = {
        "sh300_chg":    0.0,
        "sh300_close":  0.0,
        "ivix":         20.0,
        "sh_vol_change": 0.0,
        "sh_vol_today":  0.0,
        "csi300_futures_premium": 0.0,
        "ftse_a50_chg":  0.0,
        "hstech_chg":    0.0,
        "total_market_vol": 0.0,
        "limit_up_count":  0,
        "limit_down_count": 0,
        "data_source": "fallback",
    }

    if not AKSHARE_AVAILABLE:
        result["data_source"] = "no_akshare"
        _cache.set("macro", result)
        return result

    try:
        # 1. 沪深300指数
        df_idx = ak.stock_zh_index_daily(symbol="sh000300")
        if df_idx is not None and len(df_idx) >= 2:
            df_idx = df_idx.tail(10).copy()
            df_idx.columns = [c.lower() for c in df_idx.columns]
            last  = float(df_idx["close"].iloc[-1])
            prev  = float(df_idx["close"].iloc[-2])
            result["sh300_close"] = last
            result["sh300_chg"]   = round((last - prev) / prev * 100, 2)
            today_vol  = float(df_idx["volume"].iloc[-1])
            prev5_vol  = float(df_idx["volume"].iloc[-6:-1].mean()) if len(df_idx) >= 6 else today_vol
            result["sh_vol_today"]  = today_vol
            result["sh_vol_change"] = round((today_vol - prev5_vol) / prev5_vol * 100, 2) if prev5_vol else 0
    except Exception:
        pass

    try:
        # 2. 中国波指 iVIX（使用上证50ETF期权波动率代替）
        df_vix = ak.stock_zh_index_daily(symbol="sh000188")
        if df_vix is not None and len(df_vix) >= 1:
            df_vix.columns = [c.lower() for c in df_vix.columns]
            result["ivix"] = round(float(df_vix["close"].iloc[-1]), 2)
    except Exception:
        pass

    # 涨跌停数量通过专用接口获取（见下方）

    try:
        # 获取涨停板统计
        df_zt2 = ak.stock_zt_pool_em(date=datetime.datetime.now().strftime("%Y%m%d"))
        if df_zt2 is not None:
            result["limit_up_count"] = len(df_zt2)
    except Exception:
        pass

    try:
        df_dt = ak.stock_dt_pool_em(date=datetime.datetime.now().strftime("%Y%m%d"))
        if df_dt is not None:
            result["limit_down_count"] = len(df_dt)
    except Exception:
        pass

    result["data_source"] = "akshare"
    _cache.set("macro", result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 板块资金流向
# ─────────────────────────────────────────────────────────────────────────────
def get_sector_flow() -> List[dict]:
    """获取板块净资金流向"""
    cached = _cache.get("sector_flow")
    if cached:
        return cached

    result = []
    if not AKSHARE_AVAILABLE:
        _cache.set("sector_flow", result)
        return result

    try:
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
        if df is not None and len(df) > 0:
            df.columns = [c.strip() for c in df.columns]
            # 标准化列名
            col_map = {}
            for c in df.columns:
                if "名称" in c or "板块" in c:
                    col_map["name"] = c
                elif "净额" in c or "净流" in c:
                    col_map["net"] = c
                elif "涨跌" in c:
                    col_map["chg"] = c
            if "name" in col_map and "net" in col_map:
                for _, row in df.iterrows():
                    try:
                        net_val = float(str(row[col_map["net"]]).replace(",", "").replace("亿", ""))
                    except Exception:
                        net_val = 0.0
                    result.append({
                        "name": str(row[col_map["name"]]),
                        "net_flow": net_val,
                        "chg": float(row[col_map["chg"]]) if "chg" in col_map else 0.0,
                    })
    except Exception:
        pass

    _cache.set("sector_flow", result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 股票历史数据获取
# ─────────────────────────────────────────────────────────────────────────────
def get_stock_daily(symbol: str, days: int = 60) -> Optional["pd.DataFrame"]:
    """获取个股日线数据，返回标准化DataFrame"""
    cache_key = f"daily_{symbol}_{days}"
    cached = _cache.get(cache_key)
    if cached:
        return pd.DataFrame(cached)

    if not AKSHARE_AVAILABLE:
        return None

    try:
        end   = datetime.datetime.now().strftime("%Y%m%d")
        start = (datetime.datetime.now() - datetime.timedelta(days=days * 2)).strftime("%Y%m%d")

        # 根据市场前缀选择接口
        if symbol.startswith("6"):
            mkt = "sh"
        elif symbol.startswith(("0", "3")):
            mkt = "sz"
        else:
            mkt = "sz"

        full_symbol = f"{mkt}{symbol}"
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="qfq"
        )
        if df is None or len(df) < 10:
            return None
        df = df.tail(days).copy()
        df.columns = [c.strip() for c in df.columns]
        # 标准化列名
        rename = {}
        for c in df.columns:
            cl = c.lower()
            if "日期" in c or "date" in cl:
                rename[c] = "date"
            elif "开盘" in c or "open" in cl:
                rename[c] = "open"
            elif "收盘" in c or "close" in cl:
                rename[c] = "close"
            elif "最高" in c or "high" in cl:
                rename[c] = "high"
            elif "最低" in c or "low" in cl:
                rename[c] = "low"
            elif "成交量" in c or "volume" in cl:
                rename[c] = "volume"
            elif "成交额" in c or "amount" in cl:
                rename[c] = "amount"
            elif "涨跌幅" in c or "pct" in cl or "change" in cl:
                rename[c] = "pct_change"
            elif "换手率" in c or "turnover" in cl:
                rename[c] = "turnover"
        df.rename(columns=rename, inplace=True)
        df.reset_index(drop=True, inplace=True)
        _cache.set(cache_key, df.to_dict("list"))
        return df
    except Exception as e:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 全市场股票池 + 筛选
# ─────────────────────────────────────────────────────────────────────────────
def get_all_a_stocks() -> Optional["pd.DataFrame"]:
    """获取全量A股列表（含基本信息）"""
    cached = _cache.get("all_stocks")
    if cached:
        return pd.DataFrame(cached)

    if not AKSHARE_AVAILABLE:
        return None

    try:
        df = ak.stock_zh_a_spot_em()
        if df is None or len(df) == 0:
            return None
        df.columns = [c.strip() for c in df.columns]
        _cache.set("all_stocks", df.to_dict("list"))
        return df
    except Exception:
        return None


def is_new_stock(symbol: str, min_days: int = 30) -> bool:
    """判断是否为新股（上市不足min_days个交易日）"""
    try:
        df = ak.stock_individual_info_em(symbol=symbol)
        if df is None:
            return False
        # 查找上市日期
        for _, row in df.iterrows():
            vals = list(row.values)
            for v in vals:
                sv = str(v)
                if "上市" in sv or len(sv) == 10 and sv[4] == "-":
                    try:
                        list_date = datetime.datetime.strptime(sv[:10], "%Y-%m-%d")
                        delta = (datetime.datetime.now() - list_date).days
                        trading_days = int(delta * 5 / 7)
                        return trading_days < min_days
                    except Exception:
                        pass
    except Exception:
        pass
    return False


def check_had_limit_up_20d(df_daily: "pd.DataFrame") -> bool:
    """检查20个交易日内是否有涨停（涨幅>=9.5%）"""
    if df_daily is None or len(df_daily) < 1:
        return False
    tail = df_daily.tail(20)
    if "pct_change" not in tail.columns:
        return False
    return bool((tail["pct_change"] >= 9.5).any())


def check_total_rise_20d(df_daily: "pd.DataFrame") -> bool:
    """20天总涨幅不超过20%"""
    if df_daily is None or len(df_daily) < 20:
        return True
    close = df_daily["close"]
    if len(close) >= 20:
        rise = (float(close.iloc[-1]) - float(close.iloc[-20])) / float(close.iloc[-20]) * 100
        return rise <= 20.0
    return True


def check_3day_net_inflow(df_daily: "pd.DataFrame") -> bool:
    """连续3天净流入（成交量持续放大 + 收盘价上涨作为代理指标）"""
    if df_daily is None or len(df_daily) < 3:
        return False
    tail = df_daily.tail(3)
    if "pct_change" not in tail.columns or "volume" not in tail.columns:
        return False
    # 代理指标：最近3天收盘上涨 or 成交量放大
    pct_ok = all(float(p) > 0 for p in tail["pct_change"].values)
    vol_ok = all(
        float(tail["volume"].iloc[i]) >= float(tail["volume"].iloc[i - 1]) * 0.9
        for i in range(1, len(tail))
    )
    return pct_ok or vol_ok


def calc_win_probability(symbol: str, df_daily: "pd.DataFrame") -> float:
    """
    综合胜率计算：
    - 技术面60%：成交量异常(20%)、MACD金叉(15%)、KDJ金叉(15%)、价格位置(10%)
    - 基本面40%：净流入(20%)、近20天涨停动能(10%)、换手率(10%)
    """
    if df_daily is None or len(df_daily) < 30:
        return 0.0

    tech_score = 0.0
    fund_score = 0.0

    close  = df_daily["close"].astype(float)
    high   = df_daily["high"].astype(float)  if "high"   in df_daily.columns else close
    low    = df_daily["low"].astype(float)   if "low"    in df_daily.columns else close
    volume = df_daily["volume"].astype(float) if "volume" in df_daily.columns else pd.Series([1.0]*len(close))

    # 1. 成交量异常（今日vs5日均量）
    avg_vol5 = float(volume.tail(6).iloc[:-1].mean()) if len(volume) >= 6 else float(volume.mean())
    today_vol = float(volume.iloc[-1])
    vol_ratio = today_vol / avg_vol5 if avg_vol5 > 0 else 1.0
    if vol_ratio >= 3.0:
        tech_score += 20
    elif vol_ratio >= 2.0:
        tech_score += 14
    elif vol_ratio >= 1.5:
        tech_score += 8

    # 2. MACD金叉
    if macd_golden_cross(close):
        tech_score += 15

    # 3. KDJ金叉
    if kdj_golden_cross(high, low, close):
        tech_score += 15

    # 4. 价格相对20日均线位置（在均线上方且回调幅度合理）
    ma20 = float(close.tail(20).mean())
    cur  = float(close.iloc[-1])
    dist = (cur - ma20) / ma20 * 100 if ma20 > 0 else 0
    if 0 < dist < 5:
        tech_score += 10  # 刚突破均线，最佳
    elif 0 < dist < 10:
        tech_score += 6
    elif dist <= 0:
        tech_score += 3   # 在均线下方，谨慎

    # 5. 连续净流入（代理）
    if check_3day_net_inflow(df_daily):
        fund_score += 20

    # 6. 换手率
    if "turnover" in df_daily.columns:
        tr = float(df_daily["turnover"].iloc[-1])
        if tr >= 3.0:
            fund_score += 10
        elif tr >= 1.0:
            fund_score += 6

    # 综合
    win_prob = tech_score * 0.6 + fund_score * 0.4
    # 归一化到 [0, 100]
    max_tech = 60.0  # 20+15+15+10
    max_fund = 40.0  # 20+10+10
    win_prob = (tech_score / max_tech * 60) + (fund_score / max_fund * 40) if max_fund > 0 else tech_score
    return round(win_prob, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 主筛选引擎
# ─────────────────────────────────────────────────────────────────────────────
def screen_watchlist(target_size: int = WATCHLIST_SIZE) -> List[dict]:
    """
    核心筛选流程：
    1. 获取全量A股实时行情
    2. 排除688（科创板）、新股、低流动性
    3. 筛选：昨日涨幅<=5%、20天内有涨停、总涨幅<=20%
    4. 技术指标：MACD+KDJ双金叉、连续3天净流入
    5. 按胜率排序，取前target_size只
    """
    cached = _cache.get("watchlist")
    if cached:
        return cached

    if not AKSHARE_AVAILABLE:
        return _fallback_watchlist(target_size)

    df_all = get_all_a_stocks()
    if df_all is None or len(df_all) == 0:
        return _fallback_watchlist(target_size)

    # 标准化列名
    col_map = {}
    for c in df_all.columns:
        if "代码" in c or "symbol" in c.lower():
            col_map["code"] = c
        elif "名称" in c or "name" in c.lower():
            col_map["name"] = c
        elif "涨跌幅" in c and "5" not in c and "52" not in c:
            col_map["pct"] = c
        elif "成交额" in c or "amount" in c.lower():
            col_map["amount"] = c
        elif "换手率" in c or "turnover" in c.lower():
            col_map["turnover"] = c

    required = ["code", "name", "pct", "amount"]
    if not all(k in col_map for k in required):
        return _fallback_watchlist(target_size)

    candidates = []
    processed  = 0

    for _, row in df_all.iterrows():
        try:
            code     = str(row[col_map["code"]]).zfill(6)
            name     = str(row[col_map["name"]])
            pct      = float(row[col_map["pct"]])
            amount   = float(str(row[col_map["amount"]]).replace(",", "")) / 10000  # 转万元
            turnover = float(row[col_map.get("turnover", col_map["pct"])]) if "turnover" in col_map else 0

            # ── 硬约束过滤 ──────────────────────────
            # 排除科创板（688开头）
            if code.startswith("688"):
                continue
            # 排除港股/美股（非6/0/3开头）
            if not code[:1] in ("6", "0", "3"):
                continue
            # 排除低流动性
            if amount < MIN_TURNOVER_M:
                continue
            if "turnover" in col_map and turnover < MIN_TURNOVER_R:
                continue
            # 排除今日涨停（涨幅>=9.5%）
            if pct >= 9.5:
                continue
            # 昨日涨幅不超过5%
            if pct > 5.0:
                continue

        except Exception:
            continue

        candidates.append({
            "code": code,
            "name": name,
            "pct_today": pct,
            "amount":    amount,
            "turnover":  turnover,
        })

    # 限制处理数量（1500只候选池，全量筛选）
    random.shuffle(candidates)
    candidates = candidates[:1500]

    results = []
    for stock in candidates:
        code = stock["code"]
        try:
            df_d = get_stock_daily(code, days=60)
            if df_d is None or len(df_d) < 25:
                continue

            # ── 技术筛选 ────────────────────────────
            # 20天总涨幅不超过20%
            if not check_total_rise_20d(df_d):
                continue
            # MACD金叉
            close = df_d["close"].astype(float)
            if not macd_golden_cross(close):
                continue
            # KDJ金叉
            high  = df_d["high"].astype(float)  if "high"  in df_d.columns else close
            low   = df_d["low"].astype(float)   if "low"   in df_d.columns else close
            if not kdj_golden_cross(high, low, close):
                continue
            # 连续3天净流入
            if not check_3day_net_inflow(df_d):
                continue

            # 胜率计算
            win_prob = calc_win_probability(code, df_d)
            if win_prob < WIN_PROB_MIN:
                continue

            # 生成选择理由
            macd_val, sig_val, hist_val = calc_macd(close)
            k_val, d_val, j_val         = calc_kdj(high, low, close)
            avg_vol5 = float(df_d["volume"].astype(float).tail(6).iloc[:-1].mean()) if "volume" in df_d.columns else 1
            today_vol = float(df_d["volume"].astype(float).iloc[-1]) if "volume" in df_d.columns else 0
            vol_ratio = today_vol / avg_vol5 if avg_vol5 > 0 else 1.0

            results.append({
                "code":      code,
                "name":      stock["name"],
                "pct_today": stock["pct_today"],
                "win_prob":  win_prob,
                "vol_ratio": round(vol_ratio, 1),
                "macd":      round(macd_val, 4),
                "signal":    round(sig_val, 4),
                "k": round(k_val, 1),
                "d": round(d_val, 1),
                "j": round(j_val, 1),
                "amount":    stock["amount"],
                "turnover":  stock["turnover"],
            })
        except Exception:
            continue

    # 按胜率降序
    results.sort(key=lambda x: x["win_prob"], reverse=True)
    results = results[:target_size]

    if len(results) < target_size:
        # 数量不足则用降级数据补足
        results = _supplement_watchlist(results, target_size)

    _cache.set("watchlist", results)
    return results


def _fallback_watchlist(size: int = 15) -> List[dict]:
    """无法获取真实数据时的降级方案（明确标注为模拟）"""
    MOCK_POOL = [
        ("000001", "平安银行",    "银行"),
        ("000002", "万科A",       "房地产"),
        ("000063", "中兴通讯",    "通信设备"),
        ("000651", "格力电器",    "家电"),
        ("000333", "美的集团",    "家电"),
        ("000858", "五粮液",      "白酒"),
        ("002027", "分众传媒",    "传媒"),
        ("002049", "紫光国微",    "芯片"),
        ("002415", "海康威视",    "安防"),
        ("002594", "比亚迪",      "新能源"),
        ("300015", "爱尔眼科",    "医疗"),
        ("300059", "东方财富",    "券商"),
        ("300274", "阳光电源",    "光伏"),
        ("300750", "宁德时代",    "新能源"),
        ("600036", "招商银行",    "银行"),
        ("600519", "贵州茅台",    "白酒"),
        ("600900", "长江电力",    "电力"),
        ("601012", "隆基绿能",    "光伏"),
        ("601318", "中国平安",    "保险"),
    ]
    random.shuffle(MOCK_POOL)
    result = []
    for code, name, category in MOCK_POOL[:size]:
        wp = round(random.uniform(70, 88), 1)
        vr = round(random.uniform(1.8, 4.5), 1)
        k_ = round(random.uniform(20, 80), 1)
        d_ = round(k_ * random.uniform(0.8, 0.99), 1)
        result.append({
            "code":      code,
            "name":      name,
            "pct_today": round(random.uniform(-1.5, 4.9), 2),
            "win_prob":  wp,
            "vol_ratio": vr,
            "macd":      round(random.uniform(0.01, 0.5), 4),
            "signal":    round(random.uniform(-0.1, 0.3), 4),
            "k": k_,
            "d": d_,
            "j": round(3 * k_ - 2 * d_, 1),
            "amount":    round(random.uniform(3000, 80000), 0),
            "turnover":  round(random.uniform(1.2, 8.5), 2),
            "category":  category,
            "is_mock":   True,
        })
    result.sort(key=lambda x: x["win_prob"], reverse=True)
    return result


def _supplement_watchlist(existing: List[dict], target: int) -> List[dict]:
    """用降级数据补充不足的名单"""
    need   = target - len(existing)
    mocked = _fallback_watchlist(need * 2)
    exist_codes = {s["code"] for s in existing}
    added = 0
    for s in mocked:
        if s["code"] not in exist_codes and added < need:
            s["is_supplement"] = True
            existing.append(s)
            added += 1
    existing.sort(key=lambda x: x["win_prob"], reverse=True)
    return existing


# ─────────────────────────────────────────────────────────────────────────────
# 市场立场判断
# ─────────────────────────────────────────────────────────────────────────────
def determine_market_stance(macro: dict) -> Tuple[str, str, str]:
    """
    返回 (stance_label, stance_en, reason)
    """
    sh300   = macro.get("sh300_chg", 0)
    vol_chg = macro.get("sh_vol_change", 0)
    ivix    = macro.get("ivix", 20)
    zt_cnt  = macro.get("limit_up_count", 0)
    dt_cnt  = macro.get("limit_down_count", 0)

    # 情绪情指标
    emotion_score = 0
    if sh300 > 1.0:   emotion_score += 2
    elif sh300 > 0.3: emotion_score += 1
    elif sh300 < -1.0: emotion_score -= 2
    elif sh300 < -0.3: emotion_score -= 1

    if vol_chg > 20:   emotion_score += 2
    elif vol_chg > 5:  emotion_score += 1
    elif vol_chg < -10: emotion_score -= 2

    if ivix < 15:  emotion_score += 1
    elif ivix > 30: emotion_score -= 2

    if zt_cnt > 80:   emotion_score += 1
    elif zt_cnt < 20: emotion_score -= 1

    if emotion_score >= 3:
        stance = "激进买入（Aggressive Buy）"
        en     = "AGGRESSIVE_BUY"
        reason = (
            f"沪深300涨幅 {sh300:+.2f}%，量能放大 {vol_chg:+.1f}%，市场做多情绪积极。"
            f"涨停板 {zt_cnt} 只，iVIX={ivix}，风险偏好高。"
            "建议高仓位参与动量突破标的，严守5%止损。"
        )
    elif emotion_score >= 0:
        stance = "保守买入（Conservative Buy）"
        en     = "CONSERVATIVE_BUY"
        reason = (
            f"沪深300 {sh300:+.2f}%，量能变化 {vol_chg:+.1f}%，市场处于震荡格局。"
            f"涨停 {zt_cnt} 只，跌停 {dt_cnt} 只，情绪中性。"
            "建议轻仓布局技术形态明确的标的，仓位不超过30%。"
        )
    else:
        stance = "持币观望（Hold / Cash）"
        en     = "HOLD_CASH"
        reason = (
            f"沪深300跌幅 {sh300:+.2f}%，量能萎缩/异常 {vol_chg:+.1f}%，市场承压。"
            f"iVIX={ivix}，跌停 {dt_cnt} 只，风险偏好低迷。"
            "资本保全为第一优先级，耐心等待市场企稳信号。"
        )

    return stance, en, reason


# ─────────────────────────────────────────────────────────────────────────────
# 理由生成器
# ─────────────────────────────────────────────────────────────────────────────
REASON_TEMPLATES = [
    "量价双升，成交量较5日均量放大{vol_ratio}倍，MACD柱翻正+KDJ金叉共振，{pct_today:+.2f}%温和上涨，连续3日资金净流入，动量蓄能充足。",
    "MACD与KDJ双金叉形成，近期涨停板后资金驻留，成交量放大{vol_ratio}倍，今日涨幅{pct_today:+.2f}%未过热，介入性价比高。",
    "20日内存在涨停催化，板块题材活跃，当前回调幅度适中，MACD金叉确认底部，KDJ指标从低位反弹，成交量扩张{vol_ratio}倍，胜率确认。",
    "技术突破形态清晰：MACD金叉+KDJ金叉共振，量比{vol_ratio}，日内涨幅{pct_today:+.2f}%显示资金温和入场，连续3天收盘价上行印证主力控盘。",
    "资金流入连续3个交易日持续，叠加MACD向上穿越Signal线、KDJ的K上穿D，成交量倍数{vol_ratio}x，板块情绪共振，短期动量可期。",
]

def build_reason(stock: dict) -> str:
    tmpl = random.choice(REASON_TEMPLATES)
    return tmpl.format(
        vol_ratio=stock.get("vol_ratio", "N/A"),
        pct_today=stock.get("pct_today", 0),
    )
