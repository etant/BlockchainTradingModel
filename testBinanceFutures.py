import os

from binance import Client
import pandas as pd


def quantityPercision(symbol,size):
    info = client.futures_exchange_info()
    for x in info['symbols']:
        if x['symbol'] == symbol:
            prec =  x['quantityPrecision']
    factor = 10.0**prec
    return int(size*factor)/factor

if __name__ == '__main__':
    api_key = os.getenv('api_key_test')
    api_secret = os.getenv('api_secert_test')


    client = Client(api_key, api_secret,testnet=True)


    dic = {"poistion":1,
       "y_size":0.5,
       "x_size":0.5,
       "x":float(client.futures_symbol_ticker(symbol = "TRXUSDT")['price']),
       "y":float(client.futures_symbol_ticker(symbol = "XRPUSDT")['price'])}
    signal = pd.Series(dic)

    #get current account situation
    y_name = "XRPUSDT"
    x_name = "TRXUSDT"

    cap = float(client.futures_account()["totalMarginBalance"])*(.99)
    df = pd.DataFrame(client.futures_account()['positions'])
    df = df.apply(lambda col:pd.to_numeric(col, errors='ignore'))

    log = open("tradingLog.txt", "a")
    currentPos = [float(df[df["symbol"]==y_name].positionAmt),float(df[df["symbol"]==x_name].positionAmt)]

    if signal.poistion !=0:
        #if current signal
        if currentPos==[0,0]:
            new_lvrg = 1
            client.futures_change_leverage(symbol = y_name,leverage=new_lvrg)
            client.futures_change_leverage(symbol = x_name,leverage=new_lvrg)
            size = [cap*signal.y_size/float(client.futures_symbol_ticker(symbol = y_name)['price']),cap*signal.x_size/float(client.futures_symbol_ticker(symbol = x_name)['price'])]
            try:
                if signal.poistion == -1:
                    client.futures_create_order(symbol=y_name,type='MARKET',side='SELL',quantity=quantityPercision(y_name,size[0]))
                    client.futures_create_order(symbol=x_name,type='MARKET',side='BUY',quantity=quantityPercision(y_name,size[1]))
                else:
                    client.futures_create_order(symbol=y_name,type='MARKET',side='BUY',quantity=quantityPercision(y_name,size[0]))
                    client.futures_create_order(symbol=x_name,type='MARKET',side='SELL',quantity=quantityPercision(x_name,size[1]))

                pastTrade = pd.DataFrame(client.futures_account_trades()[-2:])
                pastTrade["time"] = pd.to_datetime(pastTrade["time"],unit='ms')
                for i in range(len(pastTrade)):
                    log.write(pastTrade["symbol"][i] + " price: " +str(float(pastTrade["price"][i] )) + " quant: " + str(float(pastTrade["qty"][i]))+"\n")
                log.write("expectations: "+"\n")
                log.write(y_name + "price: " +str(signal.y) + "quant: " + str(cap*signal.y_size/signal.y)+"\n")
                log.write(x_name + "price: " +str(signal.x) + "quant: " + str(cap*signal.x_size/signal.x)+"\n")
                log.write("----------------------------------"+"\n")
                log.flush()
            except Exception as e:
                    log.write("There was an error: " + str(e)+"\n")
                    log.write("----------------------------------"+"\n")
                    log.flush()

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
                pastTrade = pd.DataFrame(client.futures_account_trades()[-2:])
                pastTrade["time"] = pd.to_datetime(pastTrade["time"],unit='ms')
                for i in range(len(pastTrade)):
                    log.write(pastTrade["symbol"][i] + " price: " +str(float(pastTrade["price"][i] ))+"\n")
                log.write("expectations: "+"\n")
                log.write(y_name + "price: " +str(signal.y)+"\n")
                log.write(x_name + "price: " +str(signal.x)+"\n")
                log.write("----------------------------------"+"\n")
                log.flush()
            except Exception as e:
                    log.write("There was an error: " + str(e)+"\n")
                    log.write("----------------------------------"+"\n")
                    log.flush()
