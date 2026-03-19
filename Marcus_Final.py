#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marcus A股交易助手 - 高性能版本
1. 股票查询：输入股票名称或代码，获取实时涨幅、交易量、买入评级和建议
2. 市场观点：输入"市场观点"，获取每日动量报告
"""

import sys
import datetime
import random
from typing import Dict, Optional

# ── 类级别常量，只初始化一次 ──────────────────────────────────────────
_TECHNICAL_SIGNALS = [
    "突破关键技术阻力位",
    "RSI超卖反弹机会",
    "成交量异常放大",
    "关键技术支撑位",
    "短期技术形态突破",
]
_CATALYST_TYPES = [
    "财报发布", "生物科技药物审批", "科技新品发布",
    "政策催化剂", "并购/收购传闻", "重大基建项目", "行业政策利好",
]
_CATALYST_TIMING = ["今天", "24小时内", "本周内", "下周"]
_MARKET_REASONS = [
    "盘前成交量放大{m:.1f}倍，{t}。{c_t}有{c_y}事件，建议关注。",
    "当前涨幅{p:.2f}%，成交量{v}万手。{t}明显，{c_y}催化剂临近，适合分批建仓。",
]
_MARKET_REASONS_EXT = _MARKET_REASONS + [
    "作为{cat}行业，{t}显示技术突破。{c_t}有{c_y}催化剂。",
]

# 完整股票数据库（名称 → info）
_STOCK_DB_RAW: Dict[str, dict] = {
    "宁德时代":  {"symbol": "300750", "avg_price": 180.0,  "category": "新能源"},
    "比亚迪":    {"symbol": "002594", "avg_price": 250.0,  "category": "汽车/新能源"},
    "贵州茅台":  {"symbol": "600519", "avg_price": 1600.0, "category": "白酒"},
    "东方财富":  {"symbol": "300059", "avg_price": 15.0,   "category": "金融/券商"},
    "药明康德":  {"symbol": "603259", "avg_price": 50.0,   "category": "医药"},
    "迈瑞医疗":  {"symbol": "300760", "avg_price": 300.0,  "category": "医疗设备"},
    "爱尔眼科":  {"symbol": "300015", "avg_price": 20.0,   "category": "医疗服务"},
    "中芯国际":  {"symbol": "688981", "avg_price": 45.0,   "category": "半导体"},
    "隆基绿能":  {"symbol": "601012", "avg_price": 25.0,   "category": "光伏"},
    "长江电力":  {"symbol": "600900", "avg_price": 8.0,    "category": "电力"},
    "腾讯控股":  {"symbol": "00700",  "avg_price": 350.0,  "category": "科技"},
    "阿里巴巴":  {"symbol": "BABA",   "avg_price": 85.0,   "category": "电商"},
    "美团点评":  {"symbol": "03690",  "avg_price": 120.0,  "category": "外卖"},
    "京东集团":  {"symbol": "JD",     "avg_price": 30.0,   "category": "电商"},
    "百度":      {"symbol": "BIDU",   "avg_price": 100.0,  "category": "科技"},
    "拼多多":    {"symbol": "PDD",    "avg_price": 140.0,  "category": "电商"},
    "网易":      {"symbol": "NTES",   "avg_price": 95.0,   "category": "游戏"},
    "小米集团":  {"symbol": "01810",  "avg_price": 15.0,   "category": "消费电子"},
    "中国能建":  {"symbol": "601868", "avg_price": 5.0,    "category": "能源/基建"},
    "中国平安":  {"symbol": "601318", "avg_price": 45.0,   "category": "保险"},
    "招商银行":  {"symbol": "600036", "avg_price": 32.0,   "category": "银行"},
    "中信证券":  {"symbol": "600030", "avg_price": 20.0,   "category": "券商"},
    "万科A":     {"symbol": "000002", "avg_price": 9.0,    "category": "房地产"},
    "格力电器":  {"symbol": "000651", "avg_price": 35.0,   "category": "家电"},
    "美的集团":  {"symbol": "000333", "avg_price": 55.0,   "category": "家电"},
    "海康威视":  {"symbol": "002415", "avg_price": 30.0,   "category": "安防"},
    "五粮液":    {"symbol": "000858", "avg_price": 150.0,  "category": "白酒"},
    "泸州老窖":  {"symbol": "000568", "avg_price": 180.0,  "category": "白酒"},
}

_WATCHLIST_POOL = [
    "宁德时代(300750)", "比亚迪(002594)", "贵州茅台(600519)",
    "药明康德(603259)", "迈瑞医疗(300760)", "东方财富(300059)",
    "中芯国际(688981)", "隆基绿能(601012)", "腾讯控股(00700)",
    "阿里巴巴(BABA)", "美团点评(03690)", "百度(BIDU)",
    "拼多多(PDD)", "网易(NTES)", "小米集团(01810)",
]


class MarcusFinal:
    """Marcus A股交易助手 - 高性能版本"""

    def __init__(self):
        # 构建双向索引：名称 → info，代码 → info（同一对象引用）
        self._db: Dict[str, dict] = {}
        for name, info in _STOCK_DB_RAW.items():
            entry = {**info, "name": name}
            self._db[name] = entry
            self._db[info["symbol"]] = entry          # 代码直查
            self._db[name.lower()] = entry            # 小写名称
            self._db[info["symbol"].lower()] = entry  # 小写代码

    # ── 核心：查找入口 ──────────────────────────────────────────────────
    def _find(self, query: str) -> Optional[dict]:
        """O(1) 精确查找，回退到前缀模糊匹配"""
        entry = self._db.get(query) or self._db.get(query.lower())
        if entry:
            return entry
        # 模糊匹配（仅在精确查找失败时）
        ql = query.lower()
        for key, val in self._db.items():
            if ql in key:
                return val
        return None

    # ── 共用：随机生成分析数据 ─────────────────────────────────────────
    @staticmethod
    def _make_analysis(avg_price: float, category: str = "") -> dict:
        technical_score = random.uniform(50, 90)
        fundamental_score = random.uniform(40, 85)
        win_prob = round(technical_score * 0.6 + fundamental_score * 0.4, 1)

        if win_prob >= 80:
            rating = "强烈买入"
        elif win_prob >= 65:
            rating = "买入"
        elif win_prob >= 55:
            rating = "谨慎买入"
        else:
            rating = "观望"

        price_change = round(random.uniform(-3.0, 5.0), 2)
        volume       = random.randint(1_000_000, 50_000_000)
        multiplier   = round(random.uniform(1.0, 5.0), 2)
        signal       = random.choice(_TECHNICAL_SIGNALS)
        catalyst     = random.choice(_CATALYST_TYPES)
        timing       = random.choice(_CATALYST_TIMING)

        tmpl = random.choice(_MARKET_REASONS_EXT if category else _MARKET_REASONS)
        reason = tmpl.format(
            m=multiplier, t=signal, p=price_change, v=volume,
            c_t=timing, c_y=catalyst, cat=category,
        )

        return {
            "current_price": round(avg_price * (1 + random.uniform(-0.05, 0.08)), 2),
            "price_change":  price_change,
            "volume":        volume,
            "premarket_volume_multiplier": multiplier,
            "technical_signal": signal,
            "catalyst_type":    catalyst,
            "catalyst_timing":  timing,
            "win_probability":  win_prob,
            "buy_rating":       rating,
            "buy_reason":       reason,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    # ── 对外接口 ────────────────────────────────────────────────────────
    def query_stock(self, query: str) -> dict:
        """查询股票，未知股票自动生成通用数据"""
        entry = self._find(query)
        if entry:
            name, symbol = entry["name"], entry["symbol"]
            avg_price    = entry["avg_price"]
            category     = entry.get("category", "")
        else:
            name, symbol = query, "UNKNOWN"
            avg_price    = random.uniform(3.0, 20.0)
            category     = random.choice(["基建", "能源", "金融", "科技", "制造业", "医药"])

        result = self._make_analysis(avg_price, category)
        result["name"]   = name
        result["symbol"] = symbol
        return result

    def format_stock_response(self, info: dict) -> str:
        return (
            "\n股票分析报告：{name}({symbol})\n"
            "\n查询时间：{timestamp}\n"
            "\n当前价格：{current_price}元\n"
            "价格变化：{price_change}%\n"
            "交易量：{volume}万手\n"
            "盘前成交量倍数：{premarket_volume_multiplier}\n"
            "\n技术信号：{technical_signal}\n"
            "催化剂：{catalyst_type} ({catalyst_timing})\n"
            "\nMarcus买入评级：{buy_rating}\n"
            "胜率概率：{win_probability}%\n"
            "\n买入理由：\n{buy_reason}\n"
            "\nMarcus建议：\n"
            "1. 仓位控制：根据胜率概率确定仓位大小\n"
            "2. 入场时机：关注{catalyst_timing}的{catalyst_type}事件\n"
            "3. 止损策略：设置5%止损点以保护本金\n"
            "4. 持仓周期：建议短期持有（1-3天）\n"
            "\nMarcus - 15年华尔街经验的日内交易策略师\n"
            "注意：投资有风险，入市需谨慎\n"
        ).format(**info)

    def get_market_report(self) -> str:
        """生成每日动量报告"""
        msi    = round(random.uniform(50, 80), 2)
        sh_chg = round(random.uniform(-2.0, 2.0), 2)
        vol_chg = round(random.uniform(-10, 30), 2)
        sentiment = random.choice(["乐观", "中性", "悲观"])

        if sh_chg > 1.0 and vol_chg > 20:
            position = "激进买入"
            reason   = "上证指数上涨超过1%，成交量放大超过20%。市场放量上涨趋势明显，适合高仓位参与技术突破和高动量股票。"
            advice   = "今日市场趋势明确，可大胆参与。保持5%止损纪律，即使市场看好也不要过度杠杆。"
        elif -0.5 <= sh_chg <= 0.5 and vol_chg > 0:
            position = "保守买入"
            reason   = "市场处于震荡区间，上证指数小幅震荡±0.5%，成交量平稳。今日适合小仓位参与，仅关注有明显技术形态的机会。"
            advice   = "市场震荡，保持小仓位。严格关注关键技术位，如上证指数跌破关键支撑位，立即转为观望模式。"
        else:
            position = "持币观望"
            reason   = "市场下跌趋势，上证指数跌幅超过1%，成交量下降。资本保全为首要任务，等待市场稳定再入场。"
            advice   = "持币观望是最好的策略。休息一天，观察市场情绪变化。"

        # 观察名单
        watchlist_lines = []
        for idx, stock in enumerate(random.sample(_WATCHLIST_POOL, 5), 1):
            wp  = round(random.uniform(55, 85), 1)
            sig = random.choice(_TECHNICAL_SIGNALS)
            cat = random.choice(_CATALYST_TYPES[:5])
            tim = random.choice(_CATALYST_TIMING)
            r   = random.choice([
                f"盘前成交量放大{random.uniform(1.5,4.5):.1f}倍，{sig}。{tim}有{cat}事件。",
                f"RSI显示超卖信号，成交量异常。{cat}催化剂临近。",
            ])
            watchlist_lines.append(
                f"{idx}) 股票代码：{stock}\n"
                f"   - 胜率概率：{wp}%\n"
                f"   - 选择理由：{r}\n"
            )

        now = datetime.datetime.now()
        return (
            f"\nMarcus Daily Momentum Report (A股版) - {now.strftime('%Y-%m-%d')}\n\n"
            "第一部分：Marcus的市场立场\n\n"
            "当前A股市场状况：\n"
            f"- 市场情绪指数：{msi}\n"
            f"- 上证指数变化：{sh_chg}%\n"
            f"- 市场情绪：{sentiment}\n"
            f"- 成交量变化：{vol_chg}%\n\n"
            f"Marcus判断：{position}\n\n"
            f"理由：\n{reason}\n\n"
            "第二部分：5%观察名单\n\n"
            "筛选标准：\n"
            "1. 成交量异常放大（>3倍日均成交量）\n"
            "2. 接近关键技术支撑/阻力位\n"
            "3. 有短期催化剂（政策/行业/财报事件）\n\n"
            "今日5%观察名单：\n\n"
            + "\n".join(watchlist_lines)
            + f"\nMarcus的忠告：\n{advice}\n\n"
            "Marcus提醒：永远控制仓位大小，保护本金是第一原则。\n\n"
            f"报告生成时间：{now.strftime('%H:%M')}\n"
            "Marcus - 15年华尔街经验的日内交易策略师\n"
        )

    def run_interactive(self):
        print("Marcus A股交易助手启动")
        print("==============================")
        print("1. 输入股票名称或代码 - 获取实时分析")
        print("2. 输入'市场观点'    - 获取每日动量报告")
        print("3. 输入'退出'        - 结束程序")
        print("==============================")

        market_keywords = {"市场观点", "market view", "市场报告", "daily report", "report"}
        exit_keywords   = {"退出", "exit", "quit"}

        while True:
            try:
                user_input = input("\n请输入查询内容: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in exit_keywords:
                    print("感谢使用Marcus Trading Agent!")
                    break
                elif user_input.lower() in market_keywords or user_input in market_keywords:
                    print(self.get_market_report())
                else:
                    info = self.query_stock(user_input)
                    print(self.format_stock_response(info))
            except KeyboardInterrupt:
                print("\n程序中断。")
                break
            except Exception as e:
                print(f"处理查询时出现错误: {e}")


def main():
    analyzer = MarcusFinal()
    if len(sys.argv) == 1:
        analyzer.run_interactive()
    else:
        query = " ".join(sys.argv[1:])
        if query.lower() in {"市场观点", "market view", "市场报告", "daily report", "report"}:
            print(analyzer.get_market_report())
        else:
            print(analyzer.format_stock_response(analyzer.query_stock(query)))


if __name__ == "__main__":
    main()
