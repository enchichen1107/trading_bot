# fetching data for symbol to name conversion

import requests
import pandas as pd

url = 'https://web-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
params = {
        'start': 1,
        'limit': 5000,
    }
r = requests.get(url,params=params)
data = r.json()
 
symbols=[]
names=[]
for item in data['data']:
    symbols.append(item['symbol'])
    names.append(item['name'])
    print(f"{item['symbol']:5} | {item['name'][:10]}")

temp = {'symbol':symbols,'name':names}
df = pd.DataFrame(temp)
df.to_csv('name_symbol.csv',index=False)
