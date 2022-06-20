
# Remind: bot1 and bot2 are running on different AWS t2.micro EC2

from binance.client import Client
from binance import ThreadedWebsocketManager
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import copy
import time
import boto3
import base64
from botocore.exceptions import ClientError
import json
import psycopg2
from multiprocessing import Process
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText



# first handle all kinds of secrets and connections========================
def get_secret(secret_name, region_name):

    secret_name = secret_name
    region_name = region_name

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS key.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
    return secret



# get binance api secret
api_secret = get_secret(secret_name = "forBotTest2", region_name = "us-east-1")            
api_secrets = json.loads(api_secret)           

api_key2 = api_secrets['api_key2']
secret_key2 = api_secrets['secret_key2']


# connect to binance api
client = Client(api_key = api_key2, api_secret = secret_key2, tld = "com", testnet = True)
clientdata = Client(tld = "com", testnet = False)


# get db secret
db_secret = get_secret(secret_name = "tradeDB", region_name = "us-east-1")            
db_secrets = json.loads(db_secret)           

rds_host  = db_secrets['host']
name = db_secrets['username']
password = db_secrets['password']
db_name = db_secrets['dbname']

# connect to db
connection = psycopg2.connect(user=name, password=password, host=rds_host, database=db_name)
cursor = connection.cursor()


# get google app secret
app_secret = get_secret(secret_name = "pythonMail", region_name = "us-east-1")
app_secrets = json.loads(app_secret)
mail_secret = app_secrets['app_key']








# the trading bot class, trades will be generated from here============================
class breakout_bot():

    def __init__(self, symbol, interval, units, now, rollx, volx, position = ""):
        
        self.symbol = symbol
        self.interval = interval
        self.available_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
        self.units = units
        self.position = position
        self.signal = position
        # set close bot time
        self.end = now + timedelta(hours=11)
        self.rollx = rollx
        self.volx = volx
        self.loss = 0
   

    
    def start_trading(self):
        
        # start binance websocket
        self.twm = ThreadedWebsocketManager()
        self.twm.start()
        print("start from trade")
        
        # prepare data for trading
        historical_days = self.rollx + 7
        
        if self.interval in self.available_intervals:
            self.get_most_recent(symbol = self.symbol, interval = self.interval,
                                 days = historical_days)
            self.twm.start_kline_socket(callback = self.stream_candles,
                                        symbol = self.symbol, interval = self.interval)
    
    
    def get_most_recent(self,symbol,interval,days):
        
        now = datetime.utcnow()
        past = str(now - timedelta(days = days))
        
        # get historical price data
        bars = clientdata.get_historical_klines(symbol = self.symbol, interval = self.interval,
                                            start_str = past, end_str = None, limit = 1000)
        df = pd.DataFrame(bars)
        df["Date"] = pd.to_datetime(df.iloc[:,0], unit = "ms")
        df.columns = ["Open Time", "Open", "High", "Low", "Close", "Volume",
                      "Clos Time", "Quote Asset Volume", "Number of Trades",
                      "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore", "Date"]
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        df.set_index("Date", inplace = True)
        for column in df.columns:
            df[column] = pd.to_numeric(df[column], errors = "coerce")
        df["Complete"] = [True for row in range(len(df)-1)] + [False]
        
        self.data = df
        


    def stream_candles(self,msg):

        # get and process live stream data
        event_time = pd.to_datetime(msg["E"], unit = "ms")
        start_time = pd.to_datetime(msg["k"]["t"], unit = "ms")
        first   = float(msg["k"]["o"])
        high    = float(msg["k"]["h"])
        low     = float(msg["k"]["l"])
        close   = float(msg["k"]["c"])
        volume  = float(msg["k"]["v"])
        complete=       msg["k"]["x"]

        # stop trading session 
        if event_time >= self.end:
            self.twm.stop()
            if self.position != "":
                if self.position == "Buy":
                    order = client.create_order(symbol = self.symbol, side = "SELL", type = "MARKET", quantity = self.units)
                else:
                    order = client.create_order(symbol = self.symbol, side = "BUY", type = "MARKET", quantity = self.units)
                self.report_trade(order, "GOING NEUTRAL AND STOP") 
                self.position = ""
            else: 
                print("STOP")

        # update df with live data
        self.data.loc[start_time] = [first, high, low, close, volume, complete]

        # if the latest bar is complete then start trading strategy
        if complete == True:
            self.start_strategy()
            self.execute_trades()



    def start_strategy(self):
        
        ohlc_dict=self.data.copy()
        
        # calculate ATR
        ohlc_dict['H-L']=abs(ohlc_dict['High']-ohlc_dict['Low'])
        ohlc_dict['H-PC']=abs(ohlc_dict['High']-ohlc_dict['Close'].shift(1))
        ohlc_dict['L-PC']=abs(ohlc_dict['Low']-ohlc_dict['Close'].shift(1))
        ohlc_dict['TR']=ohlc_dict[['H-L','H-PC','L-PC']].max(axis=1,skipna=False)
        ohlc_dict['ATR'] = ohlc_dict['TR'].rolling(self.rollx).mean()
        
        # calculate breakout point
        ohlc_dict["roll_max_cp"] = ohlc_dict["High"].rolling(self.rollx).max()
        ohlc_dict["roll_min_cp"] = ohlc_dict["Low"].rolling(self.rollx).min()
        ohlc_dict["roll_max_vol"] = ohlc_dict["Volume"].rolling(self.rollx).max()
        ohlc_dict.dropna(inplace=True)
        
        # processing trading signal
        if self.position == "":
            if ohlc_dict["High"][-1]>=ohlc_dict["roll_max_cp"][-1] and \
               ohlc_dict["Volume"][-1]>self.volx*ohlc_dict["roll_max_vol"][-2]:
                self.signal = "Buy"
            elif ohlc_dict["Low"][-1]<=ohlc_dict["roll_min_cp"][-1] and \
               ohlc_dict["Volume"][-1]>self.volx*ohlc_dict["roll_max_vol"][-2]:
                self.signal = "Sell"

        elif self.position == "Buy":
            if ohlc_dict["Low"][-1]<(ohlc_dict["Close"][-2] - ohlc_dict["ATR"][-2]):
                self.signal = "Buy_Close"
            elif ohlc_dict["Low"][-1]<=ohlc_dict["roll_min_cp"][-1] and \
                 ohlc_dict["Volume"][-1]>self.volx*ohlc_dict["roll_max_vol"][-2]:
                self.signal = "Close_Sell"

        elif self.position == "Sell":
            if ohlc_dict["High"][-1]>(ohlc_dict["Close"][-2] + ohlc_dict["ATR"][-2]):
                self.signal = "Sell_Close"
            elif ohlc_dict["High"][-1]>=ohlc_dict["roll_max_cp"][-1] and \
               ohlc_dict["Volume"][-1]>self.volx*ohlc_dict["roll_max_vol"][-2]:
                self.signal = "Close_Buy"



    def execute_trades(self): 
        
        # execute trades according to trading signal
        if self.signal == "Sell":
            order = client.create_order(symbol = self.symbol, side = "SELL", type = "MARKET", quantity = self.units)
            print("New short position initiated")
            self.report_trade(order, "GOING SHORT")
            self.position="Sell"
        elif self.signal == "Buy":
            order = client.create_order(symbol = self.symbol, side = "BUY", type = "MARKET", quantity = self.units)
            print("New long position initiated")
            self.report_trade(order, "GOING LONG")
            self.position="Buy"
        elif self.signal == "Sell_Close":
            order = client.create_order(symbol = self.symbol, side = "BUY", type = "MARKET", quantity = self.units)
            print("Closing short position")
            self.report_trade(order, "GOING NEUTRAL")
            self.position=""
        elif self.signal == "Buy_Close":
            order = client.create_order(symbol = self.symbol, side = "SELL", type = "MARKET", quantity = self.units)
            print("Closing long position")
            self.report_trade(order, "GOING NEUTRAL")
            self.position=""
        elif self.signal == "Close_Sell":
            order = client.create_order(symbol = self.symbol, side = "SELL", type = "MARKET", quantity = self.units)
            print("Closing long position")
            self.report_trade(order, "GOING NEUTRAL")
            time.sleep(0.1)
            order = client.create_order(symbol = self.symbol, side = "SELL", type = "MARKET", quantity = self.units)
            print("Turning short position")
            report_trade(order, "GOING SHORT")
            position="Sell"
        elif self.signal == "Close_Buy":
            order = client.create_order(symbol = self.symbol, side = "BUY", type = "MARKET", quantity = self.units)
            print("Closing short position")
            self.report_trade(order, "GOING NEUTRAL")
            time.sleep(0.1)
            order = client.create_order(symbol = self.symbol, side = "BUY", type = "MARKET", quantity = self.units)
            print("Turning long position")
            self.report_trade(order, "GOING LONG")
            self.position="Buy"
        self.signal = ""


    def report_trade(self, order, going):

        # extract data from order
        side = order["side"]
        time = pd.to_datetime(order["transactTime"], unit = "ms")
        base_units = float(order["executedQty"])
        quote_units = float(order["cummulativeQuoteQty"])
        price = round(quote_units / base_units, 5)

        # report the trade
        print(2 * "\n" + 100* "-")
        print("{} | {}".format(time, going)) 
        print("{} | Base_Units = {} | Quote_Units = {} | Price = {} ".format(time, base_units, quote_units, price))
        print(100 * "-" + "\n")


        

# the trading data collector class, trading information will be written to db from here====
class data_collector():

    def __init__(self, now, info):
        
        self.end = now + timedelta(hours=11.1)
        self.api_key = api_key2
        self.secret_key = secret_key2
        self.btc = float(info['balances'][1]['free'])
        self.usdt = float(info['balances'][6]['free'])
        print(self.btc, self.usdt)
        
        
            
    def stream_data(self, msg):
    
        # get and process live stream data
        if (msg["e"]=='executionReport') and (msg["x"]=='TRADE') and (msg["X"]=='FILLED'):
            event_time = pd.to_datetime(msg["E"], unit = "ms")
            transaction_time = pd.to_datetime(msg["T"], unit = "ms") 
            symbol = msg["s"]
            side = msg["S"]
            price = float(msg["Z"])/float(msg["z"])
            print("Time: {}".format(transaction_time))
            print("Symbol: {}| Side: {}| Price: {}".format(symbol,side,price))

            postgres_insert_query = """ INSERT INTO trade_record2 (transaction_time, symbol, side, price) VALUES (%s,%s,%s,%s)"""
            cursor.execute(postgres_insert_query, (transaction_time,symbol,side,price))
            connection.commit()

        elif (msg["e"]=='outboundAccountPosition'):
            event_time = pd.to_datetime(msg["E"], unit = "ms")
            update_time = pd.to_datetime(msg["u"], unit = "ms") 
            for item in msg["B"]:
                symbol = item["a"]
                amount = float(item["f"])
                print("u_Time: {}| Asset: {}| Amount: {}".format(update_time,symbol,amount))

                postgres_insert_query = """ INSERT INTO asset2 (update_time, symbol, amount) VALUES (%s,%s,%s)"""
                cursor.execute(postgres_insert_query, (update_time,symbol,amount))
                connection.commit()
                if symbol == 'BTC':
                    if amount < (self.btc)*0.95:
                        self.alert_mail(mail_secret)
                elif symbol == 'USDT':
                    if amount < (self.usdt)*0.95:
                        self.alert_mail(mail_secret)
                        
                        
            
            
    def alert_mail(self, mail_secret):
    
        # creating mail
        content = MIMEMultipart()  
        content["subject"] = "Alert from bot2"  
        content["from"] = "enchichen.md10@nycu.edu.tw"  
        content["to"] = "enchichen.md10@nycu.edu.tw" 
        content.attach(MIMEText("You have better check out trading bot2")) 
        mail_secret = mail_secret
        # sending through gmail
        with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:  
            try:
                smtp.ehlo()  
                smtp.starttls()  
                smtp.login("enchichen.md10@nycu.edu.tw", mail_secret)  
                smtp.send_message(content)  
                print("Complete sending mail!")
            except Exception as e:
                print("Error message: ", e)
        
            
        
    def start_collecting(self):
        
        # start the web socket to get bot's live trading information
        self.twm = ThreadedWebsocketManager(api_key = self.api_key, api_secret = self.secret_key, tld = "com", testnet = True)
        self.twm.start()
        print("start from collect")
        
        self.twm.start_user_socket(callback = self.stream_data)
        while datetime.utcnow() < self.end:
            pass
        self.twm.stop()
        cursor.close()
        connection.close()
        print("STOP from db")
        
        

# below codes are for initializing bot and start process===========================
if __name__ == '__main__':
    
    # initialize bot2
    symbol = "BTCUSDT" 
    interval ="1m"
    units = 0.005
    position = ""
    now = datetime.utcnow()
    rollx = 9
    volx = 1.1
    info = client.get_account()

    # initialize bot2's trading
    bot2 = breakout_bot(symbol = symbol, interval = interval, now = now, rollx = rollx,
                        volx = volx, units = units, position = position)
    
    # initialize bot2's trading data collector
    now = datetime.utcnow()
    bot2_data = data_collector(now = now, info = info)
    
    # start process
    p1 = Process(target=bot2.start_trading)
    p1.start()
    p2 = Process(target=bot2_data.start_collecting)
    p2.start()
    p1.join()
    p2.join()



