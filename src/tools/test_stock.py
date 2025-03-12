import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
symbol='600734'
print(type(symbol))
start_date = datetime.now() - timedelta(days=365)
end_date = datetime.now()

df = ak.stock_zh_a_hist(
    symbol=symbol,
    period="daily",
    start_date=start_date.strftime("%Y%m%d"),
    end_date=end_date.strftime("%Y%m%d")
)
print (df)