# below codes are for btc historical price data analysis overview, mainly for plotting exploratory results

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.style.use("seaborn")



# load in dataframe=========================================================================
data = pd.read_csv("BTCUSDT15m.csv", parse_dates = ["Date"], index_col = "Date")
data["returns"] = np.log(data.Close / data.Close.shift(1))
data["creturns"] = data["returns"].cumsum().apply(np.exp)
# select time section=======================================================================
# data = data.loc['2021-06-04':]

# plot cumulative returns variation=========================================================
fig = data.plot(y='creturns')
title = "HODL BTCUSDT since 2021.06"
fig.legend(fontsize=14)
fig.set_title(title,fontsize=20)
fig.set_xlabel('Date.', fontsize=16)
fig.set_ylabel('Cumulative Return', fontsize=16)
plt.savefig('HODL2021.png')



# plotting the HODL strategy returns decline within three years=============================
# data preprocessing
creturns_compare=[]
dates = ['2019-06-04','2020-06-04','2021-06-04']
for i in range(3):
    data = data.loc[dates[i]:].copy()
    data["returns"] = np.log(data.Close / data.Close.shift(1))
    data["creturns"] = data["returns"].cumsum().apply(np.exp)
    creturns_compare.append(data["creturns"].iloc[-1])

comp = [list(i) for i in zip(dates,creturns_compare)]
comp_plt = pd.DataFrame(comp,columns = ['Date', 'creturns'])
fig = comp_plt.plot(x = 'Date',y = 'creturns',fontsize = 12)

# adding annotation into fig
for i,y in enumerate(zip(dates,creturns_compare)):
    label = "{:.3f}".format(y[1])
    plt.annotate(label,
                 (i,y[1]), 
                 textcoords = "offset points",
                 xytext = (0,10), 
                 ha = 'center',
                 size = 14,
                 arrowprops = dict(arrowstyle="fancy", color='red'))

# adding other features into fig
title = "Decline of HODL BTCUSDT in binance"
fig.legend(fontsize=14)
fig.set_title(title,fontsize=20)
fig.set_xlabel('Date.', fontsize=16)
fig.set_ylabel('Cumulative Return', fontsize=16)
plt.savefig('HODLdecline.png')
