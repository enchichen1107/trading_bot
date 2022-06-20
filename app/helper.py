import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import psycopg2
import helper
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


@st.experimental_memo
def load_asset_data(data):
    "function to load in asset data"
    df = pd.DataFrame(data)
    if data:
        df.columns = ["update_time","symbol","amount"]
        df["update_time"] = pd.to_datetime(df["update_time"])
    return df    


conn = init_connection()
def fetch_trade(bot):
    # load in trading and asset data
    placeholder = st.empty()
    placeholder.text("Loading .........")
    
    if bot == 1: 
        trade_records = run_query("SELECT * from trade_record1;")
    else:
        trade_records = run_query("SELECT * from trade_record2;")
    placeholder.empty()
    return load_trade_data(trade_records)        


def fetch_asset(bot):
    # load in trading and asset data
    placeholder = st.empty()
    placeholder.text("Loading .........")
    
    if bot == 1: 
        asset_records = run_query("SELECT * from asset1;")
    else:
        asset_records = run_query("SELECT * from asset2;")
    placeholder.empty()
    return load_asset_data(asset_records)  
    
    
    


class layout():
    
    def __init__(self, bot, df, asset):
        self.bot = bot
        self.df = df
        self.asset = asset
        
    
    # below are codes handling metric computing==========================================================  

    def multiple(self, DF):
        "function to locate latest cumulative return"
        df = DF.copy()
        mult = df["cum_return"].iloc[-1]
        return mult

    def CAGR(self, DF, days):
        "function to calculate the Cumulative Annual Growth Rate of a trading strategy"
        df = DF.copy()
        n = len(df)/(days/365.25*1)
        CAGR = (df["cum_return"].tolist()[-1])**(1/n) - 1
        return CAGR

    def volatility(self, DF, days):
        "function to calculate annualized volatility of a trading strategy"
        df = DF.copy()
        vol = df["returns"].std() * np.sqrt(days/365.25)
        return vol

    def sharpe(self, DF, days, rf):
        "function to calculate sharpe ratio ; rf is the risk free rate"
        df = DF.copy()
        sr = (self.CAGR(df, days) - rf)/self.volatility(df, days)
        return sr    

    def max_dd(self, DF):
        "function to calculate max drawdown"
        df = DF.copy()
        df["cum_roll_max"] = df["cum_return"].cummax()
        df["drawdown"] = df["cum_roll_max"] - df["cum_return"]
        df["drawdown_pct"] = df["drawdown"]/df["cum_roll_max"]
        max_dd = df["drawdown_pct"].max()
        return max_dd

    def win_ratio(self, DF):
        "function to calculate win ratio"
        df = DF.copy()
        wins = 0
        for i in range(len(df.index)):
            if (i%2) == 1:
                if (df["profit"].iloc[i] + df["profit"].iloc[i-1])>0:
                    wins+=1
        win_ratio = wins/(len(df.index)/2)
        return win_ratio
    
    
    # below are codes handling app layout==========================================================
    
        
    def start_demo(self):

        # streamlit layout
        if self.bot == 1:
            st.title('Bot1-scalping Performance Detail')
        else:
            st.title('Bot2-breakout Performance Detail')
        st.markdown("***")


        # filter trading data by sidebar
        st.subheader('📊 Trading metric dashboard ✨✨✨✨✨✨✨✨✨✨')
        
        if self.df.shape[0]>0:
            self.end_date = self.df["transaction_time"].iloc[-1].date()
            self.start_date = self.df["transaction_time"].iloc[0].date()
            self.days = (self.end_date-self.start_date).days

            if self.end_date > self.start_date:
                self.date_range = st.sidebar.slider("👇 Pick a date range", min_value=self.start_date,\
                                               value=(self.start_date, self.end_date), max_value=self.end_date, format="MM/DD")

                if self.date_range[0] == self.date_range[1]:
                    st.sidebar.error('Error: End date must be greater than start date.')
                    st.subheader('👈Please pick a date range > 1 day')

                else:
                    st.sidebar.warning('Start date: `%s`\n\nEnd date:`%s`' % (self.date_range[0], self.date_range[1]))
                    self.filtered_df = self.df.loc[(self.df["transaction_time"].dt.date>=self.date_range[0]) & (self.df["transaction_time"].dt.date<=self.date_range[1])]

                    # calculate metric
                    if len(self.filtered_df.index)%2 == 0:
                        self.bot_met = {"CAGR": self.CAGR(self.filtered_df, self.days),\
                               "sharpe": self.sharpe(self.filtered_df,self.days,0),\
                               "max_dd": self.max_dd(self.filtered_df),\
                               "trade_ct": len(self.filtered_df.index),\
                               "profits": (self.filtered_df["profit"].sum())*0.005,\
                               "win_ratio": self.win_ratio(self.filtered_df),\
                               "value":self.filtered_df["cum_return"].iloc[-1],\
                               "delta":self.filtered_df["cum_return"].iloc[-1]/self.filtered_df["cum_return"].iloc[1]}
                    else:
                        self.bot_met = {"CAGR": self.CAGR(self.filtered_df.iloc[:-1 , :], self.days),\
                               "sharpe": self.sharpe(self.filtered_df.iloc[:-1 , :], self.days, 0),\
                               "max_dd": self.max_dd(self.filtered_df.iloc[:-1 , :]),\
                               "trade_ct": len(self.filtered_df.index),\
                               "profits": (self.filtered_df["profit"].iloc[:-1].sum())*0.005,\
                               "win_ratio": self.win_ratio(self.filtered_df.iloc[:-1 , :]),\
                               "value":self.filtered_df["cum_return"].iloc[-2],\
                               "delta":self.filtered_df["cum_return"].iloc[-2]/self.filtered_df["cum_return"].iloc[1]}

                    # layout metric
                    st.text('calculated based on price returns')
                    st.text(' ')


                    col1, col2, col3 = st.columns(3)
                    col1.metric("CAGR", round(self.bot_met["value"],2))
                    col2.metric("Sharpe", str(round(self.bot_met["sharpe"]*100,2))+'%')
                    col3.metric("Max Drawdown", round(self.bot_met["max_dd"],2))

                    
                    st.text(' ')
                    col4, col5, col6 = st.columns(3)
                    col4.metric("Trading Count", self.bot_met["trade_ct"])
                    col5.metric("Cumulative Profits", round(self.bot_met["profits"],2))
                    col6.metric("Win Ratio", str(round(self.bot_met["win_ratio"]*100,2))+'%')
            else:
                st.subheader('🙇 SORRY💦💦💦 we need to wait until having at least 2 day\'s trading data...')
        else:
            st.subheader('🙇 SORRY💦💦💦 currently this bot is still waiting for its trading opportunity')
        st.markdown("***")


        # filter asset data
        st.subheader('Asset Variation within date range')
        if self.asset.shape[0]>0:
            if self.end_date > self.start_date:
                if self.date_range[0] != self.date_range[1]:


                    self.filtered_asset = self.asset.loc[(self.asset["update_time"].dt.date>=self.date_range[0]) & (self.asset["update_time"].dt.date<=self.date_range[1])]

                    # plot asset 
                    self.symbol = st.radio(
                         "👇 Pick a symbol to observe",
                         ('USDT','BTC'), horizontal=True)

                    
                    self.asset_max = self.filtered_asset.loc[self.filtered_asset["symbol"]==self.symbol,["amount"]].max()+30
                    asset_ch = alt.Chart(self.filtered_asset.loc[self.filtered_asset["symbol"]==self.symbol]).mark_area(opacity=0.3,line=True).encode(
                     x=alt.X('update_time', title='Update Time'),
                     y=alt.Y('amount:Q', title='Amount', stack=None,scale=alt.Scale(domain=[0,float(self.asset_max)])),
                     color=alt.value('#FFCF33')
                     )

                    st.altair_chart(asset_ch, use_container_width=True)
            else:
                st.subheader('🙇 SORRY💦💦💦 we need to wait until having at least 2 day\'s trading data...')


        else:
            st.subheader('🙇 SORRY💦💦💦 currently this bot is still waiting for its trading opportunity')
        st.markdown("***")




        # plot cumulative return
        st.subheader('Cumulative Returns within date range')
        if self.df.shape[0]>0:
            if self.end_date > self.start_date:
                if self.date_range[0] != self.date_range[1]:
                    df_ch = alt.Chart(self.filtered_df).mark_area(opacity=0.3,line=True).encode(
                         x=alt.X('transaction_time', title='Transaction Time'),\
                         y=alt.Y('cum_return', title='Cumulative Returns'),\
                         tooltip=alt.Tooltip('cum_return'),
                         color=alt.value('#FFCF33'))

                    st.altair_chart(df_ch, use_container_width=True)
            else:
                st.subheader('🙇 SORRY💦💦💦 we need to wait until having at least 2 day\'s trading data...')

        else:
            st.subheader('🙇 SORRY💦💦💦 currently this bot is still waiting for its trading opportunity')
        st.markdown("***")



        # show raw trading data
        if self.df.shape[0]>0:
            if self.end_date > self.start_date:
                if self.date_range[0] != self.date_range[1]:
                    if st.checkbox('Show raw trading data'):
                        st.subheader('Raw trading data')
                        st.dataframe(self.df)

                    # show raw asset data
                    if st.checkbox('Show raw asset data'):
                        st.subheader('Raw asset data')
                        st.dataframe(self.asset)


                        
                        