# Adapted for use with weewx
#
#    $Revision$
#    $Date$
#
# This source code may be freely used, including for commercial purposes
# Steve Hatchett info@softwx.com
# http:#www.softwx.org/weather

"""
This file contains functions for performing various weather related calculations.

Notes about pressure
  Sensor Pressure           raw pressure indicated by the barometer instrument
  Station Pressure          Sensor Pressure adjusted for any difference between sensor elevation and official station elevation
  Field Pressure     (QFE)  Usually the same as Station Pressure
  Altimeter Setting  (QNH)  Station Pressure adjusted for elevation (assumes standard atmosphere)
  Sea Level Pressure (QFF)  Station Pressure adjusted for elevation, temperature and humidity

Notes about input parameters:
  currentTemp -   current instantaneous station temperature
  meanTemp -      average of current temp and the temperature 12 hours in
                  the past. If the 12 hour temp is not known, simply pass
                  the same value as currentTemp for the mean temp.
  humidity -      Value should be 0 to 100. For the pressure conversion
                  functions, pass a value of zero if you do not want to
                  the algorithm to include the humidity correction factor
                  in the calculation. If you provide a humidity value
                  > 0, then humidity effect will be included in the
                  calculation.
 elevation -     This should be the geometric altitude of the station
                  (this is the elevation provided by surveys and normally
                  used by people when they speak of elevation). Some
                  algorithms will convert the elevation internally into
                  a geopotential altitude.
  sensorElevation - This should be the geometric altitude of the actual
                  barometric sensor (which could be different than the
                  official station elevation).

Notes about Sensor Pressure vs. Station Pressure:
  SensorToStationPressure and StationToSensorPressure functions are based
  on an ASOS algorithm. It corrects for a difference in elevation between
  the official station location and the location of the barometetric sensor.
  It turns out that if the elevation difference is under 30 ft, then the
  algorithm will give the same result (a 0 to .01 inHg adjustment) regardless
  of temperature. In that case, the difference can be covered using a simple
  fixed offset. If the difference is 30 ft or greater, there is some effect
  from temperature, though it is small. For example, at a 100ft difference,
  the adjustment will be .13 inHg at -30F and .10 at 100F. The bottom line
  is that while ASOS stations may do this calculation, it is likely unneeded
  for home weather stations, and the station pressure and the sensor pressure
  can be treated as equivalent."""

import math

def FToC(v): 
    return (v - 32.0) * (5.0 / 9.0)

def CToF(v): 
    return (5.0/9.0)*v + 32.0

def CToK(v): 
    return v + 273.15

def KToC(v): 
    return v - 273.15

def FToR(v): 
    return v + 459.67

def RToF(v):
    return v - 459.67

def InToHPa(v):
    return v / 0.02953

def HPaToIn(v):
    return v * 0.02953

def FtToM(v):
    return v * 0.3048

def MToFt(v):
    return v / 0.3048

def InToMm(v): 
    return v * 25.4

def MmToIn(v): 
    return v / 25.4

def MToKm(v): # Miles !
    return v * 1.609344

def KmToM(v): # Miles !
    return v / 1.609344

def msToKmh(v):
    return v * 3.6

def Power10(y):
    return pow(10.0, y)

# This maps various Pascal functions to Python functions.
Power = pow
Exp   = math.exp
Round = round

class TWxUtils(object):

    gravity = 9.80665          # g at sea level at latitude 45.5 degrees in m/sec^2
    uGC = 8.31432              # universal gas constant in J/mole-K
    moleAir = 0.0289644        # mean molecular mass of air in kg/mole
    moleWater = 0.01801528     # molecular weight of water in kg/mole
    gasConstantAir = uGC/moleAir # (287.053) gas constant for air in J/kgK
    standardSLP = 1013.25      # standard sea level pressure in hPa
    standardSlpInHg = 29.921   # standard sea level pressure in inHg
    standardTempK = 288.15     # standard sea level temperature in Kelvin
    earthRadius45 = 6356.766   # radius of the earth at latitude 45.5 degrees in km
    
    standardLapseRate = 0.0065 # standard lapse rate (6.5C/1000m i.e. 6.5K/1000m)
    
    standardLapseRateFt = standardLapseRate * 0.3048 # (0.0019812) standard lapse rate per foot (1.98C/1000ft)
    vpLapseRateUS = 0.00275    # lapse rate used by Davis VantagePro (2.75F/1000ft)
    manBarLapseRate = 0.0117   # lapse rate from Manual of Barometry (11.7F/1000m, which = 6.5C/1000m)

    @staticmethod
    def StationToSensorPressure(pressureHPa, sensorElevationM, stationElevationM, currentTempC):
        # from ASOS formula specified in US units
        Result = InToHPa(HPaToIn(pressureHPa) / Power10(0.00813 * MToFt(sensorElevationM - stationElevationM) / FToR(CToF(currentTempC))))
        return Result

    @staticmethod
    def StationToAltimeter(pressureHPa, elevationM, algorithm='aaMADIS'):
        if algorithm == 'aaASOS':
            # see ASOS training at http://www.nwstc.noaa.gov
            # see also http://wahiduddin.net/calc/density_altitude.htm
            Result = InToHPa(Power(Power(HPaToIn(pressureHPa), 0.1903) + (1.313E-5 * MToFt(elevationM)), 5.255))

        elif algorithm == 'aaASOS2':
            geopEl = TWxUtils.GeopotentialAltitude(elevationM)
            k1 = TWxUtils.standardLapseRate * TWxUtils.gasConstantAir / TWxUtils.gravity # approx. 0.190263
            k2 = 8.41728638E-5 # (standardLapseRate / standardTempK) * (Power(standardSLP,  k1)
            Result = Power(Power(pressureHPa, k1) + (k2 * geopEl), 1/k1)

        elif algorithm == 'aaMADIS':
            # from MADIS API by NOAA Forecast Systems Lab, see http://madis.noaa.gov/madis_api.html
            k1 = 0.190284 # discrepency with calculated k1 probably because Smithsonian used less precise gas constant and gravity values
            k2 = 8.4184960528E-5 # (standardLapseRate / standardTempK) * (Power(standardSLP, k1)
            Result = Power(Power(pressureHPa - 0.3, k1) + (k2 * elevationM), 1/k1)

        elif algorithm == 'aaNOAA':
            # see http://www.srh.noaa.gov/elp/wxclc/formulas/altimeterSetting.html
            k1 = 0.190284 # discrepency with k1 probably because Smithsonian used less precise gas constant and gravity values
            k2 = 8.42288069E-5 # (standardLapseRate / 288) * (Power(standardSLP, k1SMT);
            Result = (pressureHPa - 0.3) * Power(1 + (k2 * (elevationM / Power(pressureHPa - 0.3, k1))), 1/k1)

        elif algorithm == 'aaWOB':
            # see http://www.wxqa.com/archive/obsman.pdf
            k1 = TWxUtils.standardLapseRate * TWxUtils.gasConstantAir / TWxUtils.gravity # approx. 0.190263
            k2 = 1.312603E-5 # (standardLapseRateFt / standardTempK) * Power(standardSlpInHg, k1)
            Result = InToHPa(Power(Power(HPaToIn(pressureHPa), k1) + (k2 * MToFt(elevationM)), 1/k1))

        elif algorithm == 'aaSMT':
            # see WMO Instruments and Observing Methods Report No.19 at http://www.wmo.int/pages/prog/www/IMOP/publications/IOM-19-Synoptic-AWS.pdf
            k1 = 0.190284 # discrepency with calculated value probably because Smithsonian used less precise gas constant and gravity values
            k2 = 4.30899E-5 # (standardLapseRate / 288) * (Power(standardSlpInHg, k1SMT));
            geopEl = TWxUtils.GeopotentialAltitude(elevationM)
            Result = InToHPa((HPaToIn(pressureHPa) - 0.01)
                             * Power(1 + (k2 * (geopEl / Power(HPaToIn(pressureHPa) - 0.01, k1))), 1/k1))

        else:
            raise ValueError("Unknown StationToAltimeter algorithm '%s'" % algorithm)
            
        return Result
  
    @staticmethod
    def StationToSeaLevelPressure(pressureHPa, elevationM,
                        currentTempC, meanTempC, humidity, 
                        algorithm = 'paManBar'):
        Result = pressureHPa * TWxUtils.PressureReductionRatio(pressureHPa, elevationM, currentTempC,
                                                               meanTempC, humidity, algorithm)
        return Result

    @staticmethod
    def SensorToStationPressure(pressureHPa, sensorElevationM, stationElevationM, currentTempC):
        # see ASOS training at http://www.nwstc.noaa.gov

        #from US units ASOS formula
        Result = InToHPa(HPaToIn(pressureHPa) * Power10(0.00813 * MToFt(sensorElevationM - stationElevationM)
                                                        / FToR(CToF(currentTempC))))
        return Result

    # still to do
    #class function TWxUtils.AltimeterToStationPressure(pressureHPa: TWxReal; elevationM: TWxReal;
    #                        algorithm: TAltimeterAlgorithm = DefaultAltimeterAlgorithm): TWxReal;
    #begin
    #end;
    #}

    @staticmethod
    def SeaLevelToStationPressure(pressureHPa, elevationM,
                        currentTempC, meanTempC, humidity, 
                        algorithm = 'paManBar'):
        Result = pressureHPa / TWxUtils.PressureReductionRatio(pressureHPa, elevationM, currentTempC,
                                                               meanTempC, humidity, algorithm)
        return Result

    @staticmethod
    def PressureReductionRatio(pressureHPa, elevationM,
                               currentTempC, meanTempC, humidity,
                               algorithm = 'paManBar'):
        if algorithm == 'paUnivie':
            #see http://www.univie.ac.at/IMG-Wien/daquamap/Parametergencom.html
            geopElevationM = TWxUtils.GeopotentialAltitude(elevationM)
            Result = Exp(((TWxUtils.gravity/TWxUtils.gasConstantAir) * geopElevationM)
               / (TWxUtils.VirtualTempK(pressureHPa, meanTempC, humidity) + (geopElevationM * TWxUtils.standardLapseRate/2)))

        elif algorithm == 'paDavisVp':
            #see http://www.exploratorium.edu/weather/barometer.html
            if (humidity > 0):
                hCorr = (9.0/5.0) * TWxUtils.HumidityCorrection(currentTempC, elevationM, humidity, 'vaDavisVP')
            else:
                hCorr = 0
            # In the case of DavisVp, take the constant values literally.
            Result = Power(10, (MToFt(elevationM) / (122.8943111 * (CToF(meanTempC) + 460 + (MToFt(elevationM) * TWxUtils.vpLapseRateUS/2) + hCorr))))

        elif algorithm == 'paManBar':
            # see WMO Instruments and Observing Methods Report No.19 at http://www.wmo.int/pages/prog/www/IMOP/publications/IOM-19-Synoptic-AWS.pdf
            # see WMO Instruments and Observing Methods Report No.19 at http://www.wmo.ch/web/www/IMOP/publications/IOM-19-Synoptic-AWS.pdf
            if (humidity > 0):
                hCorr = (9.0/5.0) * TWxUtils.HumidityCorrection(currentTempC, elevationM, humidity, 'vaBuck')
            else:
                hCorr = 0
            geopElevationM = TWxUtils.GeopotentialAltitude(elevationM)
            Result = Exp(geopElevationM * 6.1454E-2 / (CToF(meanTempC) + 459.7 + (geopElevationM * TWxUtils.manBarLapseRate / 2) + hCorr))
        
        else:
            raise ValueError("Unknown PressureReductionRatio algorithm '%s'" % algorithm)

        return Result

    @staticmethod
    def ActualVaporPressure(tempC, humidity, algorithm='vaBolton'):

        result = (humidity * TWxUtils.SaturationVaporPressure(tempC, algorithm)) / 100.0
        return result

    @staticmethod
    def SaturationVaporPressure(tempC, algorithm='vaBolton'):
        #see http://cires.colorado.edu/~voemel/vp.html   comparison of vapor pressure algorithms
        #see (for DavisVP) http://www.exploratorium.edu/weather/dewpoint.html
        if algorithm == 'vaDavisVp':
            Result = 6.112 * Exp((17.62 * tempC)/(243.12 + tempC)) # Davis Calculations Doc
        elif algorithm == 'vaBuck':
            Result = 6.1121 * Exp((18.678 - (tempC/234.5)) * tempC / (257.14 + tempC)) # Buck(1996)
        elif algorithm == 'vaBuck81':
            Result = 6.1121 * Exp((17.502 * tempC)/(240.97 + tempC)) # Buck(1981)
        elif algorithm == 'vaBolton':
            Result = 6.112 * Exp(17.67 * tempC / (tempC + 243.5)) # Bolton(1980)
        elif algorithm == 'vaTetenNWS':
            Result = 6.112 * Power(10,(7.5 * tempC / (tempC + 237.7))) #  Magnus Teten see www.srh.weather.gov/elp/wxcalc/formulas/vaporPressure.html
        elif algorithm == 'vaTetenMurray':
            Result = Power(10, (7.5 * tempC / (237.5 + tempC)) + 0.7858) # Magnus Teten (Murray 1967)
        elif algorithm == 'vaTeten':
            Result = 6.1078 * Power(10, (7.5 * tempC / (tempC + 237.3))) # Magnus Teten see www.vivoscuola.it/US/RSIGPP3202/umidita/attivita/relhumONA.htm
        else:
            raise ValueError("Unknown SaturationVaporPressure algorithm '%s'" % algorithm)
          
        return Result

    @staticmethod
    def MixingRatio(pressureHPa, tempC, humidity):
        k1 = TWxUtils.moleWater / TWxUtils.moleAir # 0.62198
        # see http://www.wxqa.com/archive/obsman.pdf
        # see also http://www.vivoscuola.it/US/RSIGPP3202/umidita/attiviat/relhumONA.htm
        vapPres = TWxUtils.ActualVaporPressure(tempC, humidity, 'vaBuck')
        Result = 1000 * ((k1 * vapPres) / (pressureHPa - vapPres))
        return Result

    @staticmethod
    def VirtualTempK(pressureHPa, tempC, humidity):
        epsilon = 1 - (TWxUtils.moleWater / TWxUtils.moleAir) # 0.37802
        # see http://www.univie.ac.at/IMG-Wien/daquamap/Parametergencom.html
        # see also http://www.vivoscuola.it/US/RSIGPP3202/umidita/attiviat/relhumONA.htm
        # see also http://wahiduddin.net/calc/density_altitude.htm
        vapPres = TWxUtils.ActualVaporPressure(tempC, humidity, 'vaBuck')
        Result = (CToK(tempC)) / (1-(epsilon * (vapPres/pressureHPa)))
        return Result

    @staticmethod
    def HumidityCorrection(tempC, elevationM, humidity,
                        algorithm='vaBolton'):
        vapPress = TWxUtils.ActualVaporPressure(tempC, humidity, algorithm)
        Result = (vapPress * ((2.8322E-9 * (elevationM**2)) + (2.225E-5 * elevationM) + 0.10743))
        return Result

    @staticmethod
    def GeopotentialAltitude(geometricAltitudeM):
        Result = (TWxUtils.earthRadius45 * 1000 * geometricAltitudeM) / ((TWxUtils.earthRadius45 * 1000) + geometricAltitudeM)
        return Result


#===============================================================================
#                              class TWxUtilsUS
#===============================================================================

class TWxUtilsUS(object):

    """This class provides US unit versions of the functions in uWxUtils.
    Refer to uWxUtils for documentation. All input and output
    paramters are in the following US units:
        pressure in inches of mercury
        temperature in Fahrenheit
        wind in MPH
        elevation in feet"""

    @staticmethod
    def StationToSensorPressure(pressureIn, sensorElevationFt, stationElevationFt, currentTempF):
        Result = pressureIn / TWxUtils.Power10(0.00813 * (sensorElevationFt - stationElevationFt)
                                               / TWxUtils.FToR(currentTempF))
        return Result

    @staticmethod
    def StationToAltimeter(pressureIn, elevationFt, 
                        algorithm='aaMADIS'):
        Result = TWxUtils.HPaToIn(TWxUtils.StationToAltimeter(TWxUtils.InToHPa(pressureIn),
                        FtToM(elevationFt), algorithm))
        return Result

    @staticmethod
    def StationToSeaLevelPressure(pressureIn, elevationFt,
                        currentTempF, meanTempF, humidity,
                        algorithm='paManBar'):
        Result = pressureIn * TWxUtils.PressureReductionRatio(pressureIn, elevationFt,
                        currentTempF, meanTempF, humidity, algorithm)
        return Result

    @staticmethod
    def SensorToStationPressure(pressureIn,
                           sensorElevationFt, stationElevationFt,
                           currentTempF):
        Result = pressureIn * TWxUtils.Power10(0.00813 * (sensorElevationFt - stationElevationFt)
                                       / TWxUtils.FToR(currentTempF))
        return Result

    @staticmethod
    def AltimeterToStationPressure(pressureIn, elevationFt,
                        algorithm='aaMADIS'):
        Result = TWxUtils.AltimeterToStationPressure(TWxUtils.InToHPa(pressureIn),
                        TWxUtils.FtToM(elevationFt), algorithm)
        return Result

    @staticmethod
    def SeaLevelToStationPressure(pressureIn, elevationFt,
                        currentTempF, meanTempF, humidity,
                        algorithm='paManBar'):
        Result = pressureIn / TWxUtils.PressureReductionRatio(pressureIn, elevationFt,
                        currentTempF, meanTempF, humidity, algorithm)
        return Result

    @staticmethod
    def PressureReductionRatio(pressureIn, elevationFt,
                        currentTempF, meanTempF, humidity,
                        algorithm='paManBar'):
        Result = TWxUtils.PressureReductionRatio(TWxUtils.InToHPa(pressureIn),
                        TWxUtils.FtToM(elevationFt), TWxUtils.FToC(currentTempF),
                        TWxUtils.FToC(meanTempF), humidity, algorithm)
        return Result

    @staticmethod
    def ActualVaporPressure(tempF, humidity,
                        algorithm='vaBolton'):
        Result = (humidity * TWxUtils.SaturationVaporPressure(tempF, algorithm)) / 100
        return Result

    @staticmethod
    def SaturationVaporPressure(tempF,
                        algorithm='vaBolton'):
        Result = TWxUtils.HPaToIn(TWxUtils.SaturationVaporPressure(TWxUtils.FToC(tempF), algorithm))
        return Result

    @staticmethod
    def MixingRatio(pressureIn, tempF, humidity):
        Result = TWxUtils.HPaToIn(TWxUtils.MixingRatio(TWxUtils.InToHPa(pressureIn),
                    TWxUtils.FToC(tempF), humidity))
        return Result

    @staticmethod
    def HumidityCorrection(tempF, elevationFt, humidity,
                        algorithm='vaBolton'):
        Result = TWxUtils.HumidityCorrection(TWxUtils.FToC(tempF), TWxUtils.FtToM(elevationFt),
                    humidity, algorithm)
        return Result

    @staticmethod
    def GeopotentialAltitude(geometricAltitudeFt):
        Result = TWxUtils.MToFt(TWxUtils.GeopotentialAltitude(TWxUtils.FtToM(geometricAltitudeFt)))
        return Result

#===============================================================================
#                              class TWxUtilsVP
#===============================================================================

class uWxUtilsVP(object):
    """ This class contains functions for calculating the raw sensor pressure of a
    Vantage Pro weather station from the sea level reduced pressure it provides.
    The sensor pressure can then be used to calcuate altimeter setting using
    other functions in the uWxUtils and uWxUtilsUS units.
    
    notes about input parameters:
      currentTemp -   current instantaneous station temperature
      temp12HrsAgoF - temperature from 12 hours ago. If the 12 hour temp is
                      not known, simply pass the same value as currentTemp
                      for the 12 hour temp. For the vantage pro sea level
                      to sensor pressure conversion, the 12 hour temp
                      should be the hourly temp that is 11 hours to 11:59
                      in the past. For example, if the current time is
                      3:59pm, use the 4:00am temp, and if it is currently
                      4:00pm, use the 5:00am temp. Also, the vantage pro
                      seems to use only whole degree temp values in the sea
                      level calculation, so the function performs rounding
                      on the temperature.
      meanTemp -      average of current temp and the temperature 12 hours in
                      the past. If the 12 hour temp is not known, simply pass
                      the same value as currentTemp for the mean temp. For the
                      Vantage Pro, the mean temperature should come from the
                      BARDATA.VirtualTemp. The value in BARDATA is an integer
                      (whole degrees). The vantage pro calculates the mean by
                      Round(((Round(currentTempF - 0.01) + Round(temp12HrsAgoF - 0.01)) / 2) - 0.01);
      humidity -      Value should be 0 to 100. For the pressure conversion
                      functions, pass a value of zero if you do not want to
                      the algorithm to include the humidity correction factor
                      in the calculation. If you provide a humidity value
                      > 0, then humidity effect will be included in the
                      calculation.
      elevation -     This should be the geometric altitude of the station
                      (this is the elevation provided by surveys and normally
                      used by people when they speak of elevation). Some
                      algorithms will convert the elevation internally into
                      a geopotential altitude."""

    # this function is used if you have access to BARDATA (see Davis Serial docs)
    # meanTempF is from BARDATA.VirtualTemp
    # humidityCorr is from BARDATA.C (remember to first divide C by 10)
    @staticmethod
    def SeaLevelToSensorPressure_meanT(pressureIn, elevationFt,
                               meanTempF, humidityCorr):
        Result = TWxUtilsUS.SeaLevelToStationPressure(pressureIn, elevationFt, meanTempF,
                                  meanTempF + humidityCorr, 0, 'paDavisVp')
        return Result

    # this function is used if you do not have access to BARDATA. The function
    # will internally calculate the mean temp and the humidity correction
    # the would normally come from the BARDATA.
    # currentTempF is the value of the current sensor temp
    # temp12HrsAgoF is the temperature from 12 hours ago (see comments on
    #           temp12Hr from earlier in this document for more on this).
    @staticmethod
    def SeaLevelToSensorPressure_12(pressureIn, elevationFt,
                                    currentTempF, temp12HrsAgoF,
                                    humidity):
        Result = TWxUtilsUS.SeaLevelToStationPressure_metanT(pressureIn, elevationFt, currentTempF,
                                    Round(((Round(currentTempF - 0.01) + Round(temp12HrsAgoF - 0.01)) / 2) - 0.01),
                                    humidity, 'paDavisVp')
        return Result
