import os
import sys
import json
from datetime import datetime
import akshare as ak
import requests
from bs4 import BeautifulSoup
from src.tools.openrouter_config import get_chat_completion, logger as api_logger
from src.prompts.agent_config import SENT_SYS_TEXT,SENT_REQ_TEXT
import time
import pandas as pd
import re

#问题在于捕获的信息和股价相关性过强,如股价上涨在其他信息中也能体现,应加入宏观新闻等.

def get_stock_news(symbol: str, max_news: int = 10) -> list:
    """获取并处理个股新闻

    Args:
        symbol (str): 股票代码,如 "300059"
        max_news (int, optional): 获取的新闻条数,默认为10条.最大支持100条.

    Returns:
        list: 新闻列表,每条新闻包含标题、内容、发布时间等信息
    """

    # 设置pandas显示选项,确保显示完整内容
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.width', None)

    # 限制最大新闻条数
    max_news = min(max_news, 100)

    # 获取当前日期
    today = datetime.now().strftime("%Y-%m-%d")

    # 构建新闻文件路径
    # project_root = os.path.dirname(os.path.dirname(
    #     os.path.dirname(os.path.abspath(__file__))))
    news_dir = os.path.join("src", "data", "stock_news")
    print(f"新闻保存目录: {news_dir}")

    # 确保目录存在
    try:
        os.makedirs(news_dir, exist_ok=True)
        print(f"成功创建或确认目录存在: {news_dir}")
    except Exception as e:
        print(f"创建目录失败: {e}")
        return []

    news_file = os.path.join(news_dir, f"{symbol}_news.json")
    print(f"新闻文件路径: {news_file}")

    # 检查是否需要更新新闻
    need_update = True
    if os.path.exists(news_file):
        try:
            with open(news_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("date") == today:
                    cached_news = data.get("news", [])
                    if len(cached_news) >= max_news:
                        print(f"使用缓存的新闻数据: {news_file}")
                        return cached_news[:max_news]
                    else:
                        print(
                            f"缓存的新闻数量({len(cached_news)})不足,需要获取更多新闻({max_news}条)")
        except Exception as e:
            print(f"读取缓存文件失败: {e}")

    print(f'开始获取{symbol}的新闻数据...')

    try:
        # 获取新闻列表
        news_df = ak.stock_news_em(symbol=symbol)
        if news_df is None or len(news_df) == 0:
            print(f"未获取到{symbol}的新闻数据")
            return []

        print(f"成功获取到{len(news_df)}条新闻")

        # 实际可获取的新闻数量
        available_news_count = len(news_df)
        if available_news_count < max_news:
            print(f"警告:实际可获取的新闻数量({available_news_count})少于请求的数量({max_news})")
            max_news = available_news_count

        # 获取指定条数的新闻(考虑到可能有些新闻内容为空,多获取50%)
        news_list = []
        for _, row in news_df.head(int(max_news * 1.5)).iterrows():
            try:
                # 获取新闻内容
                content = row["新闻内容"] if "新闻内容" in row and not pd.isna(
                    row["新闻内容"]) else ""
                if not content:
                    content = row["新闻标题"]

                # 只去除首尾空白字符
                content = content.strip()
                if len(content) < 10:  # 内容太短的跳过
                    continue

                # 获取关键词
                keyword = row["关键词"] if "关键词" in row and not pd.isna(
                    row["关键词"]) else ""

                # 添加新闻
                news_item = {
                    "title": row["新闻标题"].strip(),
                    "content": content,
                    "publish_time": row["发布时间"],
                    "source": row["文章来源"].strip(),
                    "url": row["新闻链接"].strip(),
                    "keyword": keyword.strip()
                }
                news_list.append(news_item)
                print(f"成功添加新闻: {news_item['title']}")

            except Exception as e:
                print(f"处理单条新闻时出错: {e}")
                continue

        # 按发布时间排序
        news_list.sort(key=lambda x: x["publish_time"], reverse=True)

        # 只保留指定条数的有效新闻
        news_list = news_list[:max_news]

        # 保存到文件
        try:
            save_data = {
                "date": today,
                "news": news_list
            }
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            print(f"成功保存{len(news_list)}条新闻到文件: {news_file}")
        except Exception as e:
            print(f"保存新闻数据到文件时出错: {e}")

        return news_list

    except Exception as e:
        print(f"获取新闻数据时出错: {e}")
        return []


def get_news_sentiment(symbol_list,news_dict: dict, num_of_news: int = 10) -> float:
    """分析新闻情感得分

    Args:
        news_dict (list): 新闻字典,包含多个股票的新闻列表
        symbol_list (str): 股票代码列表,如 "300059"
        num_of_news (int): 用于分析的新闻数量,默认为10条

    Returns:
        float: 情感得分,范围[-1, 1],-1最消极,1最积极
    """
    if not news_dict:
        return 0.0

    # # 获取项目根目录
    # project_root = os.path.dirname(os.path.dirname(
    #     os.path.dirname(os.path.abspath(__file__))))

    # 检查是否有缓存的情感分析结果
    cache_file = "src/data/sentiment_cache.json"
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)

    # 生成新闻内容的唯一标识
    news_key = "|".join([
        f"{symbol}|{news['title']}|{news['content'][:100]}|{news['publish_time']}"
        for symbol, news_list in news_dict.items() 
        for news in news_list[:num_of_news]  
    ])

    # 检查缓存
    if os.path.exists(cache_file):
        print("发现情感分析缓存文件")
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                if news_key in cache:
                    print("使用缓存的情感分析结果")
                    return cache[news_key]
                print("未找到匹配的情感分析缓存")
        except Exception as e:
            print(f"读取情感分析缓存出错: {e}")
            cache = {}
    else:
        print("未找到情感分析缓存文件,将创建新文件")
        cache = {}

    # 准备系统消息
    system_message = {
        "role": "system",
        "content": SENT_SYS_TEXT
    }

    # 准备新闻内容
    news_content = "\n\n".join([
        f"相关股票:{symbol}\n"
        f"标题:{news['title']}\n"
        f"来源:{news['source']}\n"
        f"时间:{news['publish_time']}\n"
        f"内容:{news['content']}"
        for symbol, news_list in news_dict.items()  # 遍历所有股票
        for news in news_list[:num_of_news]  # 使用指定数量的新闻
    ])

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{symbol_list}相关新闻:\n\n{news_content}\n\n
        {SENT_REQ_TEXT}"""
    }

    try:
        # 获取LLM分析结果
        result = get_chat_completion([system_message, user_message])
        if result is None:
            print("Error: PI error occurred, LLM returned None")
            return 0.0

        # 提取数字结果
        result_dict = json.loads(result)
        content_value = result_dict['choices'][0]['message']['content']

        return {"sentiment_reason": content_value}

    except Exception as e:
        print(f"Error analyzing news sentiment: {e}")
        return 0.0  # 出错时返回中性分数
