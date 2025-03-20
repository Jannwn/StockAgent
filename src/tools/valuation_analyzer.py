import os
import json
from datetime import datetime
from src.tools.openrouter_config import get_chat_completion, logger as api_logger
from src.prompts.signal_config import VALUE_SIGNAL_TEXT
import time
import pandas as pd
import re

def calculate_owner_earnings_value(
    net_income: float,
    depreciation: float,
    capex: float,
    working_capital_change: float,
    growth_rate: float = 0.05,
    required_return: float = 0.15,
    margin_of_safety: float = 0.25,
    num_years: int = 5
) -> float:
    """
    使用改进的所有者收益法计算公司价值.

    Args:
        net_income: 净利润
        depreciation: 折旧和摊销
        capex: 资本支出
        working_capital_change: 营运资金变化
        growth_rate: 预期增长率
        required_return: 要求回报率
        margin_of_safety: 安全边际
        num_years: 预测年数

    Returns:
        float: 计算得到的公司价值
    """
    try:
        # 数据有效性检查
        if not all(isinstance(x, (int, float)) for x in [net_income, depreciation, capex, working_capital_change]):
            return 0

        # 计算初始所有者收益
        owner_earnings = (
            net_income +
            depreciation -
            capex -
            working_capital_change
        )

        if owner_earnings <= 0:
            return 0

        # 调整增长率,确保合理性
        growth_rate = min(max(growth_rate, 0), 0.25)  # 限制在0-25%之间

        # 计算预测期收益现值
        future_values = []
        for year in range(1, num_years + 1):
            # 使用递减增长率模型
            year_growth = growth_rate * (1 - year / (2 * num_years))  # 增长率逐年递减
            future_value = owner_earnings * (1 + year_growth) ** year
            discounted_value = future_value / (1 + required_return) ** year
            future_values.append(discounted_value)

        # 计算永续价值
        terminal_growth = min(growth_rate * 0.4, 0.03)  # 永续增长率取增长率的40%或3%的较小值
        terminal_value = (
            future_values[-1] * (1 + terminal_growth)) / (required_return - terminal_growth)
        terminal_value_discounted = terminal_value / \
            (1 + required_return) ** num_years

        # 计算总价值并应用安全边际
        intrinsic_value = sum(future_values) + terminal_value_discounted
        value_with_safety_margin = intrinsic_value * (1 - margin_of_safety)

        return max(value_with_safety_margin, 0)  # 确保不返回负值

    except Exception as e:
        print(f"所有者收益计算错误: {e}")
        return 0

def calculate_intrinsic_value(
    free_cash_flow: float,
    growth_rate: float = 0.05,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.02,
    num_years: int = 5,
) -> float:
    """
    使用改进的DCF方法计算内在价值,考虑增长率和风险因素.

    Args:
        free_cash_flow: 自由现金流
        growth_rate: 预期增长率
        discount_rate: 基础折现率
        terminal_growth_rate: 永续增长率
        num_years: 预测年数

    Returns:
        float: 计算得到的内在价值
    """
    try:
        if not isinstance(free_cash_flow, (int, float)) or free_cash_flow <= 0:
            return 0

        # 调整增长率,确保合理性
        growth_rate = min(max(growth_rate, 0), 0.25)  # 限制在0-25%之间

        # 调整永续增长率,不能超过经济平均增长
        terminal_growth_rate = min(growth_rate * 0.4, 0.03)  # 取增长率的40%或3%的较小值

        # 计算预测期现金流现值
        present_values = []
        for year in range(1, num_years + 1):
            future_cf = free_cash_flow * (1 + growth_rate) ** year
            present_value = future_cf / (1 + discount_rate) ** year
            present_values.append(present_value)

        # 计算永续价值
        terminal_year_cf = free_cash_flow * (1 + growth_rate) ** num_years
        terminal_value = terminal_year_cf * \
            (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        terminal_present_value = terminal_value / \
            (1 + discount_rate) ** num_years

        # 总价值
        total_value = sum(present_values) + terminal_present_value

        return max(total_value, 0)  # 确保不返回负值

    except Exception as e:
        print(f"DCF计算错误: {e}")
        return 0

def calculate_working_capital_change(
    current_working_capital: float,
    previous_working_capital: float,
) -> float:
    """
    Calculate the absolute change in working capital between two periods.
    A positive change means more capital is tied up in working capital (cash outflow).
    A negative change means less capital is tied up (cash inflow).

    Args:
        current_working_capital: Current period's working capital
        previous_working_capital: Previous period's working capital

    Returns:
        float: Change in working capital (current - previous)
    """
    return current_working_capital - previous_working_capital

def valuation_analyse(metrics,current_financial_line_item,previous_financial_line_item,market_cap):
    reasoning = {}
    # Calculate working capital change
    working_capital_change = (current_financial_line_item.get(
        'working_capital') or 0) - (previous_financial_line_item.get('working_capital') or 0)

    # Owner Earnings Valuation (Buffett Method)
    owner_earnings_value = calculate_owner_earnings_value(
        net_income=current_financial_line_item.get('net_income'),
        depreciation=current_financial_line_item.get(
            'depreciation_and_amortization'),
        capex=current_financial_line_item.get('capital_expenditure'),
        working_capital_change=working_capital_change,
        growth_rate=metrics["earnings_growth"],
        required_return=0.15,
        margin_of_safety=0.25
    )

    # DCF Valuation
    dcf_value = calculate_intrinsic_value(
        free_cash_flow=current_financial_line_item.get('free_cash_flow'),
        growth_rate=metrics["earnings_growth"],
        discount_rate=0.10,
        terminal_growth_rate=0.03,
        num_years=5,
    )

    # Calculate combined valuation gap (average of both methods)
    dcf_gap = (dcf_value - market_cap) / market_cap
    owner_earnings_gap = (owner_earnings_value - market_cap) / market_cap
    valuation_gap = (dcf_gap + owner_earnings_gap) / 2

    if valuation_gap > 0.10:  # Changed from 0.15 to 0.10 (10% undervalued)
        signal = 'bullish'
    elif valuation_gap < -0.20:  # Changed from -0.15 to -0.20 (20% overvalued)
        signal = 'bearish'
    else:
        signal = 'neutral'

    reasoning['factors'] = {
        'working_capital_change': working_capital_change,
        'owner_earnings_value': owner_earnings_value,
        'dcf_value': dcf_value,
        'dcf_gap': dcf_gap,
        'owner_earnings_gap': owner_earnings_gap,
        'valuation_gap': valuation_gap
    }

    reasoning["dcf_analysis"] = {
        "signal": "bullish" if dcf_gap > 0.10 else "bearish" if dcf_gap < -0.20 else "neutral",
        "details": f"Intrinsic Value: ${dcf_value:,.2f}, Market Cap: ${market_cap:,.2f}, Gap: {dcf_gap:.1%}"
    }

    reasoning["owner_earnings_analysis"] = {
        "signal": "bullish" if owner_earnings_gap > 0.10 else "bearish" if owner_earnings_gap < -0.20 else "neutral",
        "details": f"Owner Earnings Value: ${owner_earnings_value:,.2f}, Market Cap: ${market_cap:,.2f}, Gap: {owner_earnings_gap:.1%}"
    }

    reasoning["valuation_gap_analysis"] = {
        "signal": signal,
        "details": f"Combined Valuation Gap: {valuation_gap:.1%}"
    }
    return reasoning

def get_value_analyze(end_date:str,stock_value_dict: dict,signal_text: str) -> float:

    if not stock_value_dict:
        return 0.0

    stock_list=stock_value_dict.keys()


    # 准备系统消息
    system_message = {
        "role": "system",
        "content": """
        你是一个专业的股票投资者,尤其擅长对A股市场股票相关价值投资指标进行分析.
        你需要分析一组股票的价值投资指标,并针对每个股票给出介于-1到1之间的分数.
        我希望获得如下形式的回答:
        -1表示极其积极(例如: ROE、净利润率、毛利率等指标稳定在高位)
        -0.5到0.9表示积极(例如: 指标有所增长，且高于行业平均水平)
        -0表示中性(例如: 指标波动不大，未显示明显趋势)
        --0.5到-0.9表示消极(例如: 指标有所下降，且低于行业平均水平)
        --1表示极其消极(例如: 指标持续恶化，财务健康状况堪忧)

        分析时重点关注:
        1. 相对比较法:
            将目标公司的价值投资指标与同行业其他公司的相应指标进行比较，以评估其相对表现。关注行业平均水平和领先公司的数据，识别目标公司的优势和劣势。
        2. 历史趋势分析:
        分析公司的历史财务数据，识别其各项指标的趋势变化。关注指标的稳定性和持续性，判断公司是否具备长期增长潜力。
        3. 因果关系分析:
        考虑不同财务指标之间的因果关系，例如，收入增长对净利润的影响。识别关键驱动因素，分析其对公司整体财务健康的影响。
        4. 情景分析:
        设定不同的市场情景(如经济衰退、行业增长等)，评估公司在各种情况下的表现。通过模拟不同假设，判断公司的抗风险能力和适应性。
        5. 定性分析:
        除了定量指标外，考虑公司的管理团队、行业地位、市场竞争力等定性因素。评估公司的战略规划、创新能力和品牌价值等非财务因素对未来表现的影响。

        避免模糊回答,结合价值投资指标的实际含义,确保你的分析是合理的,且数据一定要是来源于提供的真实数据.
        """
    }

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{stock_list}相关价值投资指标,对比并计算每只的股票的未来价格:\n\n{stock_value_dict}\n\n
        使用股票价值投资分析、财务分析、交易理论等专业知识,避免模糊的回答，用词专业.
        首先返回一列对价值投资指标综合打分的数字,范围是-1到1,越接近1证明上涨概率越大,记作'结果:[股票列表:分数]',例如'结果:[股票代码1:0.8,股票代码2:-0.5]'.
        之后,结合你所获得的价值投资指标和相关解释,用1000字分点列出做出该判断的理由,要求有理有据且表述明确,不要用模糊的词汇,
        做出你觉得最可能的判断记作'原因:...分析过程'.
        """
    }

    try:
        # 获取价值投资分析结果
        result = get_chat_completion([system_message, user_message])
        if result is None:
            print("Error: PI error occurred, LLM returned None")
            return 0.0

        # 提取数字结果
        result_dict = json.loads(result)
        content_value = result_dict['choices'][0]['message']['content']  
        return {
            "value_reason":content_value
        }
    except Exception as e:
        print(f"Error analyzing value: {e}")
        return 0.0  # 出错时返回中性分数
