from langchain_core.messages import HumanMessage
from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.tools.overall_analyzer import get_bullish_analyze
import json
import ast


def researcher_bull_agent(state: AgentState):
    """Analyzes signals from a bullish perspective and generates optimistic investment thesis."""
    show_workflow_status("Bullish Researcher")
    show_reasoning = state["metadata"]["show_reasoning"]
    end_date = state["data"]["end_date"]
    stock_list = state["data"]["ticker_list"]

    # Fetch messages from analysts
    technical_message = next(
        msg for msg in state["messages"] if msg.name == "technical_analyst_agent")
    fundamentals_message = next(
        msg for msg in state["messages"] if msg.name == "fundamentals_agent")
    sentiment_message = next(
        msg for msg in state["messages"] if msg.name == "sentiment_agent")
    valuation_message = next(
        msg for msg in state["messages"] if msg.name == "valuation_agent")
    
    reasoning_dict = {
    "technical": json.loads(technical_message.content), 
    "fundamentals": json.loads(fundamentals_message.content),
    "sentiment": json.loads(sentiment_message.content),
    "valuation": json.loads(valuation_message.content),
    }


    reasoning=get_bullish_analyze(end_date,stock_list,reasoning_dict)

    message_content = {
        "perspective": "bullish",
        "reasoning": "Bullish thesis based on comprehensive analysis of technical, "
        "fundamental, sentiment, and valuation factors, we have the following reasoning: \n\n" + reasoning,
    }

    message = HumanMessage(
        content=json.dumps(message_content),
        name="researcher_bull_agent",
    )

    if show_reasoning:
        show_agent_reasoning(message_content, "Bullish Researcher")

    show_workflow_status("Bullish Researcher", "completed")
    return {
        "messages": state["messages"] + [message],
        "data": state["data"],
    }
