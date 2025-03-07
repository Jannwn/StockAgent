from langchain_core.messages import HumanMessage
from src.tools.openrouter_config import get_chat_completion
from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.tools.api import get_financial_metrics, get_financial_statements, get_market_data, get_price_history
from src.utils.logging_config import setup_logger

from datetime import datetime, timedelta
import pandas as pd

# 设置日志记录
logger = setup_logger('market_data_agent')


def market_data_agent(state: AgentState):
    """Responsible for gathering and preprocessing market data"""
    show_workflow_status("Market Data Agent")
    show_reasoning = state["metadata"]["show_reasoning"]

    messages = state["messages"]
    data = state["data"]

    # Set default dates
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)
    end_date = data["end_date"] or yesterday.strftime('%Y-%m-%d')

    # Ensure end_date is not in the future
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    if end_date_obj > yesterday:
        end_date = yesterday.strftime('%Y-%m-%d')
        end_date_obj = yesterday

    if not data["start_date"]:
        # Calculate 1 year before end_date
        start_date = end_date_obj - timedelta(days=365)  # 默认获取一年的数据
        start_date = start_date.strftime('%Y-%m-%d')
    else:
        start_date = data["start_date"]

    # Get all required data
    ticker_list = data["ticker_list"]

    # 获取价格数据并验证
    financial_metrics_dict={}
    financial_line_items_dict={}
    prices_df_dict={}
    market_data_dict={}
    market_cap_dict={}
    for ticker in ticker_list:
        prices_df = get_price_history(ticker, start_date, end_date)
        if prices_df is None or prices_df.empty:
            logger.warning(f"警告：无法获取{ticker}的价格数据，将使用空数据继续")
            prices_df = pd.DataFrame(
                columns=['close', 'open', 'high', 'low', 'volume'])
        if not isinstance(prices_df, pd.DataFrame):
            prices_df = pd.DataFrame(
                columns=['close', 'open', 'high', 'low', 'volume'])
        prices_dict = prices_df.to_dict(ticker)
        prices_df_dict[ticker] = prices_dict 
        
        # 获取财务指标
        try:
            financial_metrics = get_financial_metrics(ticker)
        except Exception as e:
            logger.error(f"获取财务指标失败: {str(e)}")
            financial_metrics = {}
        financial_metrics_dict[ticker] = financial_metrics

        # 获取财务报表
        try:
            financial_line_items = get_financial_statements(ticker)
        except Exception as e:
            logger.error(f"获取财务报表失败: {str(e)}")
            financial_line_items = {}
        financial_line_items_dict[ticker] = financial_line_items
        # 获取市场数据
        try:
            market_data = get_market_data(ticker)
        except Exception as e:
            logger.error(f"获取市场数据失败: {str(e)}")
            market_data = {"market_cap": 0}
        market_data_dict[ticker] = market_data
        market_cap_dict[ticker] = market_data.get("market_cap", 0)

    return {
        "messages": messages,
        "data": {
            **data,
            "prices": prices_df_dict,
            "start_date": start_date,
            "end_date": end_date,
            "financial_metrics": financial_metrics_dict,
            "financial_line_items": financial_line_items_dict,
            "market_cap": market_cap_dict,
            "market_data": market_data_dict,
        }
    }
