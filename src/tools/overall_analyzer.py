import os
import json
from datetime import datetime
from src.tools.openrouter_config import get_chat_completion, logger as api_logger
import time
import pandas as pd
import re
def get_bullish_analyze(end_date:str,stock_list:list,reasoning_dict: dict) :

    if not reasoning_dict:
        return 0.0

    # 准备系统消息
    system_message = {
        "role": "system",
        "content": """
        你是一个专业的股票投资者,尤其擅长对A股市场股票相关指标进行分析.你对市场走势的整体看法是乐观的,认为市场整体会上涨.
        你需要分析一组股票的多方面指标,综合这些指标给出并针对每个股票给出介于-1到1之间的分数,还要给出基于分数的信心指数
        我希望获得如下形式的回答:
        -1表示极其积极-0.5到0.9表示积极
        -0表示中性--0.5到-0.9表示消极
        --1表示极其消极

        避免模糊回答,结合这些基本面/价值/技术/情感分析指标的实际含义
        确保你的分析是符合经济学规律的,且数据一定要是来源于提供的真实数据.
        """
    }

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{stock_list}相关综合指标,对比并计算每只的股票的未来价格:\n\n{reasoning_dict}\n\n
        使用股票基本面分析、财务分析、价值投资、交易理论等专业知识,避免模糊的回答，用词专业.
        首先返回一列综合指标进行打分的数字,范围是-1到1,越接近1证明上涨概率越大,记作'结果:[股票列表:分数]',例如'结果:[股票代码1:0.8,股票代码2:-0.5]'.
        给出你认为这样判断的信心指数,范围是0到1,越接近1证明你越有信心,记作'信心指数:0.8'.
        之后,结合你所获得的推理过程/相关指标数据和相关解释,用1000字分点列出做出该判断的理由,要求有理有据且表述明确,不要用模糊的词汇,
        做出你觉得最可能的判断记作'原因:...分析过程'.你的原因分析中要保留指标数值等关键信息,且确保信息是正确的.
        """
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
        "content": """
        你是一个专业的股票投资者,尤其擅长对A股市场股票相关指标进行分析.你对市场走势的整体看法是悲观的,认为市场整体会进入熊市.
        你需要分析一组股票的多方面指标,综合这些指标给出并针对每个股票给出介于-1到1之间的分数,还要给出基于分数的信心指数
        我希望获得如下形式的回答:
        -1表示极其积极-0.5到0.9表示积极
        -0表示中性--0.5到-0.9表示消极
        --1表示极其消极

        避免模糊回答,结合这些基本面/价值/技术/情感分析指标的实际含义
        确保你的分析是符合经济学规律的,且数据一定要是来源于提供的真实数据.
        """
    }

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{stock_list}相关综合指标,对比并计算每只的股票的未来价格:\n\n{reasoning_dict}\n\n
        使用股票基本面分析、财务分析、价值投资、交易理论等专业知识,避免模糊的回答，用词专业.
        首先返回一列综合指标进行打分的数字,范围是-1到1,越接近1证明上涨概率越大,记作'结果:[股票列表:分数]',例如'结果:[股票代码1:0.8,股票代码2:-0.5]'.
        给出你认为这样判断的信心指数,范围是0到1,越接近1证明你越有信心,记作'信心指数:0.8'.
        之后,结合你所获得的推理过程/相关指标数据和相关解释,用1000字分点列出做出该判断的理由,要求有理有据且表述明确,不要用模糊的词汇,
        做出你觉得最可能的判断记作'原因:...分析过程'.你的原因分析中要保留指标数值等相关信息.
        """
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
        "content": """
        你是一个经验丰富的股票基金经理,尤其擅长对A股市场股票相关指标进行分析.现在你将判断从两方面视角进行的股票评估,一方认为市场会上涨,另一方认为市场会下跌.
        仔细审理它们的逻辑,找出更能说服你的一方. 综合这些指标和分析过程给出并针对每个股票给出涨或跌的判断,还要给出基于分数的信心指数
        我希望获得如下形式的回答: 1 表示看涨 0 表示看跌
        避免模糊回答,结合分析是否具有逻辑性以及基本面/价值/技术/情感分析指标的实际含义
        确保你的分析是符合经济学规律的,且数据一定要是来源于提供的真实数据.
        """
    }

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{stock_list}相关综合指标,对比并计算每只的股票的未来价格:
        以下数据中结果后的list代表对股票列表中股票依次主观打分后的结果(分数介于1~-1之间越大代表上涨概率越大),信心代表对该结果的把握.
        \n\n从乐观视角看分析如下{bull_dict}\n\n从悲观视角下分析如下{bear_dict}\n\n
        使用股票基本面分析、财务分析、价值投资、交易理论等专业知识,比对双方观点.仔细审理它们的逻辑,找出更能说服你的一方. 
        综合这些指标和分析过程给出并针对每个股票给出涨或跌的判断,还要给出基于分数的信心指数 避免模糊的回答，用词专业.
        首先返回一列对股票上涨下跌的判断,取值为1或0或-1,1代表上涨,-1代表下跌,如果对判断结果单个信心低于0.2,记作0. 
        将你的判断记作'股票预测:[股票列表:分数]',例如'股票预测:[股票代码1:-1,股票代码2:0]'.
        给出你认为这样判断的整体信心指数,范围是0到1,越接近1证明你越有信心,记作'信心指数:0.8'.
        之后,结合你所获得的推理过程&相关指标数据和相关解释,用1000字分点列出做出该判断的理由,要求有理有据且表述明确,不要用模糊的词汇,
        做出你觉得最可能的判断记作'原因:...分析过程'.你的原因分析中要保留指标数值等关键信息,且确保信息是正确的.
        """
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
