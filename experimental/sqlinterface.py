#!/usr/bin/python3

# Author: Aidan Wright

import mysql.connector
import json
import time
import datetime
import hashlib, random
import requests
import math
from commonKnowledge import *
import traceback
import os
import re

# Wrapper is a wrapper class for the mysql.connector object.
class Wrapper():

    def __init__(self):
        # open a new connection on construction
        self.db = self.connect()
        self.cursor = self.db.cursor(buffered=False)
        self.rowcount = 0

    def __del__(self):
        # Close the database connection like a good boy
        try:
            self.cursor.close()
            self.db.close()
        except:
            pass

    def connect(self):
        # Actually initialize the database connection, getting the credentials from our environment variables.
        connection = None
        try:
            connection = mysql.connector.connect(
                host=os.environ["CASS_DB_HOST"],
                user=os.environ["CASS_DB_USR"],
                passwd=os.environ["CASS_DB_PWD"],
                database=os.environ["CASS_DB_DB"]
            )
            connection.autocommit = True
        except:
            print(traceback.format_exc())
        return connection

    def retr(self, stmt, args=[], multiQuery = False):
        # Do a lot of checking and return if there's something to return or just execute the statement
        # One funtion to rule them all; no special treatment for any single type of query.
        self.result = None
        self.rowcount = None
        try:
            self.cursor.execute(stmt, args)
        except mysql.connector.errors.InternalError:
            self.cursor.fetchall()
            self.cursor.execute(stmt, args, multiQuery)
        try:
            self.rowcount = self.cursor.rowcount
            self.result = self.cursor.fetchall()
        except:
            self.result = None
        try:
            self.lastrowid = self.cursor.lastrowid
        except:
            self.lastrowid = None
        return self.result


# Make sure we're signed in with the most recent credentials
recoverLastSession()

def is_dst(dt):
    if dt.year < 2007:
        raise ValueError()
    dst_start = datetime.datetime(dt.year, 3, 8, 2, 0)
    dst_start += datetime.timedelta(6 - dst_start.weekday())
    dst_end = datetime.datetime(dt.year, 11, 1, 2, 0)
    dst_end += datetime.timedelta(6 - dst_end.weekday())
    return dst_start <= dt < dst_end

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

def getApptData(argDict, cursor = None):
    if cursor == None:
        cursor = Wrapper()
    argDict = [ argDict ]
    sql = "SELECT data FROM asset_data WHERE id=%s"
    out = cursor.retr(sql, argDict)
    
    return out

def updateAsset(ID, data, cursor = None):
    if cursor == None:
        cursor = Wrapper()
    while type(data) != dict:
        data = json.loads(data)

    sql = "UPDATE asset_info SET data=%s, stamp=CURRENT_TIMESTAMP WHERE asset_id = %s"
    cursor.retr(sql, [json.dumps(data), ID])

def addAsset(data, cursor = None):
    if cursor == None:
        cursor = Wrapper()
    while type(data) != dict:
        data = json.loads(data)
    sql = "INSERT INTO asset_info (data) VALUES (%s)"
    cursor.retr(sql, [json.dumps(data)])

def deleteAsset(ID, cursor = None):
    if cursor == None:
        cursor = Wrapper()
    cursor.retr("DELETE FROM asset_info WHERE asset_id = %s", [ID])

def assetExistsInDB(ID, cursor = None):
    if cursor == None:
        cursor = Wrapper()
    result = cursor.retr("SELECT asset_id FROM asset_info WHERE asset_id = %s", [ID])
    return len(result) > 0

def updateService(ID, data, cursor = None):
    if cursor == None:
        cursor = Wrapper()
    while type(data) != dict:
        data = json.loads(data)

    sql = "UPDATE service_info SET data=%s, stamp=CURRENT_TIMESTAMP WHERE service_id = %s"
    cursor.retr(sql, [json.dumps(data), ID])

def addService(data, cursor = None):
    if cursor == None:
        cursor = Wrapper()
    while type(data) != dict:
        data = json.loads(data)
    sql = "INSERT INTO service_info (data) VALUES (%s)"
    cursor.retr(sql, [json.dumps(data)])

def deleteService(ID, cursor = None):
    if cursor == None:
        cursor = Wrapper()
    cursor.retr("DELETE FROM service_info WHERE service_id = %s", [ID])

def serviceExistsInDB(ID, cursor = None):
    if cursor == None:
        cursor = Wrapper()
    result = cursor.retr("SELECT service_id FROM service_info WHERE service_id = %s", [ID])
    return len(result) > 0

def getServicesOnAppt(ID, cursor = None):
    if cursor == None:
        cursor = Wrapper()
    result = cursor.retr("SELECT JSON_OBJECT('id', service_id) FROM service_info WHERE service_appt_id = %s", [ID])
    out = [json.loads(result[i][0]) for i in range(len(result))]
    return out

def getAllAssetsOnLoc(ID, cursor = None):
    if cursor == None:
        cursor = Wrapper()

    result = cursor.retr("SELECT JSON_OBJECT('id', asset_id) FROM asset_info WHERE asset_location_id = %s", [ID])
    out = [json.loads(result[i][0]) for i in range(len(result))]
    return out
#def getAllBad():
#    if cursor == None:
 #       cursor = Wrapper()
#    result = cursor.retr("SELECT JSON_OBJECT('id', tmp.id, 'a_id', tmp.aid) FROM (SELECT id, asset_id AS aid, COUNT(*) AS ct FROM asset_info GROUP BY asset_id) AS tmp WHERE tmp.ct > 1")
#    allBad = [json.loads(result[i][0]) for i in range(len(result))]
#    for i in allBad:
#        cursor.retr("DELETE FROM asset_info WHERE id=%s",[i["id"]])