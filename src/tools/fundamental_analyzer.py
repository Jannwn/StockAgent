import os
import json
from datetime import datetime
from src.tools.openrouter_config import get_chat_completion, logger as api_logger
from src.prompts.agent_config import FUND_SYS_TEXT,FUND_REQ_TEXT
import time
import pandas as pd
import re

def get_fundmt_analyze(end_date:str,stock_fundmt_dict: dict,signal_text: str) -> float:
    """
    根据基本面指标分析股票走势
    Args:
        analysis_report (dict): 股票指标字典,包含股票名称-基本面指标

    Returns:
        list 按照股票上涨概率的排序
        str 分析过程
    """
    if not stock_fundmt_dict:
        return 0.0

    stock_list=stock_fundmt_dict.keys()

    # 准备系统消息
    system_message = {
        "role": "system",
        "content": FUND_SYS_TEXT
    }

    user_message = {
        "role": "user", #prompt
        "content": f"""提供股票列表{stock_list},股票基本面信息\n\n{stock_fundmt_dict}\n\n,{FUND_REQ_TEXT}
        """
    }

    try:
        # 获取基本面分析结果
        result = get_chat_completion([system_message, user_message])
        if result is None:
            print("Error: PI error occurred, LLM returned None")
            return 0.0

        # 提取数字结果
        result_dict = json.loads(result)
        content_value = result_dict['choices'][0]['message']['content']
        
        return {
            "fundanental_reason":content_value
        }

    except Exception as e:
        print(f"Error analyzing fundamental: {e}")
        return 0.0  # 出错时返回中性分数
