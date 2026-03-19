#!/usr/bin/env python3
"""
Marcus自动化脚本
用于自动化运行Marcus交易助手的功能
"""

import subprocess
import datetime
import sys

def generate_daily_report():
    """生成每日市场观点报告"""
    print(f"正在生成Marcus每日动量报告... ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})")
    result = subprocess.run(["python", "Marcus_Final.py", "市场观点"], capture_output=True, text=True)
    print(result.stdout)
    
    # 保存到文件
    with open(f"Marcus_Daily_Report_{datetime.datetime.now().strftime('%Y%m%d')}.md", "w") as f:
        f.write(f"# Marcus每日动量报告\n\n生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(result.stdout)
    
    print(f"报告已保存到Marcus_Daily_Report_{datetime.datetime.now().strftime('%Y%m%d')}.md")

def generate_stock_report(stocks):
    """生成股票分析报告"""
    print(f"正在生成股票分析报告... ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})")
    
    all_results = []
    
    for stock in stocks:
        print(f"分析股票：{stock}")
        result = subprocess.run(["python", "Marcus_Final.py", stock], capture_output=True, text=True)
        print(result.stdout)
        all_results.append(f"\n=== {stock} ===\n{result.stdout}")
    
    # 保存到文件
    with open(f"Marcus_Stock_Reports_{datetime.datetime.now().strftime('%Y%m%d')}.md", "w") as f:
        f.write(f"# Marcus股票分析报告\n\n生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("\n".join(all_results))
    
    print(f"报告已保存到Marcus_Stock_Reports_{datetime.datetime.now().strftime('%Y%m%d')}.md")

def interactive_mode():
    """启动交互模式"""
    print("启动Marcus交互模式...")
    subprocess.run(["python", "Marcus_Final.py"])

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 默认模式：生成每日报告和股票报告
        generate_daily_report()
        
        # 查询主要股票
        stocks = ["宁德时代", "比亚迪", "贵州茅台", "腾讯控股", "阿里巴巴"]
        generate_stock_report(stocks)
        
    elif sys.argv[1] == "daily":
        # 生成每日报告
        generate_daily_report()
        
    elif sys.argv[1] == "stocks":
        # 生成股票报告（可以指定股票列表）
        if len(sys.argv) > 2:
            stocks = sys.argv[2:]
        else:
            stocks = ["宁德时代", "比亚迪", "贵州茅台", "腾讯控股", "阿里巴巴"]
        generate_stock_report(stocks)
        
    elif sys.argv[1] == "interactive":
        # 交互模式
        interactive_mode()
        
    elif sys.argv[1] == "test":
        # 测试所有功能
        print("测试Marcus系统...")
        stocks_to_test = ["宁德时代", "比亚迪", "市场观点"]
        
        for query in stocks_to_test:
            print(f"\n测试查询：{query}")
            result = subprocess.run(["python", "Marcus_Final.py", query], capture_output=True, text=True)
            print(result.stdout)
        
    else:
        print("Marcus自动化脚本使用说明:")
        print("用法:")
        print("  python Marcus_Automation_Script.py          # 默认模式：生成每日报告和股票报告")
        print("  python Marcus_Automation_Script.py daily    # 仅生成每日市场观点报告")
        print("  python Marcus_Automation_Script.py stocks   # 生成股票分析报告")
        print("  python Marcus_Automation_Script.py interactive  # 启动交互模式")
        print("  python Marcus_Automation_Script.py test    # 测试所有功能")
        print()
        print("示例:")
        print("  python Marcus_Automation_Script.py stocks 宁德时代 比亚迪 贵州茅台")