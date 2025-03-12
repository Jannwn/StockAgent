from langchain_core.messages import HumanMessage

from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.tools.fundamental_analyzer import get_fundmt_analyze
from src.utils.logging_config import setup_logger
import json

##### Fundamental Agent #####
SIGNAL_TEXT='''
1.Profitability Analysis (盈利能力分析):
Return on Equity (ROE): 衡量公司利用股东投资产生利润的能力。阈值: 大于 15% 被视为强劲。
Net Margin (净利润率): 衡量公司从总收入中获得的净利润比例。阈值: 大于 20% 被视为健康的利润率。
Operating Margin (营业利润率): 衡量公司在扣除运营费用后的利润率。阈值: 大于 15% 被视为强劲的运营效率。

2.Growth Analysis (增长分析):
Revenue Growth (收入增长): 衡量公司收入的增长速度。阈值: 大于 10% 被视为良好的增长。
Earnings Growth (盈利增长): 衡量公司盈利的增长速度。阈值: 大于 10% 被视为良好的增长。
Book Value Growth (账面价值增长): 衡量公司账面价值的增长速度。阈值: 大于 10% 被视为良好的增长。

3. Financial Health (财务健康):
Current Ratio (流动比率): 衡量公司短期资产与短期负债的比率。阈值: 大于 1.5 被视为强劲的流动性。
Debt to Equity Ratio (负债权益比): 衡量公司使用债务融资的程度。阈值: 小于 0.5 被视为保守的负债水平。
Free Cash Flow per Share (每股自由现金流): 衡量公司每股产生的自由现金流。阈值: 自由现金流应大于每股收益的 80% 被视为强劲的现金流转换能力。

4.Price to X Ratios (价格比率):
Price to Earnings (P/E) Ratio (市盈率): 衡量公司股票价格与每股收益的比率。阈值: 小于 25 被视为合理。
Price to Book (P/B) Ratio (市净率): 衡量公司股票价格与每股账面价值的比率。阈值: 小于 3 被视为合理。
Price to Sales (P/S) Ratio (市销率): 衡量公司股票价格与每股销售额的比率。阈值: 小于 5 被视为合理。"
'''

def fundamentals_agent(state: AgentState):
    """Responsible for fundamental analysis"""
    show_workflow_status("Fundamentals Analyst")
    show_reasoning = state["metadata"]["show_reasoning"]
    data = state["data"]
    end_date = data["end_date"]

    results={}
    for ticker in data["ticker_list"]:
        metrics = data["financial_metrics"][ticker][0]
        results[ticker]=fundamental_analyse(metrics)

    message_content = {
        "results": results
    }
    message_text=get_fundmt_analyze(end_date,results,SIGNAL_TEXT)
    # Create the fundamental analysis message
    message = HumanMessage(
        content=json.dumps(message_text),
        name="fundamentals_agent",
    )

    # Print the reasoning if the flag is set
    if show_reasoning:
        show_agent_reasoning(message_content, "Fundamental Analysis Agent")

    show_workflow_status("Fundamentals Analyst", "completed")
    return {
        "messages": [message],
        "data": {
            **data,
            "fundamental_analysis": message_content
        }
    }



def fundamental_analyse(metrics):
    # Initialize signals list for different fundamental aspects
    signals = []
    reasoning = {}

    # 1. Profitability Analysis
    return_on_equity = metrics.get("return_on_equity", 0)
    net_margin = metrics.get("net_margin", 0)
    operating_margin = metrics.get("operating_margin", 0)

    thresholds = [
        (return_on_equity, 0.15),  # Strong ROE above 15%
        (net_margin, 0.20),  # Healthy profit margins
        (operating_margin, 0.15)  # Strong operating efficiency
    ]
    profitability_score = sum(
        metric is not None and metric > threshold
        for metric, threshold in thresholds
    )

    signals.append('bullish' if profitability_score >=
                   2 else 'bearish' if profitability_score == 0 else 'neutral')
    reasoning["profitability_signal"] = {
        "signal": signals[0],
        "details": (
            f"ROE: {metrics.get('return_on_equity', 0):.2%}" if metrics.get(
                "return_on_equity") is not None else "ROE: N/A"
        ) + ", " + (
            f"Net Margin: {metrics.get('net_margin', 0):.2%}" if metrics.get(
                "net_margin") is not None else "Net Margin: N/A"
        ) + ", " + (
            f"Op Margin: {metrics.get('operating_margin', 0):.2%}" if metrics.get(
                "operating_margin") is not None else "Op Margin: N/A"
        )
    }

    # 2. Growth Analysis
    revenue_growth = metrics.get("revenue_growth", 0)
    earnings_growth = metrics.get("earnings_growth", 0)
    book_value_growth = metrics.get("book_value_growth", 0)

    thresholds = [
        (revenue_growth, 0.10),  # 10% revenue growth
        (earnings_growth, 0.10),  # 10% earnings growth
        (book_value_growth, 0.10)  # 10% book value growth
    ]
    growth_score = sum(
        metric is not None and metric > threshold
        for metric, threshold in thresholds
    )

    signals.append('bullish' if growth_score >=
                   2 else 'bearish' if growth_score == 0 else 'neutral')
    reasoning["growth_signal"] = {
        "signal": signals[1],
        "details": (
            f"Revenue Growth: {metrics.get('revenue_growth', 0):.2%}" if metrics.get(
                "revenue_growth") is not None else "Revenue Growth: N/A"
        ) + ", " + (
            f"Earnings Growth: {metrics.get('earnings_growth', 0):.2%}" if metrics.get(
                "earnings_growth") is not None else "Earnings Growth: N/A"
        )
    }

    # 3. Financial Health
    current_ratio = metrics.get("current_ratio", 0)
    debt_to_equity = metrics.get("debt_to_equity", 0)
    free_cash_flow_per_share = metrics.get("free_cash_flow_per_share", 0)
    earnings_per_share = metrics.get("earnings_per_share", 0)

    health_score = 0
    if current_ratio and current_ratio > 1.5:  # Strong liquidity
        health_score += 1
    if debt_to_equity and debt_to_equity < 0.5:  # Conservative debt levels
        health_score += 1
    if (free_cash_flow_per_share and earnings_per_share and
            free_cash_flow_per_share > earnings_per_share * 0.8):  # Strong FCF conversion
        health_score += 1

    signals.append('bullish' if health_score >=
                   2 else 'bearish' if health_score == 0 else 'neutral')
    reasoning["financial_health_signal"] = {
        "signal": signals[2],
        "details": (
            f"Current Ratio: {metrics.get('current_ratio', 0):.2f}" if metrics.get(
                "current_ratio") is not None else "Current Ratio: N/A"
        ) + ", " + (
            f"D/E: {metrics.get('debt_to_equity', 0):.2f}" if metrics.get(
                "debt_to_equity") is not None else "D/E: N/A"
        )
    }

    # 4. Price to X ratios
    pe_ratio = metrics.get("pe_ratio", 0)
    price_to_book = metrics.get("price_to_book", 0)
    price_to_sales = metrics.get("price_to_sales", 0)

    thresholds = [
        (pe_ratio, 25),  # Reasonable P/E ratio
        (price_to_book, 3),  # Reasonable P/B ratio
        (price_to_sales, 5)  # Reasonable P/S ratio
    ]
    price_ratio_score = sum(
        metric is not None and metric < threshold
        for metric, threshold in thresholds
    )

    signals.append('bullish' if price_ratio_score >=
                   2 else 'bearish' if price_ratio_score == 0 else 'neutral')
    reasoning["price_ratios_signal"] = {
        "signal": signals[3],
        "details": (
            f"P/E: {pe_ratio:.2f}" if pe_ratio else "P/E: N/A"
        ) + ", " + (
            f"P/B: {price_to_book:.2f}" if price_to_book else "P/B: N/A"
        ) + ", " + (
            f"P/S: {price_to_sales:.2f}" if price_to_sales else "P/S: N/A"
        )
    }

    indicators = {
        "Return on Equity (ROE)":return_on_equity, 
        "net_margin":net_margin, 
        "operating_margin":operating_margin,
        "revenue_growth":revenue_growth, 
        "earnings_growth":earnings_growth, 
        "book_value_growth":book_value_growth,
        "current_ratio":current_ratio, 
        "debt_to_equity":debt_to_equity,
        "free_cash_flow_per_share":free_cash_flow_per_share, 
        "earnings_per_share":earnings_per_share,
        "pe_ratio":pe_ratio,"price_to_book":price_to_book,
        "price_to_sales":price_to_sales    
    }

    return {'indicators':indicators,'signals':signals,'reasoning':reasoning}
