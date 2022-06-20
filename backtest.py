# below are codes for backtesting trading strategy with historical price data

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import copy
import time
plt.style.use("seaborn")


# below are functions for computing performance metric====================================================
def ATR(DF,n):
    "function to calculate True Range and Average True Range"
    df = DF.copy()
    df['H-L']=abs(df['High']-df['Low'])
    df['H-PC']=abs(df['High']-df['Close'].shift(1))
    df['L-PC']=abs(df['Low']-df['Close'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1,skipna=False)
    df['ATR'] = df['TR'].rolling(n).mean()
    df2 = df.drop(['H-L','H-PC','L-PC'],axis=1)
    return df2['ATR']

def multiple(DF):
    "function to calculate multiple returns"
    df = DF.copy()
    mult=(1 + df["ret"]).cumprod().iloc[-1]
    return mult

def CAGR(DF):
    "function to calculate the Cumulative Annual Growth Rate of a trading strategy"
    df = DF.copy()
    df["cum_return"] = (1 + df["ret"]).cumprod()
    n = len(df)/(365.25*96)
    CAGR = (df["cum_return"].tolist()[-1])**(1/n) - 1
    return CAGR

def volatility(DF):
    "function to calculate annualized volatility of a trading strategy"
    df = DF.copy()
    vol = df["ret"].std() * np.sqrt(365.25*96)
    return vol

def sharpe(DF,rf):
    "function to calculate sharpe ratio ; rf is the risk free rate"
    df = DF.copy()
    sr = (CAGR(df) - rf)/volatility(df)
    return sr
    
def max_dd(DF):
    "function to calculate max drawdown"
    df = DF.copy()
    df["cum_return"] = (1 + df["ret"]).cumprod()
    df["cum_roll_max"] = df["cum_return"].cummax()
    df["drawdown"] = df["cum_roll_max"] - df["cum_return"]
    df["drawdown_pct"] = df["drawdown"]/df["cum_roll_max"]
    max_dd = df["drawdown_pct"].max()
    return max_dd

# load historical data===========================================================

ticker = "BTCUSDT" 
tc = 1-0.00075
        
ohlc_intraday = pd.read_csv("BTCUSDT15m.csv", parse_dates = ["Date"], index_col = "Date")
# select time section
# ohlc_intraday = data.loc['2021-06-04':]
ohlc_dict = ohlc_intraday.copy()



# computing ATR and rolling max price============================================
print("calculating ATR and rolling max price for ",ticker)

def prepData(ohlc_dict,rollx):
    ohlc_dict["ATR"] = ATR(ohlc_dict,rollx)
    ohlc_dict["roll_max_cp"] = ohlc_dict["High"].rolling(rollx).max()
    ohlc_dict["roll_min_cp"] = ohlc_dict["Low"].rolling(rollx).min()
    ohlc_dict["roll_max_vol"] = ohlc_dict["Volume"].rolling(rollx).max()
    ohlc_dict.dropna(inplace=True)

prepData(ohlc_dict,9)


# computig trading signals and computing returns========================================

print("calculating returns for ",ticker)

def backTest(ohlc_dict,volx):
    trade=0 #for trading counts
    tickers_signal= ""
    tickers_ret= [0]
    for i in range(1,len(ohlc_dict)):
        if tickers_signal == "":
            tickers_ret.append(0)
            if ohlc_dict["High"][i]>=ohlc_dict["roll_max_cp"][i] and \
               ohlc_dict["Volume"][i]>volx*ohlc_dict["roll_max_vol"][i-1]:
                tickers_signal = "Buy"
                price_base=ohlc_dict["Close"][i]
                trade+=1
            elif ohlc_dict["Low"][i]<=ohlc_dict["roll_min_cp"][i] and \
               ohlc_dict["Volume"][i]>volx*ohlc_dict["roll_max_vol"][i-1]:
                tickers_signal = "Sell"
                price_base=ohlc_dict["Close"][i]
                trade+=1

        elif tickers_signal == "Buy":
            if ohlc_dict["Low"][i]<(ohlc_dict["Close"][i-1] - ohlc_dict["ATR"][i-1]):
                tickers_signal = ""
                tickers_ret.append(((ohlc_dict["Close"][i-1] - ohlc_dict["ATR"][i-1])/ohlc_dict["Close"][i-1])-1)
                trade+=1
            elif ohlc_dict["Low"][i]<=ohlc_dict["roll_min_cp"][i] and \
               ohlc_dict["Volume"][i]>volx*ohlc_dict["roll_max_vol"][i-1]:
                tickers_signal = "Sell"
                tickers_ret.append((ohlc_dict["Close"][i]/ohlc_dict["Close"][i-1])-1)
                trade+=1
            else:
                tickers_ret.append((ohlc_dict["Close"][i]/ohlc_dict["Close"][i-1])-1)

        elif tickers_signal == "Sell":
            if ohlc_dict["High"][i]>(ohlc_dict["Close"][i-1] + ohlc_dict["ATR"][i-1]):
                tickers_signal = ""
                tickers_ret.append((ohlc_dict["Close"][i-1]/(ohlc_dict["Close"][i-1] + ohlc_dict["ATR"][i-1]))-1)
                trade+=1
            elif ohlc_dict["High"][i]>=ohlc_dict["roll_max_cp"][i] and \
               ohlc_dict["Volume"][i]>volx*ohlc_dict["roll_max_vol"][i-1]:
                tickers_signal = "Buy"
                tickers_ret.append((ohlc_dict["Close"][i-1]/ohlc_dict["Close"][i])-1)
                trade+=1
            else:
                tickers_ret.append((ohlc_dict["Close"][i-1]/ohlc_dict["Close"][i])-1)
                
    # print("trade count ",trade)
    # print("trade frequent",trade/len(ohlc_dict))
    ohlc_dict["ret"] = np.array(tickers_ret)
    return trade

trade = backTest(ohlc_dict,1.9)


# computing strategy's performance=======================================================
strategy_df = pd.DataFrame()
strategy_df["ret"] = ohlc_dict["ret"].mul(tc)
strategy_df["HODLret"] = ohlc_dict["Close"].div(ohlc_dict["Close"].shift(1))
strategy_df["cum_return"] = (1 + strategy_df["ret"]).cumprod()
#strategy_df["HODL_cum_return"] = (strategy_df["HODLret"]).cumprod()
#strategy_df["default_cum_return"] = destrategy_df["de_cum_return"]

print("trade ", trade)
print("multiple ",multiple(strategy_df))
print("CAGR ",CAGR(strategy_df))
print("sharpe ",sharpe(strategy_df,0))
print("max_dd ",max_dd(strategy_df))


# vizualizing strategy returns=======================================================
(1+strategy_df["ret"]).cumprod().plot()

#title = "Optimized and default scalping strategies outperform HODL"
#fig=strategy_df[["HODL_cum_return", "cum_return", "default_cum_return"]].plot(figsize=(12, 8),fontsize=14)
#fig=strategy_df[["HODL_cum_return", "cum_return"]].plot(figsize=(12, 8),fontsize=14)
#fig.legend(fontsize=16)
#fig.set_title(title,fontsize=20)
#fig.set_xlabel('Date.', fontsize=16)
#fig.set_ylabel('Cumulative Return', fontsize=16)
#strategy_df["HODLcum_return"]
#strategy_df["cum_return"]
#plt.savefig('HODL_vs_DeScalpingStrategy_vs_opt.png')




# below are codes for calculating all combinations of parameters' performance============================
# computing combinations
rollx = range(5,21,1)
volx = range(13,21,1)

combinations = [list(tup) for tup in product(rollx, volx)]
for comb in combinations:
    comb[1]=round(comb[1]*0.1,2)

# computing performances of all combinations
trades=[]
multiples = []
CAGRs = []
sharpes= []
max_dds = []
ohlc_intraday = pd.read_csv("BTCUSDT15m.csv", parse_dates = ["Date"], index_col = "Date")
for comb in combinations:
    ohlc_dict=ohlc_intraday.copy()
    prepData(ohlc_dict,comb[0])
    trade=backTest(ohlc_dict,comb[1])
    strategy_df = pd.DataFrame()
    strategy_df["ret"] = ohlc_dict["ret"].mul(tc)
    trades.append(trade)
    multiples.append(multiple(strategy_df))
    CAGRs.append(CAGR(strategy_df))
    sharpes.append(sharpe(strategy_df,0))
    max_dds.append(max_dd(strategy_df))

# putting all combinations' performance into a dataframe
results_overview =  pd.DataFrame(data = np.array(combinations), columns = ["rolling_days", "breakout_percent"])
results_overview["trade"] = trades
results_overview["multiple"] = multiples
results_overview["CAGR"] = CAGRs
results_overview["sharpe"] = sharpes
results_overview["max_dd"] = max_dds

# check out the best performances in each metric, for example
#results_overview.nlargest(5, "multiple")
#results_overview.nlargest(5, "CAGR")









