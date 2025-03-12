import os
import json
from datetime import datetime
from src.tools.openrouter_config import get_chat_completion, logger as api_logger
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
        "content": """
        你是一个专业的股票投资者,尤其擅长对A股市场股票相关基本面指标进行分析.
        你需要分析一组股票的基本面指标,并针对每个股票给出介于-1到1之间的分数.
        我希望获得如下形式的回答:
        -1表示极其积极（例如: ROE、净利润率、毛利率等指标稳定在高位）
        -0.5到0.9表示积极（例如: 指标有所增长，且高于行业平均水平）
        -0表示中性（例如: 指标波动不大，未显示明显趋势）
        --0.5到-0.9表示消极（例如: 指标有所下降，且低于行业平均水平）
        --1表示极其消极（例如: 指标持续恶化，财务健康状况堪忧）

        分析时重点关注:
        1. 相对比较法:
            将目标公司的基本面指标与同行业其他公司的相应指标进行比较，以评估其相对表现。关注行业平均水平和领先公司的数据，识别目标公司的优势和劣势。
        2. 历史趋势分析:
        分析公司的历史财务数据，识别其各项指标的趋势变化。关注指标的稳定性和持续性，判断公司是否具备长期增长潜力。
        3. 因果关系分析:
        考虑不同财务指标之间的因果关系，例如，收入增长对净利润的影响。识别关键驱动因素，分析其对公司整体财务健康的影响。
        4. 情景分析:
        设定不同的市场情景（如经济衰退、行业增长等），评估公司在各种情况下的表现。通过模拟不同假设，判断公司的抗风险能力和适应性。
        5. 定性分析:
        除了定量指标外，考虑公司的管理团队、行业地位、市场竞争力等定性因素。评估公司的战略规划、创新能力和品牌价值等非财务因素对未来表现的影响。

        避免模糊回答,结合基本面指标的实际含义,确保你的分析是合理的,且数据一定要是来源于提供的真实数据.
        """
    }

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{stock_list}相关基本面指标,对比并计算每只的股票的未来价格:\n\n{stock_fundmt_dict}\n\n
        使用股票基本面分析、财务分析、交易理论等专业知识,避免模糊的回答，用词专业.
        首先返回一列对基本面指标综合打分的数字,范围是-1到1,越接近1证明上涨概率越大,记作'结果:[股票列表:分数]',例如'结果:[股票代码1:0.8,股票代码2:-0.5]'.
        之后,结合你所获得的基本面指标和相关解释,用1000字分点列出做出该判断的理由,要求有理有据且表述明确,不要用模糊的词汇,
        做出你觉得最可能的判断记作'原因:...分析过程'.
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
    

'''

match = re.search(r'结果：\s*\[(.*?)\]', content_value)
            match_r = re.search(r'原因：\s*(.*)', content_value)
            if match:
                # 提取匹配到的数字字符串
                fundamental_str = match.group(1)
                fundamental_reason=match_r.group(1)
                try:
                    fundamental_score_list = [float(num.strip()) for num in fundamental_str]
                except ValueError:
                    print("错误:无法将字符串转换为数字.字符串格式可能不正确.")
            else:
                print("错误:未找到 '结果' 相关的内容.")   
        except ValueError as e:
            print(f"Error parsing fundamental score: {e}")
            print(f"Raw result: {result}")
            return 0.0

        # 确保分数在-1到1之间
        for sent in fundamental_score_list:
            sent = max(-1.0, min(1.0, sent))

        # 缓存结果
        cache[stock_list] = fundamental_score_list,fundamental_reason
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing cache: {e}")

'''