from typing import Dict

from langchain_core.messages import HumanMessage

from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.tools.tech_calculator import calculate_macd, calculate_rsi, calculate_bollinger_bands, calculate_obv
from src.tools.tech_calculator import calculate_trend_signals, calculate_mean_reversion_signals, calculate_momentum_signals
from src.tools.tech_calculator import calculate_volatility_signals, calculate_stat_arb_signals, weighted_signal_combination,normalize_pandas
import json

from src.tools.api import prices_to_df

## signal explaination

TEXT_SIGNAL=""" 
我们认为MACD线与信号线的交叉是一个重要的信号,可以用于判断买入或卖出的时机.
当MACD线从下方穿过信号线时,我们认为这是一个买入信号,表示股价可能会上涨.
当MACD线从上方穿过信号线时,我们认为这是一个卖出信号,表示股价可能会下跌.
同理,我们计算RSI的数值,当RSI小于30时,我们认为股价被低估,是一个买入信号.
当RSI大于70时,我们认为股价被高估,是一个卖出信号.
对于布林带指标,我们认为股价突破上轨线是一个卖出信号,突破下轨线是一个买入信号.
当股价在布林带之间时,我们认为是一个中性信号.
最后是OBV指标,我们计算OBV的斜率,当斜率为正时,我们认为是一个买入信号.
当斜率为负时,我们认为是一个卖出信号.
至于价格下跌信号,我们设置了两个阈值,当价格下跌超过5%且RSI小于40时,我们认为是一个强烈的买入信号.
当价格下跌超过3%且RSI小于45时,我们认为是一个中等的买入信号.
将这些信号综合起来,得出最终的交易信号."""

TEXT_STRATEGY="""
1. calculate_trend_signals策略是一种 多时间框架趋势跟踪策略,通过结合 8日、21日和55日 EMA 判断短期和中期趋势方向,并利用 14日 ADX 评估趋势强度,生成高置信度的交易信号.策略的核心判断标准如下:
看涨信号:EMA_8 > EMA_21 且 EMA_21 > EMA_55,同时 ADX 值较高,表明市场处于强势上涨趋势.
看跌信号:EMA_8 < EMA_21 且 EMA_21 < EMA_55,同时 ADX 值较高,表明市场处于强势下跌趋势.
中性信号:短期和中期趋势不一致,或 ADX 值较低,表明市场处于震荡或无趋势状态.策略通过多时间框架和趋势强度的综合分析,有效捕捉市场趋势并动态调整信号置信度

2. 均值回归策略(Mean Reversion Strategy)通过 Z-Score 和 布林带(Bollinger Bands) 识别价格偏离均值的极端情况,并结合 RSI 指标确认超买超卖状态,生成均值回归信号.策略的核心判断标准如下:

看涨信号:Z-Score 低于 -2 且价格接近布林带下轨(price_vs_bb < 0.2),表明价格处于超卖状态,可能反弹.
看跌信号:Z-Score 高于 2 且价格接近布林带上轨(price_vs_bb > 0.8),表明价格处于超买状态,可能回调.
中性信号:价格未达到极端水平,市场处于震荡状态.策略通过 Z-Score 和布林带的结合,有效捕捉价格回归均值的交易机会.
适用于震荡市场,捕捉价格回归均值的交易机会.

3. 动量策略(Momentum Strategy)通过 多时间框架动量(1个月、3个月、6个月)和 成交量动量 确认市场趋势的持续性,生成动量信号.策略的核心判断标准如下:

看涨信号:动量评分(momentum_score)大于 0.05 且成交量动量大于 1,表明市场处于强势上涨趋势.
看跌信号:动量评分小于 -0.05 且成交量动量大于 1,表明市场处于强势下跌趋势.
中性信号:动量评分和成交量动量未达到阈值,市场趋势不明确.策略通过多时间框架动量和成交量的结合,有效捕捉趋势延续的交易机会.
适用于趋势市场,捕捉趋势延续的交易机会.两者结合可适应不同的市场环境,提升策略的稳健性

4. 统计套利策略(Statistical Arbitrage Strategy)通过 Hurst 指数、偏度(Skewness) 和 峰度(Kurtosis) 分析价格分布特征,生成统计套利信号.策略的核心判断标准如下:

看涨信号:Hurst 指数低于 0.4(表明价格具有均值回归特性)且偏度大于 1(价格分布右偏),表明市场可能反弹.
看跌信号:Hurst 指数低于 0.4 且偏度小于 -1(价格分布左偏),表明市场可能回调.
中性信号:Hurst 指数高于 0.4 或偏度未达到阈值,市场无明显统计套利机会.策略通过价格分布特征,捕捉均值回归的交易机会.

"""

##### Technical Analyst #####
def technical_analyst_agent(state: AgentState):
    """
    Sophisticated technical analysis system that combines multiple trading strategies:
    1. Trend Following
    2. Mean Reversion
    3. Momentum
    4. Volatility Analysis
    5. Statistical Arbitrage Signals

    "data": {
    "ticker_list": ticker_list,
    "portfolio": portfolio,
    "start_date": start_date,
    "end_date": end_date,
    "num_of_news": num_of_news,}
    "metadata": {
    "show_reasoning": show_reasoning,}

    """
    show_workflow_status("Technical Analyst")
    show_reasoning = state["metadata"]["show_reasoning"]
    
    data = state["data"]
    prices_dict = data["prices"]
    report_dict={}
    # Create the technical analyst message
    for ticker,prices in prices_dict.items():
        analysis_report = calculate_signals(prices)
        report_dict[ticker]=analysis_report
    message = HumanMessage(
        content=json.dumps(analysis_report,TEXT_SIGNAL),
        name="technical_analyst_agent",
    )

    if show_reasoning:
        show_agent_reasoning(analysis_report, "Technical Analyst")

    show_workflow_status("Technical Analyst", "completed")
    return {
        "messages": [message],
        "data": data,
    }


def calculate_signals(prices: Dict) -> Dict:
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
    
    signals = signals(prices_df,macd_line, signal_line, rsi, upper_band, lower_band, obv,obv_slope,price_drop)

    # Add reasoning collection
    reasoning = {
        "MACD": {
            'MACD Line': macd_line,
            "signal": signals[0],
            "details": f"MACD Line crossed {'above' if signals[0] == 'bullish' else 'below' if signals[0] == 'bearish' else 'neither above nor below'} Signal Line"
        },
        "RSI": {
            'RSI': rsi,
            "signal": signals[1],
            "details": f"RSI is {rsi.iloc[-1]:.2f} ({'oversold' if signals[1] == 'bullish' else 'overbought' if signals[1] == 'bearish' else 'neutral'})"
        },
        "Bollinger": {
            "Upper Band": upper_band,
            "Lower Band": lower_band,
            "signal": signals[2],
            "details": f"Price is {'below lower band' if signals[2] == 'bullish' else 'above upper band' if signals[2] == 'bearish' else 'within bands'}"
        },
        "OBV": {
            "OBV": obv,
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
            "signal_meaning":TEXT_SIGNAL
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
