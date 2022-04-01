import os

from binance.client import Client

from time import sleep

from binance import ThreadedWebsocketManager

import pandas as pd
from datetime import datetime
from pycoingecko import CoinGeckoAPI
cg = CoinGeckoAPI()
import numpy as np
import pandas as pd
from pylab import plt
from math import sqrt
import time
import datetime
import datetime as dt
import pandas_datareader as web
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import talib
from talib.abstract import *
from datetime import date, timedelta
import itertools
import math
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.stattools import coint
from itertools import combinations
import time
from sklearn.linear_model import LinearRegression
import statsmodels.api as sm
from scipy.optimize import minimize, rosen, rosen_der
#pip install pycoingecko
#pip install TA-Lib/brew install ta-lib
from scipy import stats
import numpy as np
import os
import time

api_key = os.getenv('api_key')
api_secret = os.getenv('api_secert')

client = Client(api_key, api_secret,testnet=True)


def current_milli_time():
    return round(time.time() * 1000)


def getBinanceDataFuture(symbol, interval, start, end, limit=5000):
    df = pd.DataFrame()
    startDate = end
    prev = start
    while (startDate!=prev):
        prev = startDate
        url = 'https://fapi.binance.com/fapi/v1/klines?symbol=' + \
            symbol + '&interval=' + interval
        if startDate is not None:
            url += '&endTime=' + str(startDate)
        df2 = pd.read_json(url)
        df2.columns = ['Opentime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Closetime', 'Quote asset volume', 'Number of trades','Taker by base', 'Taker buy quote', 'Ignore']

        df = pd.concat([df2, df], axis=0, ignore_index=True, keys=None)
        startDate = df.Opentime[0]



    df.reset_index(drop=True, inplace=True)
    df['Opentime'] = pd.to_datetime(df['Opentime'],unit='ms')
    df = df.loc[1:]
    df = df[['Opentime', 'Open', 'High', 'Low', 'Close']]
    df = df.set_index('Opentime')
    df = df.drop_duplicates(keep=False)
    return df

def getBinanceDataFundingRate(symbol, interval, start, end, limit=1000):
    df = pd.DataFrame()
    startDate = start
    prev = 0
    while (startDate!=prev):
        prev = startDate
        url = 'https://fapi.binance.com/fapi/v1/fundingRate?symbol=' + \
            symbol + '&startTime=' + str(startDate) + '&limit=' + str(limit)


        df2 = pd.read_json(url)
        df2.columns = ['symbol','fundingTime','fundingRate']

        df = pd.concat([df, df2], axis=0, ignore_index=True, keys=None)
        startDate = df2.fundingTime[len(df2)-1]



    df.reset_index(drop=True, inplace=True)
    df['fundingTime'] = pd.to_datetime(df['fundingTime'],unit='ms')
    #df = df.loc[1:]
    #df = df.set_index('fundingTime')
    df = df.drop_duplicates(keep=False)
    df['fundingTime'] = df['fundingTime'].dt.floor('Min')
    df = df.set_index('fundingTime')
    return df

def signalf(varaible,a,b):

    lookback,sdenter,sdexit,sdloss = varaible
    lookback = int(lookback)


    #merge data
    pairPrice = a.merge(b, left_index=True, right_index=True, how='left')
    pairPrice = pairPrice.dropna()

    reg = sm.OLS(pairPrice['Open_x'],pairPrice['Open_y']).fit()
    reg2 = sm.OLS(pairPrice['Open_y'],pairPrice['Open_x']).fit()

    #see which token should be a the dependent variable
    if adfuller(reg.resid)[1]<adfuller(reg2.resid)[1]:
        y = pairPrice['Open_x']
        x = pairPrice['Open_y']
        yfr = pairPrice['fr_x']
        xfr = pairPrice['fr_y']
        hedge = reg.params[0]
        spread = reg.resid
        y_name = str(a)
        x_name = str(b)

    else:
        y = pairPrice['Open_y']
        x = pairPrice['Open_x']
        xfr = pairPrice['fr_x']
        yfr = pairPrice['fr_y']
        hedge = reg2.params[0]
        spread = reg2.resid
        y_name = str(b)
        x_name = str(a)



    #creating bbands
    bands = pd.DataFrame(BBANDS(spread,timeperiod=lookback,nbdevup=sdenter,nbdevdn = sdenter,matype=1)).T
    bands = bands.set_index(pairPrice.index)
    bands.columns = ['1upper','1mid','1lower']

    bands2 = pd.DataFrame(BBANDS(spread,timeperiod=lookback,nbdevup=sdexit,nbdevdn = sdexit,matype=1)).T
    bands2 = bands2.set_index(pairPrice.index)
    bands2.columns = ['upper','mid','lower']

    bands3 = pd.DataFrame(BBANDS(spread,timeperiod=lookback,nbdevup=sdloss,nbdevdn = sdloss,matype=1)).T
    bands3 = bands3.set_index(pairPrice.index)
    bands3.columns = ['upper2','mid2','lower2']
    bbands = bands2.join(bands)
    bbands = bbands.join(bands3)
    bbands = bbands.drop(columns = ['mid','1mid','mid2'])

    bbands['y'] = y
    bbands['x'] = x
    bbands['spread'] = spread
    bbands['hedge'] =hedge
    bbands['xfr'] = xfr
    bbands['yfr'] = yfr

    bbands = bbands.dropna()

    #creating positions
    bbands.loc[bbands['spread']>bbands['1upper'],'position']=-1
    bbands.loc[(bbands['spread']<bbands['upper']) & (bbands['spread']>bbands['lower']),'position']=0
    bbands.loc[bbands['spread']<bbands['1lower'],'position']=1
    bbands.loc[(bbands["spread"]<bbands["lower2"]) | (bbands["spread"]>bbands["upper2"]),'position']=0
    bbands = bbands.ffill()
    bbands['oposition'] = -1*bbands["position"]
    bbands = bbands.fillna(0)
    #creating size
    bbands.loc[bbands['position'].diff()!=0,"ysize"] = bbands["y"]/(bbands["x"]*bbands["hedge"]+bbands["y"])
    bbands['xsize'] = 1-bbands['ysize']

    #creating the diff
    bbands[['ydiff','xdiff']] = bbands[['y','x']].diff()
    bbands = bbands.ffill()



    return bbands,y_name,x_name

if __name__ == '__main__':
    token1="XRPUSDT"
    token2="TRXUSDT"
    while True:
        token1data = getBinanceDataFuture(token1,1458955882,current_milli_time())
        token2data = getBinanceDataFuture(token2,1458955882,current_milli_time())

        #process data with bbands
        bbands,y_name,x_name = simulf(token1data,token2data)
        signal = bbands.iloc[-1]

        #get current account situation
        cap = client.futures_account()["totalMarginBalance"]*.99
        df = pd.DataFrame(client.futures_account()['positions'])
        df = df.apply(lambda col:pd.to_numeric(col, errors='ignore'))

        #get current long short position size
        currentPos = [float(df[df["symbol"]==y_name].positionAmt),float(df[df["symbol"]==x_name].positionAmt)]

        if signal.poistion !=0:
            #if current signal
            if currentPos==[0,0]:
                new_lvrg = 1
                client.futures_change_leverage(symbol = y_name,leverage=new_lvrg)
                client.futures_change_leverage(symbol = x_name,leverage=new_lvrg)
                size = [cap*signal.y_size/float(client.futures_symbol_ticker(symbol = y_name)['price']),cap*signal.x_size/float(client.futures_symbol_ticker(symbol = x_name)['price'])]
                if signal.poistion == -1:
                    client.futures_create_order(symbol=y_name,type='MARKET',side='SELL',quantity=quantityPercision(y_name,size[0]))
                    client.futures_create_order(symbol=x_name,type='MARKET',side='BUY',quantity=quantityPercision(y_name,size[1]))
                else:
                    client.futures_create_order(symbol=y_name,type='MARKET',side='BUY',quantity=quantityPercision(y_name,size[0]))
                    client.futures_create_order(symbol=x_name,type='MARKET',side='SELL',quantity=quantityPercision(y_name,size[1]))
            else:
                pass
        else:
            if currentPos==[0,0]:
                pass
            else:
                currentLS = ['SELL' if i < 0 else 'BUY' for i in CurrentPos]
                client.futures_create_order(symbol=x_name,side=currentLS[0],type="MARKET",reduceOnly = True,quantity = abs(currentPos[1]))
                client.futures_create_order(symbol=y_name,side=currentLS[1],type="MARKET",reduceOnly = True,quantity =abs(currentPos[0]))


        client.futures_account_trades()[-2:]
        print([y_name + "price: " +str(signal.y) + +  cap*signal.y_size/signal.y,signal.x,cap*signal.x_size/signal.x])
