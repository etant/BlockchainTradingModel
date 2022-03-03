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
from autogluon.tabular import TabularDataset, TabularPredictor

def getData(id):
    end = dt.datetime.now()
    start = dt.datetime(2010,1,10)
    data = web.DataReader(id+"-USD", 'yahoo', start, end)
    data = data.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
    return data

def minMax(data):
    #this could be EMA or MA and different timeperiod
    data["MA"] = EMA(data["close"],timeperiod=20)
    localMin = []
    localMax = []

    for i in range(len(data)-1):
        if data["MA"].iloc[i] > data["MA"].iloc[i+1] and data["MA"].iloc[i] > data["MA"].iloc[i-1] :
            localMax.append((data["MA"].iloc[i],i))
        elif data["MA"].iloc[i] < data["MA"].iloc[i+1] and data["MA"].iloc[i] < data["MA"].iloc[i-1] :
            localMin.append((data["MA"].iloc[i],i))
        else:
            continue
    localMin = pd.DataFrame(localMin,columns=["localMin","minIndex"] )
    localMax= pd.DataFrame(localMax,columns=["localMax","maxIndex"] )


    frames = [localMin,localMax]
    minMax = pd.concat(frames, axis=1)

    return minMax

def turningPoints(minMax, data):
    isna = False
    if minMax.isna().any().any():
        isna = True
        minMax = minMax.fillna(len(data))

    result= []
    minI = int(minMax["minIndex"].iloc[0])
    maxI = int(minMax["maxIndex"].iloc[0])

    if minMax["maxIndex"].iloc[0]>minMax["minIndex"].iloc[0]:
        peaki = max(data["close"][minI:maxI])
        prevMinI = minI
        prevMaxI = maxI
        peakIndex = int(np.where(data["close"]== peaki)[0])
        result.append((peaki,data.index[peakIndex],"peak"))
    else:
        troughi = min(data["close"].iloc[maxI:minI])
        prevMinI = minI
        prevMaxI = maxI
        troughIndex = int(np.where(data["close"]== troughi)[0])
        result.append((troughi,data.index[troughIndex],"trough"))

    for i in range(1,len(minMax)):
        minI = int(minMax["minIndex"].iloc[i])
        maxI = int(minMax["maxIndex"].iloc[i])

        if minMax["maxIndex"].iloc[0]>minMax["minIndex"].iloc[0]:

            peaki = max(data["close"][minI:maxI])
            troughi = min(data["close"].iloc[prevMaxI: minI])
            peakIndex = int(np.where(data["close"]== peaki)[0])
            troughIndex = int(np.where(data["close"]== troughi)[0])
            result.append((troughi,data.index[troughIndex],"trough"))
            result.append((peaki,data.index[peakIndex],"peak"))


        else:

            troughi = min(data["close"].iloc[maxI:minI])
            peaki = max(data["close"].iloc[prevMinI: maxI])
            peakIndex = int(np.where(data["close"]== peaki)[0])
            troughIndex = int(np.where(data["close"]== troughi)[0])
            result.append((peaki,data.index[peakIndex],"peak"))
            result.append((troughi,data.index[troughIndex],"trough"))
        prevMinI = minI
        prevMaxI = maxI

    result = pd.DataFrame(result, columns = ["price","date","type"])

    #this removes the label, since it will assume automaticlly to be a local min or local max
    if isna:
        result.drop(result.tail(1).index,inplace=True)

    return result

def helper(start_date,end_date):
    delta =  end_date[1] - start_date[1]    # returns timedelta
    label = []
    for i in range(int(delta.days + 1)):
        day = start_date[1] + timedelta(days=i)
        if (start_date[2]== "peak"):
            score = np.linspace(1,-1,delta.days+1)
        else:
            score = np.linspace(-1,1,delta.days+1)
        label.append((day,score[i]))
    return label

def labeling(data):
    minmax = minMax(data)
    TurnPdata = turningPoints(minmax,data)
    label = []
    prev = TurnPdata.iloc[0]
    for i in range(1,len(TurnPdata)):
        now = TurnPdata.iloc[i]
        label.append(helper(prev,now))
        prev = now
    return pd.DataFrame(list(itertools.chain.from_iterable(label)),columns =["Dates","Label"]).drop_duplicates(subset=["Dates"]).set_index("Dates")


def feature(eth):
    feature = pd.DataFrame()
    periods = []
    temp2 = []
    useless = ['Math Operators' , "Math Transform", 'Pattern Recognition','Price Transform','Statistic Functions']
    groups = talib.get_function_groups()
    for i in groups:
        if (i not in useless):
            for j in groups[i]:
                try:
                    feature[j] = eval(j)(eth)
                    continue
                except:
                    periods.append(j)

                try:
                    temp = eval(j)(eth)
                    for k in temp:
                        feature[k] = temp[k]
                except:
                    temp2.append(j)
    return feature.dropna()

def combine(data):
    labels = labeling(data)
    modelData = pd.concat([feature(data), labels], axis=1).dropna()
    return modelData

if __name__ == '__main__':
    eth = getData('eth')
    data = combine(eth)
    split = data.iloc[:1183]
    test = data.iloc[1183:]
    save_path = 'agModels-predictClass'  # specifies folder to store trained models
    predictor = TabularPredictor(label="Label", path=save_path).fit(split,excluded_model_types=["GBM","XGB"])
    y_test = test["Label"]
    test_data_nolab = test.drop(columns=["Label"])
    y_pred = predictor.predict(test_data_nolab)
    perf = predictor.evaluate_predictions(y_true=y_test, y_pred=y_pred, auxiliary_metrics=True)
    print(y_pred)
    print(y_test)
