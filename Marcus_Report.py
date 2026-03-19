#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marcus A股 · 报告生成器 v3.0
输出：
  - 盘中动量报告（10:00 / 11:25 / 14:30）
  - 收盘总结 + 次日操作建议（15:00）
  - 开盘风险提醒（次日 9:25）
"""

import datetime
import random
from typing import List

from Marcus_Engine import (
    get_market_macro,
    get_sector_flow,
    screen_watchlist,
    determine_market_stance,
    build_reason,
)

# ─────────────────────────────────────────────────────────────────────────────
# 工具
# ─────────────────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def _today() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")

def _data_tag(stock: dict) -> str:
    """数据来源标注"""
    if stock.get("is_mock") or stock.get("is_supplement"):
        return "⚠️[模拟]"
    return "✅[实时]"

# ─────────────────────────────────────────────────────────────────────────────
# 第一部分：市场立场
# ─────────────────────────────────────────────────────────────────────────────
def render_market_stance(macro: dict) -> str:
    stance, en, reason = determine_market_stance(macro)

    # 风格图标
    icons = {
        "AGGRESSIVE_BUY":   "🚀",
        "CONSERVATIVE_BUY": "🟡",
        "HOLD_CASH":        "🛡️",
    }
    icon = icons.get(en, "📊")

    sh300   = macro.get("sh300_chg",    0)
    sh300_c = macro.get("sh300_close",  0)
    ivix    = macro.get("ivix",         20)
    vol_chg = macro.get("sh_vol_change", 0)
    zt      = macro.get("limit_up_count",   0)
    dt      = macro.get("limit_down_count", 0)

    lines = [
        "═" * 55,
        f"  📊 Marcus Daily Momentum Report · {_today()}",
        "═" * 55,
        "",
        "【第一部分】Marcus 的市场立场",
        "─" * 40,
        f"  沪深300：    {sh300_c:.2f}  ({sh300:+.2f}%)",
        f"  中国iVIX：   {ivix:.2f}",
        f"  全市场量能：  较5日均量 {vol_chg:+.1f}%",
        f"  涨停板数量：  {zt} 只  |  跌停：{dt} 只",
        f"  富时A50：    {macro.get('ftse_a50_chg', 0):+.2f}%  (前晚)",
        f"  恒生科技：   {macro.get('hstech_chg', 0):+.2f}%  (昨收)",
        "",
        f"  {icon}  Marcus 判断：{stance}",
        "",
        f"  理由：",
        f"  {reason}",
        "",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 第二部分：15只观察名单
# ─────────────────────────────────────────────────────────────────────────────
def render_watchlist(watchlist: List[dict], report_time: str = "") -> str:
    lines = [
        "【第二部分】胜率 ≥70% 观察名单（共15只）",
        "─" * 40,
        f"  推送时间：{report_time or _now()}",
        f"  筛选逻辑：688排除 | 非新股 | 日成交≥2000万 | 昨涨≤5%",
        f"           20日内有涨停 | 总涨幅≤20% | MACD+KDJ双金叉",
        f"           连续3天净流入 | 非今日涨停",
        "",
    ]

    for idx, stock in enumerate(watchlist[:15], 1):
        tag      = _data_tag(stock)
        code     = stock.get("code", "------")
        name     = stock.get("name", "未知")
        wp       = stock.get("win_prob",  0)
        pct      = stock.get("pct_today", 0)
        vr       = stock.get("vol_ratio", 0)
        k        = stock.get("k",  0)
        d        = stock.get("d",  0)
        j        = stock.get("j",  0)
        macd_v   = stock.get("macd", 0)
        sig_v    = stock.get("signal", 0)
        amount   = stock.get("amount",  0)
        turnover = stock.get("turnover", 0)
        reason   = build_reason(stock)

        # 胜率样式
        if wp >= 85:
            wp_tag = "🔥"
        elif wp >= 78:
            wp_tag = "⭐"
        else:
            wp_tag = "🟢"

        lines += [
            f"  {idx:02d}. {tag} {name}  （{code}）",
            f"      今日涨幅：{pct:+.2f}%   胜率概率：{wp_tag} {wp:.1f}%",
            f"      量比：{vr:.1f}x   日成交额：{amount:.0f}万",
            f"      换手率：{turnover:.2f}%",
            f"      MACD：{macd_v:.4f}  Signal：{sig_v:.4f}（金叉确认）",
            f"      KDJ：K={k:.1f}  D={d:.1f}  J={j:.1f}（金叉确认）",
            f"      选择理由：{reason}",
            "",
        ]

    lines += [
        "  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─",
        "  ⚠️  标注[模拟]的数据为网络限制下的参考估算，仅供研究参考。",
        "  ✅  标注[实时]的数据来自真实市场行情。",
        "",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 第三部分：收盘总结（15:00推送）
# ─────────────────────────────────────────────────────────────────────────────
def render_closing_summary(macro: dict, sector_flow: List[dict]) -> str:
    # 板块排序
    sorted_flow = sorted(sector_flow, key=lambda x: x.get("net_flow", 0), reverse=True)
    top_inflow   = sorted_flow[:3]
    top_outflow  = sorted_flow[-3:] if len(sorted_flow) >= 3 else []

    sh300   = macro.get("sh300_chg", 0)
    vol_chg = macro.get("sh_vol_change", 0)
    zt      = macro.get("limit_up_count",  0)
    dt      = macro.get("limit_down_count", 0)

    # 次日操作建议逻辑
    if sh300 > 0.5 and vol_chg > 10:
        next_day_advice = (
            "今日放量上涨，市场做多动能持续。明日可延续进攻思路，"
            "重点关注今日净流入前三板块的龙头标的，逢低介入昨日MACD+KDJ共振标的。"
            "注意尾盘有无异动出货信号。"
        )
        next_stance = "偏多思路，轻仓试探"
    elif sh300 < -0.5 and vol_chg < -5:
        next_day_advice = (
            "今日缩量下跌，空头惯性犹存。明日开盘30分钟观察情绪，"
            "若沪深300跌幅扩大则坚守空仓，若低开高走则关注超跌反弹机会。"
            "仓位控制在20%以内，优先保本。"
        )
        next_stance = "防守为主，轻仓试探反弹"
    else:
        next_day_advice = (
            "今日震荡整理，方向不明。明日重点关注量能变化：若开盘放量上行则跟进布局，"
            "若继续缩量则持币等待。选择今日净流入板块中技术形态最优的1-2只标的，小仓位参与。"
        )
        next_stance = "中性观望，精选个股"

    # 今日行情综述
    if sh300 > 0:
        mkt_summary = f"沪深300收涨 {sh300:.2f}%，全天呈{('放量' if vol_chg > 0 else '缩量')}上涨格局，"
    else:
        mkt_summary = f"沪深300收跌 {abs(sh300):.2f}%，全天{('缩量' if vol_chg < 0 else '放量')}下跌，"

    mkt_summary += f"涨停 {zt} 只、跌停 {dt} 只，市场情绪{'偏强' if zt > dt * 2 else ('偏弱' if dt > zt else '中性')}。"

    lines = [
        "【第三部分】收盘总结（15:00）",
        "─" * 40,
        f"  推送时间：{_now()}",
        "",
        "  📈 今日行情综述",
        f"  {mkt_summary}",
        "",
    ]

    if top_inflow:
        lines += ["  💚 净流入前三板块（主力资金流入）"]
        for i, s in enumerate(top_inflow, 1):
            net  = s.get("net_flow", 0)
            name = s.get("name", "未知")
            chg  = s.get("chg", 0)
            lines.append(f"    {i}. {name}  净流入：{net:+.2f}亿  涨跌：{chg:+.2f}%")
        lines.append("")
    else:
        lines += ["  💚 净流入板块：数据获取中，请登录东方财富查看", ""]

    if top_outflow:
        lines += ["  🔴 净流出前三板块（主力资金撤离）"]
        for i, s in enumerate(reversed(top_outflow), 1):
            net  = s.get("net_flow", 0)
            name = s.get("name", "未知")
            chg  = s.get("chg", 0)
            lines.append(f"    {i}. {name}  净流出：{net:+.2f}亿  涨跌：{chg:+.2f}%")
        lines.append("")

    lines += [
        "  📋 明日操作建议",
        f"  立场：{next_stance}",
        f"  {next_day_advice}",
        "",
        "  重点关注：今日净流入龙头标的 + MACD/KDJ双金叉形成的超跌反弹标的",
        f"  仓位建议：{'60-80%' if sh300 > 0.5 else ('10-20%' if sh300 < -0.5 else '20-40%')}",
        "  止损原则：任何单只标的亏损达5%立即出局，不挣扎。",
        "",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 第四部分：开盘风险提醒（次日 9:25推送）
# ─────────────────────────────────────────────────────────────────────────────
def render_opening_alert(macro: dict, watchlist: List[dict], sector_flow: List[dict]) -> str:
    stance, en, _ = determine_market_stance(macro)
    sh300   = macro.get("sh300_chg", 0)
    vol_chg = macro.get("sh_vol_change", 0)
    zt      = macro.get("limit_up_count",  0)
    dt      = macro.get("limit_down_count", 0)

    # 今日关注点
    top3_watch = [f"{s['name']}({s['code']})" for s in watchlist[:3]]
    top_sector = [s["name"] for s in sorted(sector_flow, key=lambda x: x.get("net_flow", 0), reverse=True)[:3]]

    # 关键风险点
    risks = []
    if abs(sh300) > 1.5:
        risks.append(f"昨日大幅{'上涨' if sh300 > 0 else '下跌'} {sh300:+.2f}%，今日存在反向修正风险")
    if dt > zt * 1.5:
        risks.append(f"昨日跌停 {dt} 只远超涨停 {zt} 只，情绪严重偏弱")
    if vol_chg < -20:
        risks.append(f"昨日量能大幅萎缩 {vol_chg:.1f}%，多头意愿不足")

    if not risks:
        risks.append("当前无极端风险信号，按常规纪律操作")

    lines = [
        "═" * 55,
        f"  ⏰ Marcus 开盘提醒 · {_today()} 09:25",
        "═" * 55,
        "",
        "【第四部分】开盘风险提示 & 操作建议",
        "─" * 40,
        "",
        "  📌 开盘操作建议",
        f"  当前市场立场：{stance}",
        "",
        "  开盘前15分钟（9:15-9:25）关注：",
        "  ① 股指期货升贴水（判断机构多空意愿）",
        "  ② 沪深300指数开盘方向（确认整体趋势）",
        "  ③ 昨日涨停股今日高开 or 低开（验证情绪延续性）",
        "",
        "  🎯 今日重点关注标的（来自观察名单Top3）",
    ]

    for i, s in enumerate(top3_watch, 1):
        lines.append(f"    {i}. {s}")

    if top_sector:
        lines += [
            "",
            "  🏭 今日重点关注板块（昨日净流入）",
        ]
        for i, name in enumerate(top_sector[:3], 1):
            lines.append(f"    {i}. {name}")

    lines += [
        "",
        "  ⚠️  风险提示",
    ]
    for r in risks:
        lines.append(f"    · {r}")

    lines += [
        "",
        "  📏 今日纪律",
        "    · 开盘前5分钟不下单（避免开盘情绪波动）",
        "    · 单只标的仓位≤20%",
        "    · 亏损5%立即止损，不等待",
        "    · 涨停封板未成功 → 立即离场",
        "    · 11:00前无明确信号 → 当日持币",
        "",
        "  「交易的本质是管理预期差，而不是预测未来。」",
        "  ─ Marcus",
        "",
        "  ⚠️  声明：本报告仅供学习研究，不构成投资建议。",
        "      A股投资有风险，请根据自身承受能力决策。",
        "═" * 55,
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 整合：生成完整报告
# ─────────────────────────────────────────────────────────────────────────────
def generate_intraday_report(report_time: str = "") -> str:
    """盘中报告：第一+第二部分（10:00 / 11:25 / 14:30推送）"""
    print("[Marcus] 正在获取市场数据...")
    macro     = get_market_macro()
    watchlist = screen_watchlist(15)

    part1 = render_market_stance(macro)
    part2 = render_watchlist(watchlist, report_time)

    footer = [
        "─" * 55,
        "  ⚠️  声明：本报告仅供学习研究，不构成投资建议。",
        f"  数据来源：{'AkShare 实时行情' if macro.get('data_source') == 'akshare' else '模拟估算（网络受限）'}",
        f"  生成时间：{_now()}",
        "  Marcus — 15年华尔街+A股实战经验的日内动量策略师",
        "═" * 55,
    ]

    return part1 + part2 + "\n".join(footer)


def generate_closing_report() -> str:
    """收盘报告：第三部分（15:00推送）"""
    print("[Marcus] 正在生成收盘总结...")
    macro       = get_market_macro()
    sector_flow = get_sector_flow()
    watchlist   = screen_watchlist(15)

    part1 = render_market_stance(macro)
    part3 = render_closing_summary(macro, sector_flow)

    footer = [
        "─" * 55,
        f"  数据来源：{'AkShare 实时行情' if macro.get('data_source') == 'akshare' else '模拟估算'}",
        f"  生成时间：{_now()}",
        "  Marcus — 日内动量策略师",
        "═" * 55,
    ]
    return part1 + part3 + "\n".join(footer)


def generate_opening_alert() -> str:
    """开盘提醒：第四部分（次日9:25推送）"""
    print("[Marcus] 正在生成开盘风险提醒...")
    macro       = get_market_macro()
    sector_flow = get_sector_flow()
    watchlist   = screen_watchlist(15)
    return render_opening_alert(macro, watchlist, sector_flow)


# ─────────────────────────────────────────────────────────────────────────────
# 快速测试
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "intraday"
    if mode == "closing":
        print(generate_closing_report())
    elif mode == "alert":
        print(generate_opening_alert())
    else:
        print(generate_intraday_report(report_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
