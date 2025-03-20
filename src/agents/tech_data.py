from src.tools.tech_analyzer import tech_analyse

def tech_data_agent(message,data)->dict:
    prices_dict = data["prices"]
    end_date = data["end_date"]
    report_dict={}
    # Create the technical analyst message
    for ticker,prices in prices_dict.items():
        analysis_report = tech_analyse(prices)
        report_dict[ticker]=analysis_report
    #message_text=get_tech_analyze(end_date,analysis_report,TECH_SIGNAL_TEXT,
    # TECH_STRATEGY_TEXT)
    return {"message":message,
            "result":report_dict}