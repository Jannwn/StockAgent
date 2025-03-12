from langchain_core.messages import HumanMessage
from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.tools.news_crawler import get_stock_news, get_news_sentiment
from src.utils.logging_config import setup_logger
import json
from datetime import datetime, timedelta

# 设置日志记录
logger = setup_logger('sentiment_agent')


def sentiment_agent(state: AgentState):
    """Responsible for sentiment analysis"""
    show_workflow_status("Sentiment Analyst")
    show_reasoning = state["metadata"]["show_reasoning"]
    data = state["data"]
    symbol_list = data["ticker_list"]
    logger.info(f"正在分析股票集: {symbol_list}")
    # 从命令行参数获取新闻数量，默认为5条
    num_of_news = data.get("num_of_news", 10)

    news_dict = {} 
    for symbol in symbol_list:
        news_dict[symbol] = get_stock_news(symbol, max_news=num_of_news)  # 确保获取足够的新闻

    '''# 过滤7天内的新闻
    cutoff_date = datetime.now() - timedelta(days=7)
    recent_news = [news for news in news_list
                   if datetime.strptime(news['publish_time'], '%Y-%m-%d %H:%M:%S') > cutoff_date]
    '''
    
    sentiment_result = get_news_sentiment(symbol_list,news_dict, num_of_news=num_of_news)
    # 生成分析结果
    message_content = {
        "reasoning": f"""基于最近的新闻报导,关于列表中股票的情感分析结果如下{sentiment_result}"""
    }

    # 如果需要显示推理过程
    if show_reasoning:
        show_agent_reasoning(message_content, "Sentiment Analysis Agent")

    # 创建消息
    message = HumanMessage(
        content=json.dumps(message_content),
        name="sentiment_agent",
    )

    show_workflow_status("Sentiment Analyst", "completed")
    return {
        "messages": [message],
        "data": {
            **data,
            "sentiment_analysis": message_content
        }
    }
