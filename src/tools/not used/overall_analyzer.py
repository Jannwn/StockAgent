import os
import json
from datetime import datetime
from src.tools.openrouter_config import get_chat_completion, logger as api_logger
from src.prompts.agent_config import BULL_SYS_TEXT,BULL_REQ_TEXT,BEAR_SYS_TEXT,BEAR_REQ_TEXT,DEBATE_SYS_TEXT,DEBATE_REQ_TEXT
import time
import pandas as pd
import re
def get_bullish_analyze(end_date:str,stock_list:list,reasoning_dict: dict) :

    if not reasoning_dict:
        return 0.0

    # 准备系统消息
    system_message = {
        "role": "system",
        "content": BULL_SYS_TEXT
    }

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{stock_list}相关综合指标,\n\n{reasoning_dict}\n\n
        {BULL_REQ_TEXT}"""
    }

    try:
        result = get_chat_completion([system_message, user_message])
        if result is None:
            print("Error: PI error occurred, LLM returned None")
            return 0.0

        result_dict = json.loads(result)
        content_value = result_dict['choices'][0]['message']['content']
        
        return content_value
    
    except Exception as e:
        print(f"Error analyzing fundamental: {e}")
        return 0.0
    
def get_bearish_analyze(end_date:str,stock_list:list,reasoning_dict: dict) :

    if not reasoning_dict:
        return 0.0

    # 准备系统消息
    system_message = {
        "role": "system",
        "content": BEAR_SYS_TEXT
    }

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{stock_list}相关综合指标,对比并计算每只的股票的未来价格:\n\n{reasoning_dict}\n\n
        {BEAR_REQ_TEXT}"""

    }

    try:
        result = get_chat_completion([system_message, user_message])
        if result is None:
            print("Error: PI error occurred, LLM returned None")
            return 0.0

        result_dict = json.loads(result)
        content_value = result_dict['choices'][0]['message']['content']
        
        return content_value
    
    except Exception as e:
        print(f"Error analyzing fundamental: {e}")
        return 0.0

def get_debate_analyze(end_date:str,stock_list:list,bull_dict: dict,bear_dict: dict):

    # 准备系统消息
    system_message = {
        "role": "system",
        "content": DEBATE_SYS_TEXT

    }

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{stock_list}相关综合指标,对比并计算每只的股票的未来价格:
        \n\n从乐观视角看分析如下{bull_dict}\n\n从悲观视角下分析如下{bear_dict}\n\n
        {DEBATE_REQ_TEXT}"""

    }

    try:
        result = get_chat_completion([system_message, user_message])
        if result is None:
            print("Error: PI error occurred, LLM returned None")
            return 0.0

        result_dict = json.loads(result)
        content_value = result_dict['choices'][0]['message']['content']
        
        return content_value
    
    except Exception as e:
        print(f"Error analyzing fundamental: {e}")
        return 0.0
