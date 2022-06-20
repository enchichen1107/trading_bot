import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import psycopg2
from binance.client import Client


# below are codes handling data==========================================================

@st.experimental_singleton(suppress_st_warning=True)
def init_connection():
    "initialize db connection"
    return psycopg2.connect(**st.secrets["postgres"])


@st.experimental_memo(ttl=600)
def run_query(query):
    "execute query"
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


@st.experimental_memo
def get_most_recent(symbol, interval, end_date, start_date):
    "function to load in price data from binance to calculate HODL returns"
    now = str(end_date)
    past = str(start_date)
    
    client = Client(tld = "com", testnet = False)
    bars = client.get_historical_klines(symbol = symbol, interval = interval,
                                        start_str = past, end_str = now, limit = 1000)
    df = pd.DataFrame(bars)
    df["Date"] = pd.to_datetime(df.iloc[:,0], unit = "ms")
    df.columns = ["Open Time", "Open", "High", "Low", "Close", "Volume",
                  "Close Time", "Quote Asset Volume", "Number of Trades",
                  "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore", "Date"]
    df = df[["Date", "Close"]].copy()
    df.set_index("Date", inplace = True)
    for column in df.columns:
        df[column] = pd.to_numeric(df[column], errors = "coerce")
    df["returns"] = (df.Close / df.Close.shift(1)).mul(1-0.00075)
    df["cum_return"] = df["returns"].cumprod()
    
    return df



@st.experimental_memo
def load_trade_data(data):
    "function to load in trading data"
    df = pd.DataFrame(data)
    if data:
        df.columns = ["transaction_time","symbol","side","price"]
        df["transaction_time"] = pd.to_datetime(df["transaction_time"])
        df["price"] = pd.to_numeric(df["price"], errors = "coerce")
        df["returns"] = (df.price / df.price.shift(1)).mul(1-0.00075)
        df["cum_return"] = df["returns"].cumprod()
        df["sign"] = np.where(df['side']=='BUY', -1, 1) 
        df["profit"] = df["price"]*df["sign"]
    return df


def get_date(DF):
    df = DF.copy()
    dates = {'start_date':"", 'end_date':""}
    if df.shape[0]>0:
        dates["end_date"] = df["transaction_time"].iloc[-1].date()
        dates["start_date"] = df["transaction_time"].iloc[0].date()
    return dates

def get_metric(DF):
    df = DF.copy()
    if len(df.index)%2 == 0:
        met = {"value":df["cum_return"].iloc[-1],\
               "delta":df["cum_return"].iloc[-1]/df["cum_return"].iloc[1]}
    else:
        met = {"value":df["cum_return"].iloc[-2],\
               "delta":df["cum_return"].iloc[-2]/df["cum_return"].iloc[1]}
    return met


# below are codes handling app layout==========================================================
# streamlit layout
st.title('Bot Performance Quick View')
st.markdown("***")


# load in trading data
placeholder = st.empty()
placeholder.text("Loading .........")
conn = init_connection()
bot1_record = run_query("SELECT * from trade_record1;")
df1 = load_trade_data(bot1_record)
bot2_record = run_query("SELECT * from trade_record2;")
df2 = load_trade_data(bot2_record)
placeholder.empty()



# filter data by sidebar
df1_dates = get_date(df1)
df2_dates = get_date(df2)
filtered_df = {}
start_date = ""
end_date = ""

if (df1_dates["end_date"]!="")and(df2_dates["end_date"]!=""):
    
    if df1_dates["end_date"]<df2_dates["end_date"]:
        end_date = df1_dates["end_date"]
    else:
        end_date = df2_dates["end_date"]
    if df1_dates["start_date"]<df2_dates["start_date"]:
        start_date = df1_dates["start_date"]
    else:
        start_date = df2_dates["start_date"]
        
    if end_date > start_date:
        date_range = st.sidebar.slider("👇 Pick a date range > 1 day", min_value=start_date, value=(start_date, end_date), max_value=end_date, format="MM/DD")

        if  date_range[0] == date_range[1]:
            st.sidebar.error('Error: End date must be greater than start date.')
            st.subheader('👈Please pick a date range > 1 day')

        else:
            st.sidebar.warning('Start date: `%s`\n\nEnd date:`%s`' % (date_range[0],date_range[1]))

            filtered_df1 = df1.loc[(df1["transaction_time"].dt.date>=date_range[0]) & (df1["transaction_time"].dt.date<=date_range[1])]
            filtered_df1["bot"] = np.where(filtered_df1['symbol']!='', 'bot1', '')
            filtered_df2 = df2.loc[(df2["transaction_time"].dt.date>=date_range[0]) & (df2["transaction_time"].dt.date<=date_range[1])]
            filtered_df2["bot"] = np.where(filtered_df2['symbol']!='', 'bot2', '')
            filtered_df = pd.concat([filtered_df1,filtered_df2])

            # calculate return metric

            bdf = get_most_recent(symbol = "BTCUSDT", interval = "15m", end_date = date_range[1] , start_date = date_range[0] )
            HODL = {"value":bdf["cum_return"].iloc[-1],"delta":bdf["cum_return"].iloc[-1]/bdf["cum_return"].iloc[1]}

            bot1 = get_metric(filtered_df1)
            bot2 = get_metric(filtered_df2)

            winner = 'BOT1-scalping' if bot1["value"] >= bot2["value"] else 'BOT2-breakout'
            st.subheader('🏆 The latest winner is {}'.format(winner))
            st.text('base on the cumulative returns metric')
            st.text(' ')

            col1, col2, col3 = st.columns(3)
            col1.metric("Bot1-scalping", str(round(bot1["value"]*100,2))+'%', round(bot1["delta"],3))
            col2.metric("Bot2-breakout", str(round(bot2["value"]*100,2))+'%', round(bot2["delta"],3))
            col3.metric("HODL", str(round((HODL["value"]-1)*100,2))+'%', round((HODL["delta"]-1)*100,3))
            
    else:
        st.subheader('🏆 The latest winner is...')
        st.subheader('🙇 SORRY💦💦💦 we need to wait until having at least 2 day\'s trading data...')
            
else:
    st.subheader('🏆 The latest winner is...')
    st.subheader('🙇 SORRY💦💦💦 we need to wait until every bot has its first trade...')
    if (df1_dates["end_date"]==""):
        st.text('currently bot1-scalping is waiting for its trading opportunity')
    else:
        st.text('currently bot2-breakout is waiting for its trading opportunity')
st.markdown("***")


# plot cumulative return

st.subheader('Cumulative Returns within date range')

if (df1_dates["end_date"]!="")and(df2_dates["end_date"]!=""):
    if end_date > start_date:
        if date_range[0] != date_range[1]:

            ch = alt.Chart(filtered_df).mark_area(opacity=0.3, line=True).encode(
                 alt.X('transaction_time', title='Transaction Time'),\
                 alt.Y('cum_return', title='Cumulative Returns', stack=None),\
                 alt.Color('bot',scale=alt.Scale(domain=['bot1', 'bot2'],
                    range=['#EA6309', '#FFCF33'])),
                 alt.Tooltip('cum_return'))

            st.altair_chart(ch, use_container_width=True)
    else:
        st.subheader('🙇 SORRY💦💦💦 we need to wait until having at least 2 day\'s trading data...')
        
else:
    st.subheader('🙇 SORRY💦💦💦 we need to wait until every bot has its first trade...')
    if (df1_dates["end_date"]==""):
        st.text('currently bot1-scalping is waiting for its trading opportunity')
    else:
        st.text('currently bot2-breakout is waiting for its trading opportunity')
        






