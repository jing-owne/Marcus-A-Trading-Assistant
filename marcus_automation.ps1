# Marcus Trading Agent自动化脚本
# PowerShell脚本用于自动运行Marcus Agent并发送Daily Momentum Report

param (
    [string]$OutputPath = "Marcus_Daily_Report"
)

# 设置工作目录
$workingDir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
Set-Location $workingDir

# 生成报告的文件名
$date = Get-Date -Format "yyyyMMdd"
$reportFile = "$OutputPath_$date.md"
$jsonFile = "$OutputPath_$date.json"

# 检查Python环境
$pythonVersion = python --version
Write-Host "检查Python环境: $pythonVersion"

# 运行Marcus Agent
Write-Host "🔄 启动Marcus Trading Agent..."
python marcus_trading_agent.py

# 检查生成的报告
if (Test-Path $reportFile) {
    Write-Host "✅ Marcus Daily Momentum Report已生成: $reportFile"
    
    # 读取报告内容
    $reportContent = Get-Content $reportFile -Raw
    
    # 显示摘要信息
    Write-Host ""
    Write-Host "📊 Marcus Daily Momentum Report摘要"
    Write-Host ""
    
    # 提取Marcus市场立场
    $positionLine = $reportContent | Select-String -Pattern "Marcus判断"
    if ($positionLine) {
        Write-Host "Marcus的市场立场: $($positionLine.Matches[0].Value)"
    }
    
    # 提取观察名单股票
    $watchlistLines = $reportContent | Select-String -Pattern "股票代码："
    Write-Host "今日观察名单:"
    foreach ($line in $watchlistLines) {
        Write-Host "  $($line.Matches[0].Value)"
    }
    
    Write-Host ""
    Write-Host "📁 报告文件位置:"
    Write-Host "  1. Markdown报告: $reportFile"
    Write-Host "  2. JSON数据: $jsonFile"
    Write-Host "  3. Marcus配置文件: Marcus_Trading_Agent.md"
    Write-Host "  4. Python脚本: marcus_trading_agent.py"
    
    # 发送邮件通知（可选）
    # Write-Host "📧 发送邮件通知..."
    # Send-MailMessage -From "Marcus@trading.com" -To "youremail@example.com" -Subject "Marcus Daily Momentum Report - $date" -Body $reportContent -SmtpServer "smtp.example.com"
    
} else {
    Write-Host "❌ 报告文件未找到，请检查Python脚本运行是否成功"
    Write-Host "尝试手动运行: python marcus_trading_agent.py"
}

Write-Host ""
Write-Host "🎯 Marcus Trading Agent运行完成"
Write-Host "Marcus的忠告: '永远控制仓位大小，保护本金是第一原则'"