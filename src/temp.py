'''
def get_historical_data(symbol: str) -> pd.DataFrame:
    """Get historical market data for a given stock symbol.
    If we can't get the full year of data, use whatever is available."""
    # Calculate date range
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)
    end_date = yesterday  # Use yesterday as end date
    target_start_date = yesterday - \
        timedelta(days=365)  # Target: 1 year of data

    print(f"\n正在获取 {symbol} 的历史行情数据...")
    print(f"目标开始日期：{target_start_date.strftime('%Y-%m-%d')}")
    print(f"结束日期：{end_date.strftime('%Y-%m-%d')}")

    try:
        # Get historical data
        df = ak.stock_zh_a_hist(symbol=symbol,
                                period="daily",
                                start_date=target_start_date.strftime(
                                    "%Y%m%d"),
                                end_date=end_date.strftime("%Y%m%d"),
                                adjust="qfq")

        actual_days = len(df)
        target_days = 365  # Target: 1 year of data

        if actual_days < target_days:
            print(f"提示：实际获取到的数据天数({actual_days}天)少于目标天数({target_days}天)")
            print(f"将使用可获取到的所有数据进行分析")

        print(f"成功获取历史行情数据，共 {actual_days} 条记录\n")
        return df

    except Exception as e:
        print(f"获取历史数据时发生错误: {str(e)}")
        print("将尝试获取最近可用的数据...")

        # Try to get whatever data is available
        try:
            df = ak.stock_zh_a_hist(symbol=symbol,
                                    period="daily",
                                    adjust="qfq")
            print(f"成功获取历史行情数据，共 {len(df)} 条记录\n")
            return df
        except Exception as e:
            print(f"获取历史数据失败: {str(e)}")
            return pd.DataFrame()
'''