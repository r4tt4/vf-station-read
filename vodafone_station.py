#!/usr/bin/python3
#
# enhanced for IP, PW as ARG.
# some parse fixes
# hardcoded GERMAN language, caused by my german VF Station.
# new supported OFDMA Upload Channel.
# tested with Firmware-Version: 01.02.068.11.EURO.SIP

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from array import *

import argparse

# Get password given as argument
parser = argparse.ArgumentParser()
parser.add_argument("ipadr", help="The IP address of the Vodafone Station")
parser.add_argument("password", help="Vodafone Station web interface password")
args = parser.parse_args()

# Connection parameters
router_adr = args.ipadr
router_pwd = args.password
#router_pwd = "<PW>"
#router_adr = "<IP>"

# open Firefox in headless mode and connect to Vodafone Station
options = Options()
options.headless = True                         # DEBUG : Turn to False to see the browser
driver = webdriver.Firefox(options=options)
driver.get ("http://"+router_adr)
#driver.get ("http://"+router_adr+"/?status_docsis")

# fill password field with password and clicl on "Log In" (user field is prefilled with "admin" and inactive on Vodafone Station (Arris TG3442DE)
#driver.switchTo().frame(1);
WebDriverWait(driver, 4000).until(EC.presence_of_element_located((By.XPATH, "//*[@id='language-info']")))
driver.find_element_by_id("Password").send_keys(router_pwd)
driver.find_element_by_xpath("//input[@type='button']").click() 
#driver.switchTo().defaultContent();

# go to Docsis status page after login
driver.get ("http://"+router_adr+"/?status_docsis")

#driver.switchTo().frame(0);
# wait for page being built up (i.e the usTable being present)
WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='usTable']")))

# grab number of rows and columns in dsTable (downstream)
ds_rows = ( len(driver.find_elements_by_xpath("//*[@id='dsTable']/tbody/tr")) )
ds_cols = int( len(driver.find_elements_by_xpath("//*[@id='dsTable']/tbody/tr/th")) / ds_rows )

# grab number of rows and columns in usTable (upstream)
us_rows = ( len(driver.find_elements_by_xpath("//*[@id='usTable']/tbody/tr")) )
us_cols = int( len(driver.find_elements_by_xpath("//*[@id='usTable']/tbody/tr/th")) / us_rows )


# grab raw DSTABLE data
# create string storage array for raw data
ds_raw_data = [["" for x in range(ds_cols)] for y in range(ds_rows)] 


# sweep each line and copy data in raw data array
# HTML table and array starts with 1

for html_row in range(1, ds_rows+1):
    for html_col in range(1, ds_cols+1):
        ds_raw_data[(html_row-1)][(html_col-1)] = driver.find_element_by_xpath("//*[@id='dsTable']/tbody/tr[%d]/th[%d]" % (html_row,html_col)).text


# grab raw USTABLE data
# create string storage array for raw data
us_raw_data = [["" for x in range(us_cols)] for y in range(us_rows)] 


# sweep each line and copy data in raw data array
# HTML table and array starts with 1

for html_row in range(1, us_rows+1):
    for html_col in range(1, us_cols+1):
        us_raw_data[(html_row-1)][(html_col-1)] = driver.find_element_by_xpath("//*[@id='usTable']/tbody/tr[%d]/th[%d]" % (html_row,html_col)).text


# close browser instance before further processing
driver.quit()

# start sorting and processing the extracted DOWNSTREAM data

# preparing storage array for processing
# data map:
# Channel (int)   Frequency(int)    Chan.Typ(string)    Modulation(string)      Rx.Power_dBmV(float)    Rx.Power_dBµV(float)    SNR_dB(float)   LockStatus(bool)

ds_data = []
ds_data_line = [0,0,"","",0.00,0.00,0.00,False]

# searching the max channel Nr. which was grabbed
ds_channel_max = 0

for array_row in range(0,len(ds_raw_data)-1):
    if int(ds_raw_data[array_row][0]) > ds_channel_max:
        ds_channel_max = int(ds_raw_data[array_row][0])


# starting channel scanning between 1 and channel max
channel = 1

while channel <= ds_channel_max:
     
    # start with the first line when searching for the actual channel
    array_row = 0

    # sweeping the raw data until reached the last line
    while array_row <= (len(ds_raw_data)-1):

        # look the actual line if searched channel is present (convert value as an int because having beeing grabed as a string)
        if int(ds_raw_data[array_row][0]) == channel:
            
            # clearing data line
            ds_data_line = [0,0,"","",0.00,0.00,0.00,False]
            
            # copy channel number
            ds_data_line[0] = int(ds_raw_data[array_row][0])
            
            # copy frequency
            # if ODFM band extract channel boundaries from "XXX~XXX" format and compute central frequency
            if ds_raw_data[array_row][1] == "OFDM":
                ofdm_freq_band = ds_raw_data[array_row][2].split("~")
                ds_data_line[1] = int((int(ofdm_freq_band[0])+int(ofdm_freq_band[1]))/2)
            else:
            # SC-QAM band or other
                ds_data_line[1] = int(ds_raw_data[array_row][2])
            
            # copy channel type
            ds_data_line[2] = ds_raw_data[array_row][1]
            
            # copy modulation type
            ds_data_line[3] = ds_raw_data[array_row][3]
            
            # split string containing two Rx Power values
            rx_power=ds_raw_data[array_row][4].split("/")
            # copy both Rx Power values and convert them into float format
            ds_data_line[4] = float(rx_power[0])
            ds_data_line[5] = float(rx_power[1])
            
            # copy channel SNR
            ds_data_line[6] = float(ds_raw_data[array_row][5])
            
            # set LockStatus to True if string is YES
            if ds_raw_data[array_row][6] == "JA":
                ds_data_line[7] = True
            # else (if NO or anything else) set LockStatus on False
            else:
                ds_data_line[7] = False
            
            # append the parsed line into the ds_data table
            ds_data.append(ds_data_line)
                      
            
            # if a data set has been processed, not need to sweep further: bail out and go to next channel 
            break
            
        array_row += 1

    # Proceed next channel
    channel += 1


# start sorting and processing the extracted UPSTREAM data

# preparing storage array for processing
# data map:
# Channel (int)   Frequency(int)    Chan.Typ(string)    Modulation(string)      Tx.Power_dBmV(float)    Rx.Power_dBµV(float)    SNR_dB(float)   RangingStatus(bool)

us_data = []
us_data_line = [0,0,"","",0.00,0.00,False]

# searching the max channel Nr. which was grabbed
us_channel_max = 0

for array_row in range(0,len(us_raw_data)-1):
    if int(us_raw_data[array_row][0]) > us_channel_max:
        us_channel_max = int(us_raw_data[array_row][0])


# starting channel scanning between 1 and channel max
channel = 1

while channel <= us_channel_max:
     
    # start with the first line when searching for the actual channel
    array_row = 0

    # sweeping the raw data until reached the last line
    while array_row <= (len(us_raw_data)-1):

        # look the actual line if searched channel is present (convert value as an int because having beeing grabed as a string)
        if int(us_raw_data[array_row][0]) == channel:
            
            # clearing data line
            us_data_line = [0,0,"","",0.00,0.00,False]
            
            # copy channel number
            us_data_line[0] = int(us_raw_data[array_row][0])
            
            # copy frequency
            # if ODFMA band extract channel boundaries from "XXX~XXX" format and compute central frequency
            if us_raw_data[array_row][1] == "OFDMA":
                ofdma_freq_band = us_raw_data[array_row][2].split("~")
                us_data_line[1] = int((float(ofdma_freq_band[0])+float(ofdma_freq_band[1]))/2)
            else:
            # SC-QAM band or other
                us_data_line[1] = int(us_raw_data[array_row][2])

            # copy channel type
            us_data_line[2] = us_raw_data[array_row][1]
            
            # copy modulation type
            us_data_line[3] = us_raw_data[array_row][3]
            
            # split string containing two Rx Power values
            tx_power=us_raw_data[array_row][4].split("/")
            # copy both Rx Power values and convert them into float format
            us_data_line[4] = float(tx_power[0])
            us_data_line[5] = float(tx_power[1])
            
            # set RangingStatus to True if string is SUCCESS
            if us_raw_data[array_row][5] == "Erfolgreich":
                us_data_line[6] = True
            # else (if anything else) set RangingStatus on False
            else:
                us_data_line[6] = False
            
            # append the parsed line into the ds_data table
            us_data.append(us_data_line)
            
            # if a data set has been processed, not need to sweep further: bail out and go to next channel 
            break
            
        array_row += 1

    # Proceed next channel
    channel += 1


# Print out DS results

print("Downstream informations")
print("***********************\n")
print("Channel\t\tFrequency (MHz)\tChan.Typ\tModulation\tRx.Power (dBmV)\tRx.Power (dBµV)\tSNR (dB)\tLocked", end='')

for x in range(0, len(ds_data)):
    print("")
    for y in range(0, len(ds_data[0])):
        print(ds_data[x][y], end='\t\t')

# Print out US results

print("\n\nUpstream informations")
print("*********************\n")
print("Channel\t\tFrequency (MHz)\tChan.Typ\tModulation\tTx.Power (dBmV)\tTx.Power (dBµV)\tRanged", end='')

for x in range(0, len(us_data)):
    print("")
    for y in range(0, len(us_data[0])):
        print(us_data[x][y], end='\t\t')

# Newline before handing back
print("\n")
