#!/usr/bin/env python
# coding: utf-8
#update python at 2019-05-31
#from __future__ import division
import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import pandas as pd
import datetime as dt
import numpy as np
import math
from datetime import datetime, timedelta
import json
#constant
converge = 0.05
stefanb = 5.6696E-8 # Stefan-Boltzmann constant

alb_wick = 0.4
alb_sfc = 0.25
alb_globe = 0.05

emis_wick = 0.95
emis_sfc = 0.999
emis_globe = 0.95

diamGlobe = 0.0508  # diameter of globe bulb
diamWick = 0.007    # diameter of wet bulb
lenWick = 0.0254 # length of wet bulb

fdir_fix = 0.67

M_air = 28.97
M_H2O = 18.015

Cp = 1003.5 #specific heat capacity, J/kg-K
R_gas = 8314.34 #J/kg mol-K

MinWindSpeed = 0.1 # if wind speed less than 0.1 m/s
AtmPressure = 1013.25 #kPa

time_col = "DataTime"
time_col_local = "Local_DataTime"
lon_col ="lon"
lat_col = "lat"
airpressure_col = "airpressure"
Ta_col = "Temperature"
RH_col = "RH"
solar_col = "solar"
ws_col = "WS"

# =================
# Based on iso 7243 to predict the temperature of a black globe of 150 mm diameter, tg150,
# from the temperature, tgd, of a black globe of diameter, d, in millimetres
def fISO7243_globe150(row):
    _ret = np.nan
    Ta = row[Ta_col]
    Tg = row['globe_bulb_50mm']
    speed = row[ws_col]
    if np.isnan(Ta)|np.isnan(Tg)|np.isnan(speed):
        return _ret
    tg150 = Ta + (1 + 1.13 * (speed ** 0.6) * ((diamGlobe) ** -0.4 ) ) * ( Tg - Ta ) / (1 + 2.41 * (speed ** 0.6))
    return tg150
# =================

def data_column_value(data):
    columnNames=list(data.columns.values)
    return columnNames

def time_convert(row, time_interval,DateTime_format):
    data_time = dt.datetime.strptime(row, DateTime_format)
    data_time = data_time + time_interval  # modified at 2019/07/30
    year = data_time.year
    mon = data_time.month
    day = data_time.day
    hr = data_time.hour
    minute = data_time.minute
    sec = data_time.second
    day_in_year = data_time.timetuple().tm_yday
    return year, mon, day, hr, minute, sec, day_in_year

# check if the year is a leap year or not.
def fLeap(year):
    if ((year % 4 == 0 and year % 100 != 0) or (year % 400 == 0 and year % 4000 != 0)):
        # print("leap year")
        return True
    else:
        # print("not leap year")
        return False

#https://www.esrl.noaa.gov/gmd/grad/solcalc/solareqns.PDF
def solar_zenith(row):
    lon = row['lon']
    lat = row['lat']
    year = row['year']
    hr = row['hr']
    minute = row['minute']
    sec = row['second']
    day_in_year = row['day_in_year']

    if fLeap(year):
        days_the_year = 366
    else:
        days_the_year = 365

    gamma = (2 * math.pi / days_the_year) * ((day_in_year - 1) + (hr - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma) - 0.014615 * math.cos(
        2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = 0.006918 - (0.399912 * math.cos(gamma)) + 0.070257 * math.sin(gamma) - 0.006758 * math.cos(
        2 * gamma) + 0.000907 * math.sin(2 * gamma) - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)
    time_offset = eqtime - 4 * lon + 60 * row['timezone']
    tst = hr * 60 + minute + sec / 60 + time_offset
    ha = (tst / 4) - 180  # The solar hour angle, in degrees
    zenith = math.degrees(math.acos(((math.sin(math.radians(lat)) * math.sin(decl)) + (
                math.cos(math.radians(lat)) * math.cos(decl) * math.cos(math.radians(ha))))))
    return zenith

# reference Liljegren et al.(2008) eq.13 & eq.14
def solar_fdir(row, solar_col=solar_col):
    zenith = row['solar_zenith']
    if (row[solar_col] == 0 or row[solar_col] == ''):
        solar = 0.00001  # default is 0, modified at 20190527
    else:
        solar = row[solar_col]
    if zenith <= 89.5:
        solarmax = 1367 * math.cos(math.radians(zenith)) / (1) ** 2
        fdir = math.exp(3 - 1.34 * (solar / solarmax) - 1.65 / (solar / solarmax))
        fdir = max(min(fdir, 0.9), 0.0)  # reference raw code from wbgt.c
    else:
        fdir = 0
    return fdir

# Calculation of dew point from RH
def fTd(Ta, RH):
    RHD = RH / 100
    fTd = 237.3 * (math.log(RHD, math.exp(1)) / 17.27 + Ta / (237.3 + Ta)) / (
                1 - math.log(RHD, math.exp(1)) / 17.27 - Ta / (237.3 + Ta))  # Gornicki et al., 2017
    return fTd

#  Purpose: Compute the viscosity of air, kg/(m s) given temperature, K
#  Reference: BSL
def viscosity(Tair):
    _ret = np.nan
    Tr = Tair / 97  # ε/K =97 in Air of Table E.1
    if Tr <= 3:
        omega = 1.6214 * (Tr) ** (-0.456)  # Table E.2
    else:
        omega = 1.2083 * (Tr) ** (-0.16)  # Table E.2
    _ret = 0.0000026693 * (28.97 * Tair) ** 0.5 / (3.617 ** 2 * omega)  # Reference: BSL, page 278, kg/(m-s)
    return _ret

#  Purpose: calculate the saturation vapor pressure (mb) over liquid water given the temperature (K).
#  Reference: Buck's (1981) approximation (eqn 3) of Wexler's (1976) formulae.
#  over liquid water
def esat(Tk, Pair):
    _ret = np.nan
    _ret = 6.1121 * np.exp(17.502 * (Tk - 273.15) / (
                Tk - 32.18))  # eq(8), ew=[1.0007+(3.46E-6*P)]*6.1121*exp((17.502*T)/(240.97+T)) P:mb, 1 hPa=1 mba; T: degree C
    _ret = (1.0007 + (
                3.46E-6 * Pair)) * _ret  # correction for moist air, if pressure is not available; for pressure > 800 mb
    return _ret

#  Reference: Oke (2nd edition), page 373., P: hPa
def emis_atm(Ta, RH, Pair):
    _ret = np.nan
    e = RH * esat(Ta, Pair)
    _ret = 0.575 * e ** (1 / 7)
    return _ret

#  Purpose: compute the diffusivity of water vapor in air, m2/s
#  Reference: BSL, page 521.
def diffusivity(Tair, Pair):
    _ret = np.nan
    pcrit13 = (36.4 * 218.3) ** (
                1 / 3)  # Air at Table E.1; H2O at Table A.2, Fundamentals of Thermodynamics 6 ed. 1MPa =  9.8692326671601 atm (1 atm = 1013.25 hPa)
    tcrit512 = (132 * 647.3) ** (5 / 12)  # Table E.1
    Tcrit12 = (132 * 647.3) ** 0.5  # Table E.1
    Mmix = (1 / M_air + 1 / M_H2O) ** 0.5
    _ret = 0.000364 * (Tair / Tcrit12) ** 2.334 * pcrit13 * tcrit512 * Mmix / (Pair / 1013.25) * 0.0001
    return _ret

#  Purpose: to calculate the convective heat tranfer coefficient for flow around a sphere.
#  Reference: Bird, Stewart, and Lightfoot (BSL).
def h_sphere_in_air(Tair, Pair, speed):
    _ret = np.nan
    Rair = R_gas / M_air
    Pr = Cp / (Cp + 1.25 * Rair)  # BSL, page 276
    thermal_con = (Cp + 1.25 * R_gas / M_air) * viscosity(Tair)  # BSL, page 276
    density = Pair * 100 / (Rair * Tair)  # kg/m3
    if speed < MinWindSpeed:
        speed = MinWindSpeed
    Re = speed * density * diamGlobe / viscosity(Tair)
    Nu = 2 + 0.6 * Re ** 0.5 * Pr ** (1 / 3)  # reference Liljegren eq. 16
    _ret = Nu * thermal_con / diamGlobe  # W/(m2 K)
    return _ret

#  Purpose: to calculate the convective heat transfer coefficient for a long cylinder in cross flow.
#  Reference: Bedingfield and Drew, eqn 32
#  Author:  James C. Liljegren
#       Decision and Information Sciences Division
#       Argonne National Laboratory
#
def h_cylinder_in_air(Tair, Pair, speed):
    _ret = np.nan
    Rair = R_gas / M_air
    Pr = Cp / (Cp + 1.25 * Rair)  # Euken formula; BSL, page 276
    thermal_con = (Cp + 1.25 * R_gas / M_air) * viscosity(Tair)  # Euken formula; BSL, page 276
    density = Pair * 100 / (Rair * Tair)
    if speed < MinWindSpeed:
        speed = MinWindSpeed
    Re = speed * density * diamWick / viscosity(Tair)
    Nu = 0.281 * Re ** 0.6 * Pr ** 0.44  # reference Liljegren eq. 10
    _ret = Nu * thermal_con / diamWick
    return _ret

# find natural wet bulb temperature
# def fTwb(row,  airpressure_col=airpressure_col, Ta_col=Ta_col, RH_col=RH_col,solar_col=solar_col, ws_col=ws_col):
def fTwb(row):
    _ret = np.nan
    global alb_sfc, fdir
    # global alb_sfc
    Pair = row[airpressure_col]
    Ta = row[Ta_col]
    relh = row[RH_col]
    solar = row[solar_col]
    speed = row[ws_col]
    zenith = row['solar_zenith']
    fdir = row['fdir']
    ratio = Cp * M_air / M_H2O
    Pr = Cp / (Cp + (1.25 * R_gas / M_air))
    Td = fTd(Ta, relh)  # calculate dewpoint temp

    if np.isnan(Ta)|np.isnan(relh)|np.isnan(solar)|np.isnan(speed):
        print('fTwb error: Temp or RH or solar or wind speed is empty at row %s'%(row.name+2))
        return _ret

    # Check to make sure Td < Ta
    if Td > Ta:
        if Td-Ta > 0.1:
            print('fTwb error: Td-Ta > 0.1 at row %s' % (row.name + 2))
            return _ret
        else:
            Td = Ta

    try:
        alb_sfc = row['surface_albedo']
    except:
        pass

    try:
        if (row['variable_fdir'] == 'Yes') | (row['variable_fdir'] == 'yes') | (
                row['variable_fdir'] == 'Y') | (row['variable_fdir'] == 'y'):
            pass
        else:
            fdir = fdir_fix
    except:
        fdir = fdir_fix

    if zenith<=89.5:    #modified at 2019/07/30
        zenith = zenith
    else:
        zenith = 89.5

    Tdew = Td + 273.15
    Tair = Ta + 273.15
    RH = relh * 0.01

    eair = RH * esat(Tair, Pair)
    emis_at = emis_atm(Tair, RH, Pair)  # reference Liljegren et al.(2008)

    Tsfc = Tair
    Twb_prev = Tdew  # First guess is the dew point temperature

    # Do iteration
    testno = 1
    while (testno <= 1000):
        evap = (313.15 - Twb_prev) / 30 * (
            -71100) + 2407300  # 'reference Table C.14, Combustion book, at 10-40C(283-313K)
        h = h_cylinder_in_air(Twb_prev, Pair, speed)
        #         Fatm = stefanb * emis_wick *  ( 0.5 *  ( emis_at * Tair ** 4 + emis_sfc * Tsfc ** 4 ) - Twb_prev ** 4 )  +  ( 1 - alb_wick )  * solar *  ( ( 1 - fdir )  *  ( 1 + 0.25 * diamWick / lenWick )  +  ( ( math.tan(math.radians(zenith)) / math.pi )  + 0.25 * diamWick / lenWick )  * fdir + alb_sfc )
        Fatm = stefanb * emis_wick * (0.5 * (emis_at * Tair ** 4 + emis_sfc * Tsfc ** 4) - Twb_prev ** 4) + (
                    1 - alb_wick) * solar * ((1 - fdir) * (1 + 0.25 * diamWick / lenWick) + (
                    (math.sin(math.radians(zenith)) / math.pi) + 0.25 * math.cos(
                math.radians(zenith)) * diamWick / lenWick) * fdir + alb_sfc)

        ewick = esat(Twb_prev, Pair)
        density = Pair * 100 / (Twb_prev * R_gas / M_air)
        Sc = viscosity(Twb_prev) / (density * diffusivity(Twb_prev, Pair))
        Twb = Tair - evap / ratio * (ewick - eair) / (Pair - ewick) * (Pr / Sc) ** 0.56 + Fatm / h
        dT = Twb - Twb_prev

        if abs(dT) < converge:
            _ret = Twb - 273.15
            return _ret
        else:
            Twb_prev = (0.9 * Twb_prev + 0.1 * Twb)
            testno += 1
    print('fTwb error: Twb No convergence at row %s' % (row.name + 2))
    return _ret

# find globe temperature : black globe temp
#  Purpose: to calculate the globe temperature
#  Author:  James C. Liljegren
#       Decision and Information Sciences Division
#       Argonne National Laboratory
# Pressure in kPa (Atm =101 kPa)
# def fTg(row, airpressure_col=airpressure_col, Ta_col=Ta_col, RH_col=RH_col,solar_col=solar_col, ws_col=ws_col):
def fTg(row):
    _ret = np.nan
    global alb_sfc
    Pair = row[airpressure_col]
    Ta = row[Ta_col]
    relh = row[RH_col]
    solar = row[solar_col]
    speed = row[ws_col]
    zenith = row['solar_zenith']
    fdir = row['fdir']

    if np.isnan(Ta)|np.isnan(relh)|np.isnan(solar)|np.isnan(speed):
        print('fTg error: Temp or RH or solar or wind speed is empty at row %s'%(row.name+2))
        return _ret

    try:
        alb_sfc = row['surface_albedo']
    except:
        pass
###  midified at 20190910
    try:
        if (row['variable_fdir'] == 'Yes') | (row['variable_fdir'] == 'yes') | (
                row['variable_fdir'] == 'Y') | (row['variable_fdir'] == 'y'):
            pass
        else:
            fdir = fdir_fix
    except:
        fdir = fdir_fix

    Tair = Ta + 273.15
    RH = relh * 0.01
    Tsfc = Tair
    Tglobe_prev = Tair

    testno = 1

    while (testno <= 1000):
        h = h_sphere_in_air(Tglobe_prev, Pair, speed)
        #         Tglobe = ( 0.5 *  ( emis_atm(Tair, RH, Pair) * Tair ** 4 + emis_sfc * Tsfc ** 4 )  - h /  ( emis_globe * stefanb )  *  ( Tglobe_prev - Tair )  + solar /  ( 2 * emis_globe * stefanb )  *  ( 1 - alb_globe )  *  ( fdir *  ( 1 /  ( 2 * cza )  - 1 )  + 1 + alb_sfc ) )  ** 0.25
        Tglobe = (0.5 * (emis_atm(Tair, RH, Pair) * Tair ** 4 + emis_sfc * Tsfc ** 4) - h / (emis_globe * stefanb) * (
                    Tglobe_prev - Tair) + solar / (2 * emis_globe * stefanb) * (1 - alb_globe) * (
                              fdir * (1 / 2 - 1) + 1 + alb_sfc)) ** 0.25
        dT = Tglobe - Tglobe_prev

        if abs(dT) < converge:
            _ret = Tglobe - 273.15
            return _ret
        else:
            Tglobe_prev = (0.9 * Tglobe_prev + 0.1 * Tglobe)
            testno += 1
    print('fTg error: Tg No convergence at row %s' % (row.name + 2))

# WBGT outside, time_colm=time_col, lon_col=lon_col, lat_col=lat_col
def fWBGTo(data):
    if airpressure_col in data.columns:
        data[airpressure_col] = data[airpressure_col].fillna(AtmPressure)
    else:
        data[airpressure_col] =AtmPressure
    df = pd.DataFrame(data,columns=data_column_value(data))
    #DateTime_format = data['DateTime_format'][0]
    time_series = df[time_col_local].apply(lambda row: dt.datetime.strptime(row, "%Y/%m/%d %H:%M:%S"))  #modified at 2019/08/
    #print(data['data_avg'][0])
    if data['data_avg'][0] == "Y":
        time_interval = (time_series[1]-time_series[0])/2  #calculate solar angle for average data #modified at 2019/07/30
    else:
        time_interval = (time_series[1]-time_series[1])
    #print(time_interval)
    data_time = pd.DataFrame(list(df[time_col_local].apply(time_convert, time_interval=time_interval,DateTime_format="%Y/%m/%d %H:%M:%S")),
                             columns=['year', 'mon', 'day', 'hr', 'minute', 'second',
                                      'day_in_year'])  # modified at 2019/07/30
    # print(data_time)
    # print(df)
    df = pd.concat([df,data_time], axis=1)#, join_axes=[df.index])
    # zenith
    zenith = pd.DataFrame(list(df.apply(solar_zenith, axis=1)), columns=['solar_zenith'])
    df = pd.concat([df, zenith], axis=1)#, join_axes=[df.index])
    # fdir
    fdir = pd.DataFrame(list(df.apply(solar_fdir, axis=1)), columns=['fdir'])
    df = pd.concat([df, fdir], axis=1)#, join_axes=[df.index])
    #print(df)

    #WBGT calculation
    dry_bulb = df[Ta_col]
    data['wet_bulb'] =round((pd.DataFrame(list(df.apply(fTwb, axis=1)))), 2)
    data['globe_bulb_50mm'] = round((pd.DataFrame(list(df.apply(fTg, axis=1)))), 2)
    data['globe_bulb_150mm'] = round((pd.DataFrame(list(data.apply(fISO7243_globe150, axis=1)))), 2)
    data['WBGTo']=round(( 0.7 * data['wet_bulb'] + 0.2 * data['globe_bulb_150mm'] + 0.1 * dry_bulb), 2)

    #del data['data_avg']
    #del data['DateTime_format']
    #del data['Local_DataTime']
    #del data['variable_fdir']
    #del data['timezone']


    # #return the original data to get all data and cal Tw, Tg and WBGT from input data
    #Set lat, lon and airpressure as default, will not save default value to dataframe
    #modified at 20190528
    #print(data)
    return data


#CurrentPath=os.path.abspath(os.path.dirname(__file__))
#filename = '000.csv'
#data = pd.read_csv(os.path.join(CurrentPath, filename),header=0, index_col=False)
#calData=fWBGTo(data)
#print(calData)
#calData.to_csv(path_or_buf=os.path.join(CurrentPath, filename), index=False, header=True)





