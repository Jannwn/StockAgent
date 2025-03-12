import os
import json
from datetime import datetime
from src.tools.openrouter_config import get_chat_completion, logger as api_logger
import time
import pandas as pd
import re

def get_tech_analyze(end_date:str,stock_tech_dict: dict,signal_text: str,strategy_text:str) -> float:
    """
    根据技术指标分析股票走势
    Args:
        analysis_report (dict): 股票指标字典,包含股票名称-技术指标

    Returns:
        list 按照股票上涨概率的排序
        str 分析过程
    """
    if not stock_tech_dict:
        return 0.0
    
    stock_list=stock_tech_dict.keys()

    # 准备系统消息
    system_message = {
        "role": "system",
        "content": """
        你是一个专业的股票投资者,尤其擅长对A股市场k线以及相关技术指标进行分析.
        你需要分析一组股票的技术指标,并针对每个股票给出介于-1到1之间的分数.
        我希望获得如下形式的回答:
        - 1表示极其积极(例如:连续稳定上涨,指标稳定在高位)
        - 0.5到0.9表示积极(例如:技术指标向上突破、金叉、MACD稳定)
        - 0表示中性(例如:技术指标波动较大,难以判断)
        - -0.5到-0.9表示消极(例如:技术指标向下突破、死叉、MACD下行)
        - -1表示极其消极(例如:连续稳定下跌,指标稳定在低位)

        分析时重点关注:
        1. K线形态:包括各种形态的意义
        2. 技术指标:MACD、KDJ、RSI、均线等
        3. 交易信号:金叉、死叉、突破等
        4. 走势预测:趋势、震荡、反转等
        5. 风险提示:技术指标的局限性、市场风险等
        6. 量价关系:成交量与价格的关系等
        7. 历史回顾:技术指标的历史表现等

        结合技术指标的实际含义,确保你的分析是合理的,且数据一定要是来源于提供的真实数据.
        """
    }

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{stock_list}相关新闻,对比并计算每只的股票的技术指标:\n\n{stock_tech_dict}\n\n
        使用股票技术指标、交易理论等专业知识,避免模糊的回答，用词专业.
        首先返回一列对技术指标综合打分的数字,范围是-1到1,越接近1证明上涨概率越大,记作'结果:[股票列表:分数]',例如'结果:[股票代码1:0.8,股票代码2:-0.5]'.
        之后,结合你所获得的技术指标和相关解释,用1000字分点列出做出该判断的理由,要求有理有据且表述明确,不要用模糊的词汇,
        做出你觉得最可能的判断记作'原因:分析过程'.
        """
    }

    try:
        # 获取技术分析结果
        result = get_chat_completion([system_message, user_message])
        if result is None:
            print("Error: PI error occurred, LLM returned None")
            return 0.0

        # 提取数字结果
        result_dict = json.loads(result)
        content_value = result_dict['choices'][0]['message']['content']
        return {'technical_reason':content_value}

    except Exception as e:
        print(f"Error analyzing news sentiment: {e}")
        return 0.0  # 出错时返回中性分数