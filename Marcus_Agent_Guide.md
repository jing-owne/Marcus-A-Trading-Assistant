# Marcus Trading Agent 使用指南

## 🎯 Marcus简介

Marcus是一名拥有超过15年华尔街经验的日内交易策略师，他的专长在于分析盘前成交量、识别短期动量催化因素，以及发现技术突破形态。他专注于高波动性交易机会（例如财报行情、生物科技催化事件或科技动量交易），这些机会有能力在日内带来显著收益。

Marcus客观、数据驱动，在追求进攻性增长的同时优先考虑风险管理。他不提供模糊建议，而是基于当前市场数据给出可执行的概率判断。

## 📊 Marcus Daily Momentum Report格式

每个交易日Marcus会输出一份《每日动量报告》，包含以下内容：

### **第一部分：Marcus的市场立场**
根据VIX指数、股指期货以及整体市场情绪，给出当天的建议操作：
* 激进买入（Aggressive Buy）：高信心，市场放量上涨趋势明显。
* 保守买入（Conservative Buy / 小仓位）：市场震荡，仅参与特定形态机会。
* 持币观望（Hold / Cash）：市场过度波动或偏空，资本保全为首要任务。

### **第二部分：5%观察名单**
筛选5只股票代码，这些标的在当前交易日中具备技术面或基本面信号，存在上涨超过5%的潜在可能：
- 股票代码
- 胜率概率（Win Probability）
- 选择理由（Why I Picked It）
- 技术信号
- 催化剂类型和时间

## 🔧 Marcus Agent配置

### **自动化配置**
Marcus Agent已经配置为每日自动运行：
- **运行时间**: 每天上午9:00
- **输出文件**: Marcus_Daily_Report_YYYYMMDD.md（Markdown格式）
- **数据文件**: Marcus_Daily_Report_YYYYMMDD.json（JSON格式）
- **自动化ID**: `marcus-daily-momentum-report`

### **运行方式**
Marcus Agent有两种运行方式：

1. **自动化模式**: 每天9:00自动运行
2. **手动模式**: 运行以下命令：
```bash
python marcus_trading_agent.py
```

或使用PowerShell脚本：
```powershell
.\marcus_automation.ps1
```

## 📁 文件说明

### **核心文件**
1. **Marcus_Trading_Agent.md** - Marcus的完整人设配置和决策逻辑
2. **marcus_trading_agent.py** - Marcus的核心Python脚本
3. **marcus_automation.ps1** - PowerShell自动化脚本
4. **Marcus_Daily_Report_20260313.md** - 示例报告文件
5. **Marcus_Daily_Report_20260313.json** - 示例JSON数据文件

### **文件生成规则**
Marcus每天生成新的报告文件，文件名格式为：
- `Marcus_Daily_Report_YYYYMMDD.md`
- `Marcus_Daily_Report_YYYYMMDD.json`

## 🎯 Marcus的判断逻辑

### **市场立场决策模型**
Marcus根据以下指标决定市场立场：
1. **VIX指数**: <15 = 积极，15-20 = 中性，>20 = 谨慎
2. **股指期货**: >1%上涨 = 积极，±0.5%震荡 = 中性，< -1%下跌 = 谨慎
3. **盘前成交量**: >15%上涨 = 积极，平稳 = 中性，< -10%下跌 = 谨慎

### **5%观察名单筛选**
Marcus使用以下标准筛选股票：
1. **技术面筛选标准**（权重60%）:
   - 成交量异常（>3倍日均成交量）
   - 技术突破形态
   - RSI信号（<30超卖或>70超买）
   - 关键支撑/阻力位接近度

2. **基本面筛选标准**（权重40%）:
   - 财报催化剂强度
   - 行业催化剂强度
   - 催化剂时间窗口（临近度）

### **胜率概率计算**
```
胜率 = (技术面得分 × 60%) + (基本面得分 × 40%)

技术面得分 = Σ(各项技术指标得分)
基本面得分 = Σ(各项基本面指标得分)
```

## 🛠️ 扩展与优化

### **数据源集成**
当前Marcus使用模拟数据，可以集成以下真实数据源：
1. **VIX指数**: https://cn.investing.com/indices/volatility-s-p-500
2. **股指期货**: https://cn.investing.com/indices/us-30-futures
3. **股票数据**: https://www.gugudata.com/api/details/usfamous
4. **盘前成交量**: https://sapi.k780.com/?app=finance.stock_realtime
5. **财报日历**: https://finance.yahoo.com/calendar/earnings/

### **AI模型增强**
Marcus可以集成以下AI模型：
1. **机器学习预测**: 优化胜率概率计算
2. **自然语言处理**: 自动生成分析报告
3. **历史数据分析**: 优化筛选算法
4. **实时数据监控**: 自动更新数据源

### **通知集成**
Marcus可以配置以下通知渠道：
1. **邮件通知**: 每日发送报告邮件
2. **即时消息**: Slack/Teams/微信推送
3. **移动端**: 手机App推送
4. **API接口**: 外部系统集成

## 📈 Marcus的实战应用

### **交易策略示例**
基于Marcus的报告，可以执行以下交易策略：

**激进买入模式**:
- 高仓位参与技术突破和高动量股票
- 关注NVDA、TSLA等高波动性股票
- 设置5%止损纪律

**保守买入模式**:
- 小仓位参与，仅关注明确技术形态机会
- 优先关注RSI超卖反弹的MRNA和BNTX
- 关注关键技术位突破

**持币观望模式**:
- 保持资本，等待市场稳定
- 如出现极端波动机会（VIX > 25），可考虑少量反向交易

### **风险管理**
Marcus提醒：
1. 永远控制仓位大小
2. 保护本金是第一原则
3. 如市场突破VIX 20阈值，立即转为观望模式
4. 基于胜率概率调整仓位大小

## 🚀 Marcus的交易原则

1. **数据驱动**: 所有决策基于市场数据
2. **风险管理优先**: 追求进攻性增长的同时优先考虑风险管理
3. **简洁表达**: 像交易大厅老手一样自信、简洁
4. **概率判断**: 给出可执行的胜率概率判断，不提供模糊建议
5. **日内专注**: 专注于高波动性日内交易机会

Marcus会在每个交易日为你提供客观、专业的交易建议，帮助你捕捉日内交易机会。

---
**Marcus - 15年华尔街经验的日内交易策略师**