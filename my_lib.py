# -*- coding: UTF-8 -*-
#可以根據局屬測站起始與中止日期進行最近站點挑選
import pandas as pd
from os import listdir
from math import cos, asin, sqrt
from datetime import datetime
import os

def distance(lat1, lon1, lat2, lon2):
    p = 0.017453292519943295
    a = 0.5 - cos((lat2-lat1)*p)/2 + cos(lat1*p)*cos(lat2*p) * (1-cos((lon2-lon1)*p)) / 2
    #print (12742 * asin(sqrt(a)))
    return 12742 * asin(sqrt(a))

def closest(data, v):
    return min(data, key=lambda p: distance(v['lat'],v['lon'],p['lat'],p['lon']))

def csv_col_to_numeric(input_col):
    if input_col.dtypes == 'float64' or input_col.dtypes == 'int64':
        return input_col
    else:
        return pd.to_numeric(input_col.str.replace(' ', '').str.replace(',',''),errors='coerce')

def readFile(filepath,filename,row1,row2):
    #read Header
    if (filename[-3:])=="csv":
        Header = pd.read_csv(filepath + filename, header=None, nrows=1, skiprows=row1, delim_whitespace=None, sep=',',low_memory=False,skipinitialspace =True)
    elif (filename[-3:])=="txt":
        Header = pd.read_csv(filepath + filename, header=None, nrows=1, skiprows=row1, delim_whitespace=True, sep=',',low_memory=False,skipinitialspace =True)
    Header=Header.values.tolist()[0]
    #print(Header)
    if "#" in Header:
        Header.remove("#")
    #print(Header)

    if "latitude" in Header:
        Header=Header.replace('latitude', 'lat')
    if "longitude" in Header:
        Header = Header.replace('longitude', 'lon')
    #Header = [w.replace('latitude', 'lat') for w in Header]
    #Header = [w.replace('longitude', 'lon') for w in Header]
    #read table
    if (filename[-3:])=="csv":
        Data= pd.read_csv(filepath + filename, header=None, skiprows=row2, delim_whitespace=None, sep=',',low_memory=True,skipinitialspace =True)
        Data=Data.dropna(axis='columns', how='all')
    elif (filename[-3:])=="txt":
        Data = pd.read_csv(filepath + filename, header=None, skiprows=row2, delim_whitespace=True, sep=',',low_memory=True,skipinitialspace =True)
        Data = Data.dropna(axis='columns', how='all')
    #add Header to table
    Data.columns = Header
    #convert to number
    if 'lon' in Data.columns:
        Data['lon']=csv_col_to_numeric(Data['lon'])
    if 'lat' in Data.columns:
        Data['lat'] = csv_col_to_numeric(Data['lat'])
    if 'Start_date' in Data.columns:
        Data['Start_date']=pd.to_datetime(Data['Start_date'],format='%Y-%m-%d')
    if 'End_date' in Data.columns:
        Data['End_date'] = pd.to_datetime(Data['End_date'], format='%Y-%m-%d')
    #convert to dictionary
    Data_dic=Data.to_dict('records')
    return Data_dic , Data #1 dictionary and 1 dataframe

def MatchStationID(filepath,filename1,filename2, datamonth):
    Station_auto=readFile(filepath, filename1,0,1)
    Station_std = readFile(filepath, filename2,0,1)
    #print(Station_std[0])
    matchstd=[]
    for v in Station_auto[0]:
        #Station_std = readFile(filepath, filename2, 0, 1)
        #print(Station_std[1]['End_date'])
        d3=[e for e in Station_std[0] if ((e.get('Start_date',None) >datetime.strptime(datamonth,'%Y-%m-%d')  and (e.get('End_date',None) < datetime.strptime(datamonth,'%Y-%m-%d'))) or e.get('End_date',None) is pd.NaT )]
        #print(len(d3))
        #print(d3)
        #print(Station_std[0][35]['End_date'])
        #near=closest(Station_std[0], v)
        near = closest(d3, v)
        v.update({'STD_station':near['Station_id'],'STD_Loaction':near['Location_name']})
        matchstd.append(v)
        #print(matchstd)
    #print(matchstd)
    return pd.DataFrame.from_dict(matchstd,orient='columns')


def find_filenames(path_to_dir, suffix ):
    filenames = listdir(path_to_dir)
    return [ filename for filename in filenames if filename.endswith( suffix ) ]

def find_all_filenames( path_to_dir ):
    filenames = listdir(path_to_dir)
    return [ filename for filename in filenames if filename ]

def remove999(data_merge,col1,filterNo,value):
    data_merge.loc[data_merge[col1] < filterNo, col1] = value

#matchStation=MatchStationID(filepath,'Station_auto.csv','Station_std.csv', '1900-01-01','2000-12-31').to_csv(filepath +'match9999.csv', index=None, sep=',', encoding='big5')

def CreateFolder(foldername):
    #current_path = os.path.dirname(os.path.abspath(__file__))
    current_path = os.path.dirname(os.path.realpath(__file__))
    Newfolder =  os.path.join(current_path,foldername )
    try:
        os.stat(Newfolder)
    except:
        os.mkdir(Newfolder)

def mymkdir(Newfolder):
    if not os.path.exists(Newfolder):
        os.makedirs(Newfolder)



def csv_col_to_numeric(input_col):
    if input_col.dtypes == 'float64' or input_col.dtypes == 'int64':
        return input_col
    else:
        return pd.to_numeric(input_col.str.replace(' ', '').str.replace(',',''))