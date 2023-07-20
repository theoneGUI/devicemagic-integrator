#!/home/ubuntu/env/bin/python

# Author: Aidan Wright

# This file contains a lot of global utility functions
# It also contains all the permissions definitions so the system can use them anywhere it needs to authenticate based on permissions
# It also contains the WebSocket stuff which has to be referenced by multiple files

import json
import dotenv, os, datetime
dotenv.load_dotenv("/home/ubuntu/cass-config/.env")

#load the last saved session variables out of the environment file
def recoverLastSession():
    dotenv.load_dotenv("/home/ubuntu/cass-config/.env")
# save all current session variables into the environment file
def saveThisSession():
    for i in os.environ:
        if "CASS_" in i:
            dotenv.set_key("/home/ubuntu/cass-config/.env",i, os.environ[i])

# this is a utility function used globally in order to strip bad characters out of the extremely unorganized data that ServiceTrade gives
def processPhoneNo(phone):
    digits = "0123456789"
    phone = str(phone)
    if "/" in phone:
        phone = phone.split("/")[0]
        phone = [i for i in phone if i in digits]
        phone = ''.join(phone)
    else:
        phone = [i for i in phone]
        phone = [i for i in phone if i in digits]
        phone = ''.join(phone)
    if len(phone) == 11:
        phone = phone[1:len(phone)]
    elif len(phone) == 12:
        phone = phone[2:len(phone)]
    return phone

# Convert unix timestamp to python datetime usable for sending texts
# @returns a 2-item list with date first and time second, both strings
def toDateAndTime(arg):
    apptStart = datetime.datetime.fromtimestamp(int(arg))
    apptStartTimeH = apptStart.strftime("%H")
    apptStartTimeM = apptStart.strftime("%M")
    apptStartTimePostfix = "AM"
    apptStartTimeH=int(apptStartTimeH)
    if apptStartTimeH > 12:
        apptStartTimeH = apptStartTimeH-12
        apptStartTimePostfix = "PM"
    elif apptStartTimeH == 12:
        apptStartTimeH = 12
        apptStartTimePostfix = "PM"
    apptStartTime = f"{apptStartTimeH}:{apptStartTimeM} {apptStartTimePostfix}"
    apptStartDate = apptStart.strftime("%m/%d/%Y")
    return [apptStartDate,apptStartTime]

# This function is a helper function which formats the text for the appointment reminder by replacing tokens found from the text stored in the database
# @returns string with tokens replaced with actual values
def formatText(text, windowStart, windowEnd, customerName = None):
    # Formats the text for the appointment reminder.
    apptStartDate=toDateAndTime(windowStart)[0]
    apptStartTime=toDateAndTime(windowStart)[1]
    apptEndDate=toDateAndTime(windowEnd)[0]
    apptEndTime=toDateAndTime(windowEnd)[1]
    if customerName != None:
        return text.replace("$APPTSTARTTIME$", apptStartTime).replace("$APPTSTARTDATE$", apptStartDate).replace("$APPTENDTIME$", apptEndTime).replace("$APPTENDDATE$", apptEndDate).replace("$CUSTNAME$", customerName)
    else:
        return text.replace("$APPTSTARTTIME$", apptStartTime).replace("$APPTSTARTDATE$", apptStartDate).replace("$APPTENDTIME$", apptEndTime).replace("$APPTENDDATE$", apptEndDate)

# Defining an exception for the web app to use when user is not authenticated
class InvalidLoginError(Exception):
	pass

# utility function to not throw an error if a key in a dict doesn't exist
def get(lib, key):
	try:
		return lib[key]
	except:
		return None
