from src.tools.news_crawler import get_stock_news

def news_data_agent(message,data)->dict:
    symbol_list = data["ticker_list"]
    num_of_news = data.get("num_of_news", 20)

    news_dict = {} 
    for symbol in symbol_list:
        news_dict[symbol] = get_stock_news(symbol, max_news=num_of_news)
    return {"message":message,
            "news_dict":news_dict}