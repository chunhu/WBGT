import sys
sys.path.append('/home/chunhu/PycharmProjects/MyPythonCode/')
import os
from Cal_WBGT_20190910_01.my_lib import find_filenames, csv_col_to_numeric
import pandas as pd
import numpy as np
from Cal_WBGT_20190910_01.create_folder import Create_folder
import json
from datetime import datetime, timedelta
from WBGT.wbgt_lib import fWBGTo
pd.set_option('display.max_columns', None)

CurrentPath=os.path.abspath(os.path.dirname(__file__))
Create_folder("CSV_data")
Create_folder("WBGT_data")
Create_folder("CSV_data_BK")

CSV_data=os.path.join(CurrentPath, "CSV_data")
CSV_data_BK=os.path.join(CurrentPath, "CSV_data_BK")
WBGT_data=os.path.join(CurrentPath, "WBGT_data")
WBGT_data_BK=os.path.join(CurrentPath, "WBGT_data_BK")
WBGT_data_ER=os.path.join(CurrentPath, "WBGT_data_ER")
titles_file=os.path.join(CurrentPath, "config.json")


with open(titles_file, 'r') as f:
    titles = json.load(f)
    time_col = titles[1]['time']
    DateTime_format_col=titles[1]['DateTime_format']
    time_col_local = titles[1]['time']+'_local' #Datatime column of localtime 20190531
    lon_col = titles[1]['lon']
    lat_col = titles[1]['lat']
    airpressure_col = titles[1]['airpressure']
    Ta_col = titles[1]['Ta']
    RH_col = titles[1]['RH']
    solar_col = titles[1]['solar']
    ws_col = titles[1]['ws']
    timezone=titles[1]['TimeZone']
    localtime=titles[1]['localtime']
    alb_sfc_col = titles[1]['alb_sfc']
    center_lon=titles[1]['lon_center']
    center_lat = titles[1]['lat_center']
    data_avg = titles[1]['data_avg']
    variable_fdir = titles[1]['variable_fdir']
    center_lat_col = center_lat
    center_lon_col = center_lon
    #DateTime_format_col=titles[1]['DateTime_format']






#get CSV file list
csv_files=find_filenames(CSV_data, "csv")
csv_files.sort()
#print(CSVFile)
current_path = os.path.dirname(os.path.abspath(__file__))

def TimeZone_check(row):
    try:
        data_time = datetime.strptime(row, DateTime_format_col)
    except Exception as e:
        print("Please check the DataTime format %s"%e)
    if localtime == "Yes":
        data_time = datetime.strftime(data_time, "%Y/%m/%d %H:%M:%S")
    else:
        data_time = data_time + timedelta(hours=timezone)
        data_time = datetime.strftime(data_time, "%Y/%m/%d %H:%M:%S")
    return str(data_time)


def nantonone(input_col):
    if np.isnan(input_col):
        input_col=''
    else:
        pass
    return input_col

def check_column(oldName, newName,datafile):
    if oldName in datafile.columns:
       newName
    return newName

def del_column(ColumnName,dataframe1,dataframe2):
    if ColumnName in dataframe1.columns:
        pass
    else:
        del dataframe2.ColumnName


def Cal_WBGT(csvfiles,CSV_data):
    for f in csvfiles:
        try:
            datafile = pd.read_csv(CSV_data+'/'+f, header=0, index_col=False)
            WBGT=datafile.copy()
            datafile[time_col_local] = datafile[time_col].apply(TimeZone_check)
            datafile[Ta_col] = csv_col_to_numeric(datafile[Ta_col])
            datafile[RH_col] = csv_col_to_numeric(datafile[RH_col])
            datafile[solar_col] = csv_col_to_numeric(datafile[solar_col])
            datafile[ws_col] = csv_col_to_numeric(datafile[ws_col])
            if lon_col in datafile.columns:
                datafile[lon_col] = datafile[lon_col].fillna(center_lon_col)
            else:
                datafile[lon_col] =center_lon_col

            if lat_col in datafile.columns:
                datafile[lat_col] = datafile[lat_col].fillna(center_lat_col)
            else:
                datafile[lat_col] =center_lat_col
            datafile['data_avg']=data_avg
            datafile['variable_fdir']=variable_fdir
            datafile['DateTime_format']=DateTime_format_col
            datafile['timezone']=timezone

            datafile.rename({
                time_col: "DataTime",
                time_col_local: "Local_DataTime",
                Ta_col: "Temperature",
                RH_col: "RH",
                solar_col: "solar",
                ws_col: "WS",
                airpressure_col:check_column(airpressure_col,"airpressure",datafile),
                alb_sfc_col: check_column(alb_sfc_col,"surface_albedo",datafile),
                data_avg:'data_avg'

            }, axis='columns', inplace=True)
            #print(WBGT)
            print("Cal WBGT : ", f)
            WBGT_f = fWBGTo(datafile)
            WBGT['wet_bulb']=WBGT_f['wet_bulb']
            WBGT['globe_bulb']=WBGT_f['globe_bulb']
            WBGT['WBGTo']=WBGT_f['WBGTo']
            print(WBGT)
            WBGT.to_csv(WBGT_data + "/" + f + ".csv", mode='w+', index=False)


        except Exception as e:
            print("data error: ",e)


if __name__ == '__main__':
    Cal_WBGT(csv_files,CSV_data)