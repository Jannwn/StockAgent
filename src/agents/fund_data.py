from src.tools.fundamental_analyzer import fundamental_analyse

def fund_data_agent(message,data):
    end_date = data["end_date"]

    results={}
    for ticker in data["ticker_list"]:
        metrics = data["financial_metrics"][ticker][0]
        results[ticker]=fundamental_analyse(metrics)
    return {"message":message,"results":results}