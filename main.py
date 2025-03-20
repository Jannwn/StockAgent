import os
import sys
cur_path=os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path+"/..")

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pickle

from src.agents.state import AgentState
from src.agents.market_data import market_data_agent
from src.agents.fund_data import fund_data_agent
from src.agents.value_data import value_data_agent
from src.agents.news_data import news_data_agent
from src.agents.tech_data import tech_data_agent



def parse_ticker_list(ticker_str: str) -> list:
    # 处理输入字符串，确保它是一个有效的列表
    try:
        # 去掉外部的方括号并分割字符串
        if ticker_str.startswith('[') and ticker_str.endswith(']'):
            ticker_list = ticker_str.strip('[]').split(',')
            # 去掉每个元素的空格
            ticker_list = [ticker.strip() for ticker in ticker_list]
            return ticker_list
        else:
            raise ValueError("Input must be in the format [symbol1, symbol2, ...]")
    except Exception as e:
        raise ValueError(f"Invalid input format: {e}")

def formulate_data(ticker_list: List[str], 
                   start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, 
                   num_of_news: int = 10) -> Dict:
    
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)

    # 处理结束日期
    if end_date:
        end_date = min(datetime.strptime(end_date, '%Y-%m-%d'), yesterday)
    else:
        end_date = yesterday

    # 处理开始日期
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = end_date - timedelta(days=365)  # 默认获取一年的数据    
    
    start_date = start_date.strftime('%Y-%m-%d')
    end_date = end_date.strftime('%Y-%m-%d')
    return {
        "ticker_list": ticker_list,
        "start_date": start_date,
        "end_date": end_date,
        "num_of_news": num_of_news   
    }


def get_factors(data):
    market_result=market_data_agent("market_data_agent",data)
    data=market_result["data"]
    fund_result=fund_data_agent("fund_data_agent",data)
    val_result=value_data_agent("value_data_agent",data)
    news_result=news_data_agent("news_data_agent",data)
    tech_result=tech_data_agent("tech_data_agent",data)
    with open('data\\result\\market_result.pkl', 'wb') as pkl_file:
        pickle.dump(market_result, pkl_file)
    with open('data\\result\\fund_result.pkl', 'wb') as pkl_file:
        pickle.dump(fund_result, pkl_file)
    with open('data\\result\\val_result.pkl', 'wb') as pkl_file:
        pickle.dump(val_result, pkl_file)
    with open('data\\result\\news_result.pkl', 'wb') as pkl_file:
        pickle.dump(news_result, pkl_file)
    with open('data\\result\\ech_result.pkl', 'wb') as pkl_file:
        pickle.dump(tech_result, pkl_file)   


if __name__ == "__main__":
    sample_stock_list=["601899","603993","600362","601168"]
    data=formulate_data(sample_stock_list)
    get_factors(data)
    


    