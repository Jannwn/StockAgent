from langchain_core.messages import HumanMessage
from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
import json
from src.tools.valuation_analyzer import get_value_analyze

SIGNAL_TEXT='''
1. valuation_gap:含义: 反映公司内在价值与市场资本化的差距.
判断标准:> 0.10: 表示公司被低估10%以上,可能是买入信号.< -0.20: 表示公司被高估20%以上,可能是卖出信号.
在 -0.20 到 0.10 之间,表示市场对公司的估值合理.
2.dcf_gap:含义: 基于折现现金流法(DCF)计算的内在价值与市场资本化的差距.
判断标准:> 0.10: 表示内在价值高于市场资本化10%以上,可能是买入信号.< -0.20: 表示内在价值低于市场资本化20%以上,可能是卖出信号.
在 -0.20 到 0.10 之间,表示市场对公司的估值合理.
3.owner_earnings_gap:
含义: 基于业主收益法计算的内在价值与市场资本化的差距.
判断标准:> 0.10: 表示业主收益高于市场资本化10%以上,可能是买入信号.< -0.20: 表示业主收益低于市场资本化20%以上,可能是卖出信号.
在 -0.20 到 0.10 之间,表示市场对公司的估值合理.
4. working_capital_change：反映当前财务报表与之前财务报表之间的营运资本变化.营运资本是公司用于日常运营的资金,计算方式为流动资产减去流动负债.正值表示公司在流动资产方面的改善,可能意味着公司有更好的短期财务健康状况.
5.owner_earnings_value:基于业主收益法（Buffett Method）计算的公司内在价值.业主收益是指公司在扣除必要支出后,能够为股东创造的现金流.这个值可以帮助投资者评估公司在长期内的盈利能力和价值.
6.dcf_value:基于折现现金流（Discounted Cash Flow, DCF）模型计算的公司内在价值.DCF 方法通过预测未来现金流并将其折现到现值,来评估公司的真实价值.这个值是判断公司是否被市场低估或高估的重要依据.
'''

def valuation_agent(state: AgentState):
    """Responsible for valuation analysis"""
    show_workflow_status("Valuation Agent")
    show_reasoning = state["metadata"]["show_reasoning"]
    data = state["data"]
    end_date = data["end_date"]

    results={}
    for ticker in data["ticker_list"]:
        metrics = data["financial_metrics"][ticker][0]
        current_financial_line_item = data["financial_line_items"][ticker][0]
        previous_financial_line_item = data["financial_line_items"][ticker][1]
        market_cap = data["market_cap"][ticker]
        results[ticker]=valuation_analyse(metrics,current_financial_line_item,previous_financial_line_item,market_cap)
    
    message_content = {"results": results}
    message_text=get_value_analyze(end_date,results,SIGNAL_TEXT)
    message = HumanMessage(
        content=json.dumps(message_text),
        name="valuation_agent",
    )

    if show_reasoning:
        show_agent_reasoning(message_content, "Valuation Analysis Agent")

    show_workflow_status("Valuation Agent", "completed")
    return {
        "messages": [message],
        "data": {
            **data,
            "valuation_analysis": message_content
        }
    }


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