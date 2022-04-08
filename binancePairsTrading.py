from key import *
from binance.client import Client
import pandas as pd
import time
from datetime import datetime, tzinfo, timedelta
import talib
from talib.abstract import *
from statsmodels.tsa.stattools import adfuller
import statsmodels.api as sm
import pytz
#pip install TA-Lib

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



def signalf(varaible,a,b,a_name,b_name):
    lookback,sdenter,sdexit,sdloss = varaible
    lookback = int(lookback)


    #merge data
    pairPrice = a.merge(b, left_index=True, right_index=True, how='left')
    pairPrice = pairPrice.dropna()

    reg = sm.OLS(pairPrice['Close_x'],pairPrice['Close_y']).fit()
    reg2 = sm.OLS(pairPrice['Close_y'],pairPrice['Close_x']).fit()

    #see which token should be a the dependent variable
    if adfuller(reg.resid)[1]<adfuller(reg2.resid)[1]:
        y = pairPrice['Close_x']
        x = pairPrice['Close_y']

        hedge = reg.params[0]
        spread = reg.resid
        y_name = a_name
        x_name = b_name

    else:
        y = pairPrice['Close_y']
        x = pairPrice['Close_x']

        hedge = reg2.params[0]
        spread = reg2.resid
        y_name = a_name
        x_name = b_name



    #creating bbands
    bands = pd.DataFrame(BBANDS(spread,timeperiod=lookback,nbdevup=sdenter,nbdevdn = sdenter,matype=1)).T
    bands = bands.set_index(pairPrice.index)
    bands.columns = ['Short','1mid','Long']

    bands2 = pd.DataFrame(BBANDS(spread,timeperiod=lookback,nbdevup=sdexit,nbdevdn = sdexit,matype=1)).T
    bands2 = bands2.set_index(pairPrice.index)
    bands2.columns = ['exShort','mid','exLong']

    bands3 = pd.DataFrame(BBANDS(spread,timeperiod=lookback,nbdevup=sdloss,nbdevdn = sdloss,matype=1)).T
    bands3 = bands3.set_index(pairPrice.index)
    bands3.columns = ['stShort','mid2','stLong']
    bbands = bands2.join(bands)
    bbands = bbands.join(bands3)
    bbands = bbands.drop(columns = ['mid','1mid','mid2'])

    bbands['y'] = y
    bbands['x'] = x
    bbands['spread'] = spread
    bbands['hedge'] =hedge


    bbands = bbands.dropna()


    return bbands,y_name,x_name

def quantityPercision(symbol,size):
    info = client.futures_exchange_info()
    for x in info['symbols']:
        if x['symbol'] == symbol:
            prec =  x['quantityPrecision']
    factor = 10.0**prec
    return int(size*factor)/factor

def current_milli_time():
    return round(time.time() * 1000)


def getPostion(signal,currentPos):
    if (currentPos ==[0,0]).all():
        if (signal["spread"]>signal["Short"])&(signal["spread"]<signal["stShort"]):
            return -1
        elif (signal["spread"]<signal["Long"]) & (signal["spread"]>signal["stLong"]):
            return 1
        else:
            return 0
    elif (np.sign(currentPos)==[-1,1]).all():
        if (signal["spread"]<signal["exShort"])|(signal["spread"]>signal["stShort"]):
            return 0
        else:
            return -1
    else:
        if (signal["spread"]>signal["exLong"])|(signal["spread"]<signal["stLong"]):
            return 0
        else:
            return 1


if __name__ == '__main__':


    client = Client(api_key, api_secret)
    log = open("tradingLog.txt", "a")


    token1="XRPUSDT"
    token2="TRXUSDT"
    new_lvrg = 1
    client.futures_change_leverage(symbol = token1,leverage=new_lvrg)
    client.futures_change_leverage(symbol = token2,leverage=new_lvrg)
    while True:
        now = datetime.utcnow()
        nexthour = now.replace(microsecond=0, second=0, minute=0)+timedelta(hours=1)
        timesleep = (nexthour-now).seconds
        time.sleep(timesleep)

        utc_now_dt = datetime.now(tz=pytz.UTC)
        log.write(str(utc_now_dt.strftime("%d/%m/%Y %H:%M:%S"))+": "+"\n")

        token1data = getBinanceDataFuture(token1,'1h',1458955882,current_milli_time())
        token2data = getBinanceDataFuture(token2,'1h',1458955882,current_milli_time())

        #LookBack Period, SD enter, Sd exit, stoploss
        param = [61*24,1.50,0.1,2.55]
        bbands,y_name,x_name = signalf(param,token1data,token2data,token1,token2)
        signal = bbands.iloc[-1]


        #get current account situation
        cap = float(client.futures_account()["totalMarginBalance"])*.5
        df = pd.DataFrame(client.futures_account()['positions'])
        df = df.apply(lambda col:pd.to_numeric(col, errors='ignore'))
        #get current long short position size

        currentPos = [float(df[df["symbol"]==y_name].positionAmt),float(df[df["symbol"]==x_name].positionAmt)]
        position = getPostion(signal,currentPos)

        if position !=0:
            if currentPos==[0,0]:
                #get percetange of y and x
                yp = signal["y"]/(signal["x"]*signal["hedge"]+signal["y"])
                xp = 1-yp
                #get sizing
                size = np.array([position*cap*yp/float(client.futures_symbol_ticker(symbol = y_name)['price']),-1*position*cap*xp/float(client.futures_symbol_ticker(symbol = x_name)['price'])])
                LS = ['SELL' if i < 0 else 'BUY' for i in size]

                try:
                    client.futures_create_order(symbol=y_name,type='MARKET',side=LS[0],quantity=quantityPercision(y_name,abs(size[0])))
                    client.futures_create_order(symbol=x_name,type='MARKET',side=LS[1],quantity=quantityPercision(x_name,abs(size[1])))

                    df = pd.DataFrame(client.futures_account()['positions'])
                    df = df.apply(lambda col:pd.to_numeric(col, errors='ignore'))
                    df = df[df["positionAmt"]!=0]
                    for i in range(len(df)):
                        log.write(df["symbol"][i] + " price: " +str(float(df["entryPrice"][i] )) + " quant: " + str(float(df["positionAmt"][i]))+"\n")

                    log.write("expectations: "+"\n")
                    log.write(y_name + "price: " +str(signal.y) + "quant: " + str(size[0])+"\n")
                    log.write(x_name + "price: " +str(signal.x) + "quant: " + str(size[1])+"\n")

                except Exception as e:
                        log.write("There was an error: " + str(e)+"\n")

            else:
                pass
        else:
            if currentPos==[0,0]:
                pass
            else:
                try:
                    currentLS = ['SELL' if i < 0 else 'BUY' for i in CurrentPos]
                    client.futures_create_order(symbol=x_name,side=currentLS[0],type="MARKET",reduceOnly = True,quantity = abs(currentPos[1]))
                    client.futures_create_order(symbol=y_name,side=currentLS[1],type="MARKET",reduceOnly = True,quantity =abs(currentPos[0]))
                    log.write("expectations: "+"\n")
                    log.write(y_name + "price: " +str(signal.y)+"\n")
                    log.write(x_name + "price: " +str(signal.x)+"\n")

                except Exception as e:
                        log.write("There was an error: " + str(e)+"\n")
        log.write("----------------------------------"+"\n")
        log.flush()
