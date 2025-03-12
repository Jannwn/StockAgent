from langchain_core.messages import HumanMessage
from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.tools.overall_analyzer import get_debate_analyze
import json
import ast


def debate_room_agent(state: AgentState):
    """Facilitates debate between bull and bear researchers to reach a balanced conclusion."""
    show_workflow_status("Debate Room")
    show_reasoning = state["metadata"]["show_reasoning"]
    end_date = state["data"]["end_date"]
    stock_list = state["data"]["ticker_list"]

    # Fetch messages from researchers
    bull_message = next(
        msg for msg in state["messages"] if msg.name == "researcher_bull_agent")
    bear_message = next(
        msg for msg in state["messages"] if msg.name == "researcher_bear_agent")

    try:
        bull_thesis = json.loads(bull_message.content)
        bear_thesis = json.loads(bear_message.content)
    except Exception as e:
        bull_thesis = ast.literal_eval(bull_message.content)
        bear_thesis = ast.literal_eval(bear_message.content)

    message_text=get_debate_analyze(end_date,stock_list,bull_thesis,bear_thesis)

    message_content = {
        "reasoning": message_text
    }

    message = HumanMessage(
        content=json.dumps(message_content),
        name="debate_room_agent",
    )

    if show_reasoning:
        show_agent_reasoning(message_content, "Debate Room")

    show_workflow_status("Debate Room", "completed")
    return {
        "messages": state["messages"] + [message],
        "data": {
            **state["data"],
            "debate_analysis": message_content
        }
    }
