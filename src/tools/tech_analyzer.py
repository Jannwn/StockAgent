import os
import json
from typing import Dict
from datetime import datetime
from src.tools.openrouter_config import get_chat_completion, logger as api_logger
from src.tools.tech_calculator import calculate_macd, calculate_rsi, calculate_bollinger_bands, calculate_obv
from src.tools.tech_calculator import calculate_trend_signals, calculate_mean_reversion_signals, calculate_momentum_signals
from src.tools.tech_calculator import calculate_volatility_signals, calculate_stat_arb_signals, weighted_signal_combination,normalize_pandas
from src.tools.tech_calculator import cal_signals
from src.tools.api import prices_to_df
from src.prompts.agent_config import TECH_SYS_TEXT,TECH_REQ_TEXT
from src.prompts.signal_config import TECH_SIGNAL_TEXT
import time
import pandas as pd
import re


def tech_analyse(prices: Dict) -> Dict:
    """
    Calculate trading signals based on price data.

    Args:
        prices (Dict): A dictionary containing price data.

    Returns:
        Dict: A dictionary containing the calculated signals and confidence levels.
    """
    prices_df = prices_to_df(prices)
    '''
    Indicators:
    MACD: Moving Average Convergence Divergence
    RSI: Relative Strength Index
    Bollinger Bands (Upper and Lower Bands)
    OBV: On-Balance Volume
    '''

    macd_line, signal_line = calculate_macd(prices_df)
    rsi = calculate_rsi(prices_df)
    upper_band, lower_band = calculate_bollinger_bands(prices_df)
    obv = calculate_obv(prices_df)
    obv_slope = obv.diff().iloc[-5:].mean()
    price_drop = (prices_df['close'].iloc[-1] -
                  prices_df['close'].iloc[-5]) / prices_df['close'].iloc[-5]
    
    signals = cal_signals(prices_df,macd_line, signal_line, rsi, upper_band, lower_band, obv,obv_slope,price_drop)
    print(f'计算signals:{signals}')
    # Add reasoning collection
    reasoning = {
        "MACD": {
            'MACD Line': macd_line,
            "signal": signals[0],
            "details": f"MACD Line crossed {'above' if signals[0] == 'bullish' else 'below' if signals[0] == 'bearish' else 'neither above nor below'} Signal Line"
        },
        "RSI": {
            'RSI': rsi.iloc[-1],
            "signal": signals[1],
            "details": f"RSI is {rsi.iloc[-1]:.2f} ({'oversold' if signals[1] == 'bullish' else 'overbought' if signals[1] == 'bearish' else 'neutral'})"
        },
        "Bollinger": {
            #"Upper Band": upper_band,
            #"Lower Band": lower_band,
            "signal": signals[2],
            "details": f"Price is {'below lower band' if signals[2] == 'bullish' else 'above upper band' if signals[2] == 'bearish' else 'within bands'}"
        },
        "OBV": {
            #"OBV": obv,
            "OBV_slope": obv_slope,
            "signal": signals[3],
            "details": f"OBV slope is {obv_slope:.2f} ({signals[3]})"
        }
    }

    '''
    # Determine overall signal
    bullish_signals = signals.count('bullish')
    bearish_signals = signals.count('bearish')

    if bullish_signals > bearish_signals:
        overall_signal = 'bullish'
    elif bearish_signals > bullish_signals:
        overall_signal = 'bearish'
    else:
        overall_signal = 'neutral'
    
    # Calculate confidence level based on the proportion of indicators agreeing
    total_signals = len(signals)
    confidence = max(bullish_signals, bearish_signals) / total_signals
    '''
    # Generate the message content
    message_content = {
        "reasoning": {
            "MACD": reasoning["MACD"],
            "RSI": reasoning["RSI"],
            "Bollinger": reasoning["Bollinger"],
            "OBV": reasoning["OBV"],
            "signal_meaning":TECH_SIGNAL_TEXT
        }
    }

    trend_signals = calculate_trend_signals(prices_df)
    mean_reversion_signals = calculate_mean_reversion_signals(prices_df)
    momentum_signals = calculate_momentum_signals(prices_df)
    volatility_signals = calculate_volatility_signals(prices_df)
    stat_arb_signals = calculate_stat_arb_signals(prices_df)
    strategy_weights = {
        'trend': 0.30,
        'mean_reversion': 0.25,  # Increased weight for mean reversion
        'momentum': 0.25,
        'volatility': 0.15,
        'stat_arb': 0.05
    }

    combined_signal = weighted_signal_combination({
        'trend': trend_signals,
        'mean_reversion': mean_reversion_signals,
        'momentum': momentum_signals,
        'volatility': volatility_signals,
        'stat_arb': stat_arb_signals
    }, strategy_weights)

    analysis_report = {
        "technical_analyze_message": message_content,
        "signal": combined_signal['signal'],
        "confidence": f"{round(combined_signal['confidence'] * 100)}%",
        "strategy_signals": {
            "trend_following": {
                "signal": trend_signals['signal'],
                "confidence": f"{round(trend_signals['confidence'] * 100)}%",
                "metrics": normalize_pandas(trend_signals['metrics'])
            },

            "mean_reversion": {
                "signal": mean_reversion_signals['signal'],
                "confidence": f"{round(mean_reversion_signals['confidence'] * 100)}%",
                "metrics": normalize_pandas(mean_reversion_signals['metrics'])
            },
            "momentum": {
                "signal": momentum_signals['signal'],
                "confidence": f"{round(momentum_signals['confidence'] * 100)}%",
                "metrics": normalize_pandas(momentum_signals['metrics'])
            },
            "volatility": {
                "signal": volatility_signals['signal'],
                "confidence": f"{round(volatility_signals['confidence'] * 100)}%",
                "metrics": normalize_pandas(volatility_signals['metrics'])
            },
            "statistical_arbitrage": {
                "signal": stat_arb_signals['signal'],
                "confidence": f"{round(stat_arb_signals['confidence'] * 100)}%",
                "metrics": normalize_pandas(stat_arb_signals['metrics'])
            }
        }
    }
    
    return analysis_report

def tech_analyze_result(data)->Dict:
    prices_dict = data["prices"]
    end_date = data["end_date"]
    report_dict={}
    # Create the technical analyst message
    for ticker,prices in prices_dict.items():
        analysis_report = tech_analyse(prices)
        report_dict[ticker]=analysis_report
    return report_dict

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
        "content": TECH_SYS_TEXT
    }

    user_message = {
        "role": "user", #prompt
        "content": f"""
        分析以下A股上市公司{stock_list}相关新闻,对比并计算每只的股票的技术指标:\n\n{stock_tech_dict}\n\n
        {TECH_REQ_TEXT}"""
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