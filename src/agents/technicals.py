from typing import Dict

from langchain_core.messages import HumanMessage

from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.tools.tech_calculator import calculate_macd, calculate_rsi, calculate_bollinger_bands, calculate_obv
from src.tools.tech_calculator import calculate_trend_signals, calculate_mean_reversion_signals, calculate_momentum_signals
from src.tools.tech_calculator import calculate_volatility_signals, calculate_stat_arb_signals, weighted_signal_combination,normalize_pandas
from src.tools.tech_calculator import cal_signals
from src.tools.tech_analyzer import get_tech_analyze
from src.prompts.signal_config import TECH_SIGNAL_TEXT,TECH_STRATEGY_TEXT

from src.tools.api import prices_to_df
import json

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
    end_date = data["end_date"]
    report_dict={}
    # Create the technical analyst message
    for ticker,prices in prices_dict.items():
        analysis_report = calculate_signals(prices)
        report_dict[ticker]=analysis_report
    message_text=get_tech_analyze(end_date,analysis_report,TECH_SIGNAL_TEXT,TECH_STRATEGY_TEXT)
    message = HumanMessage(
        content=json.dumps(message_text),
        name="technical_analyst_agent",
    )

    if show_reasoning:
        show_agent_reasoning(
            analysis_report, "Technical Analyst")

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
