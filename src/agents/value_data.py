from langchain_core.messages import HumanMessage
from src.agents.state import AgentState
import json
from src.tools.valuation_analyzer import valuation_analyse
from src.prompts.signal_config import VALUE_SIGNAL_TEXT

def value_data_agent(message,data):
    """Responsible for valuation analysis"""

    end_date = data["end_date"]

    results={}
    for ticker in data["ticker_list"]:
        metrics = data["financial_metrics"][ticker][0]
        current_financial_line_item = data["financial_line_items"][ticker][0]
        previous_financial_line_item = data["financial_line_items"][ticker][1]
        market_cap = data["market_cap"][ticker]
        results[ticker]=valuation_analyse(metrics,current_financial_line_item,previous_financial_line_item,market_cap)
    
    #message_content = {"results": results}
    #message_text=get_value_analyze(end_date,results,VALUE_SIGNAL_TEXT)
    #message = HumanMessage(
    #    content=json.dumps(message_text),
    #    name="valuation_agent",)


    return {
        "messages": message, # If need gpt analyze, introduce the above and below code.
        #"data": {
            # **data,
            #"valuation_analysis": results}

        "results": results
    }