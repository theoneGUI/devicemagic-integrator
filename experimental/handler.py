#!/home/ubuntu/env/bin/python

# Author: Aidan Wright

import os
import json
import time
import math
import datetime
import urllib3
http = urllib3.PoolManager()
import requests, mysql
import sqlinterface as s
import math
from threading import Thread
import commonKnowledge
from commonKnowledge import formatText
import traceback
# Load all of our required environment variables
commonKnowledge.recoverLastSession()

# If we're in development mode, load an import that we need.
# If not, don't bother
if os.environ["CASS_STAGE"] == "DEV":
    import random

# Set up global variables for use
TBKey = os.environ["CASS_TEXTING_KEY"]
auditData = None
login_locked = False


forciblyUpdating = {}

# Set up how to get stuff from ServiceTrade
def makeAPIRequest(page):
    resp = http.request("GET",
        os.environ["CASS_ROOTURL"]+"/"+page,
        headers={"Cookie": f"PHPSESSID={os.environ['CASS_SESSID']}"}
    )
    return resp.data.decode()

def makeAPIURIRequest(page):
    resp = http.request("GET",
        page,
        headers={"Cookie": f"PHPSESSID={os.environ['CASS_SESSID']}"}
    )
    return resp.data.decode()

# Convert unix timestamp to python datetime usable for sending texts
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

# this is a utility function used in order to strip bad characters out of the extremely unorganized data that ServiceTrade gives
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

# Do the credential send to ServiceTrade and store the PHP session it gives back
def login():
    r = requests.post("https://app.servicetrade.com/api/auth",{
        "username": os.environ["CASS_SERVICE_USR"],
        "password": os.environ["CASS_SERVICE_PWD"]
    }
    ,cookies={
        "PHPSESSID" : os.environ["CASS_SESSID"]
    })
    os.environ["CASS_SESSID"] = r.cookies["PHPSESSID"]
    commonKnowledge.saveThisSession()

# If we might be logged out, make sure.
# If we are logged out, log back in and save
def doPanic():
    global login_locked
    try:
        tmp=makeAPIRequest("auth")
        if json.loads(tmp)["data"]["authenticated"] == False:
            raise json.decoder.JSONDecodeError("moo", "rr", 9)
    except json.decoder.JSONDecodeError:
        if login_locked:
            while login_locked:
                time.sleep(.5)
        else:
            login_locked = True
            try:
                print("*********************** CASS SYSTEM SIGNED OUT OF SERVICETRADE")
                login()
                commonKnowledge.recoverLastSession()
                print("*********************** CASS SYSTEM SIGNED BACK IN TO SERVICETRADE")
                time.sleep(4)
                login_locked = False
            finally:
                login_locked = False

print("Initializing...",end="", flush=True)
# Make sure we're logged in right off the bat.
doPanic()
print("[DONE]")

# ServiceTrade class for standardized web requests to ST 
class ServiceTrade():
    def __init__(self):
        self.proto = "https"
        self.domain = "app.servicetrade.com"
        self.apiRoot = "/api"
        self.url = self.proto + "://" + self.domain + self.apiRoot

    def get(self, entity:str, entId:int, args:dict = None):
        return requests.get(self.url+"/"+entity+"/"+str(entId),
            params = args,
            cookies={
                "PHPSESSID" : os.environ['CASS_SESSID']
            }
        )
    
    def put(self, entity:str, entId:int, args:dict = None):
        return requests.put(self.url+"/"+entity+"/"+str(entId),
            params = args,
            cookies={
                "PHPSESSID" : os.environ['CASS_SESSID']
            }
        )

# Make a usable ServiceTrade instance
st = ServiceTrade()

def getResourceFromServiceTrade(route):
    response = None
    try:
        response = http.request("GET",
            "https://app.servicetrade.com/api"+route,
            headers={
                "Cookie": "PHPSESSID="+os.environ['CASS_SESSID']
            }
        ).data.decode()
        library = json.loads(response)
    except json.decoder.JSONDecodeError:
        doPanic()
        response = http.request("GET",
            "https://app.servicetrade.com/api"+route,
            headers={
                "Cookie": "PHPSESSID="+os.environ['CASS_SESSID']
            }
        ).data.decode()
        library = json.loads(response) 
    library = library["data"]
    return library

def processAssetsOnLocation(loc, verb, cursor = None):
    locId = loc["id"]
    assets = getResourceFromServiceTrade("/location?_sideload=appointment.techs,asset.assetDefinition,asset.deficiencies,asset.serviceLine,assetDefinition.serviceLine,attachment.creator,comment.author,deficiency.job,job.invoices,job.vendor,job.customer,location.assets,location.assignedRegions,location.attachments,location.brand,location.comments,location.company,location.contacts,location.externalIds,location.offices,location.primaryContact,location.regions,location.serviceLinesRequired&id="+str(locId))["assets"]
    assetInfo = []
    for i in assets:
        assetInfo.append(getResourceFromServiceTrade("/asset/"+str(i["id"])))

    needToDelete = set()
    locationAssets = s.getAllAssetsOnLoc(locId, cursor)
    locationAssetIds = [i["id"] for i in assetInfo]

    for i in locationAssets:
        if i["id"] not in locationAssetIds:
            needToDelete.add(i["id"])

    for i in needToDelete:
        s.deleteAsset(i, cursor)

    for i in assetInfo:
        if i["status"] == "inactive":
            verb = "delete"
        else:
            verb = "post"
        if s.assetExistsInDB(i["id"], cursor):
            if verb == "delete":
                s.deleteAsset(i["id"], cursor)
            else:
                s.updateAsset(i["id"],i, cursor)
        else:
            if verb == "delete":
                s.deleteAsset(i["id"], cursor)
            else:
                s.addAsset(i, cursor)

def processAssetsOnJob(job, verb, cursor = None):
    loc = None
    try:
        loc = job["locations"]
        for i in loc:
            processAssetsOnLocation(i, verb, cursor=cursor)
    except KeyError:
        loc = job["location"]
        processAssetsOnLocation(loc, verb, cursor=cursor)

def processServicesOnLocation(loc, verb, cursor = None):
    loc = getResourceFromServiceTrade("/location?_sideload=appointment.techs,asset.assetDefinition,asset.deficiencies,asset.serviceLine,assetDefinition.serviceLine,attachment.creator,comment.author,deficiency.job,job.invoices,job.vendor,job.customer,location.assets,location.assignedRegions,location.attachments,location.brand,location.comments,location.company,location.contacts,location.externalIds,location.offices,location.primaryContact,location.regions,location.serviceLinesRequired&id="+str(loc["id"]))
    for i in loc["jobs"]:
        processServicesOnJob(i, verb, cursor=cursor)

def processServicesOnJob(job, verb, cursor = None):
    jobInfo = getResourceFromServiceTrade("/job/"+str(job["id"]))
    for i in jobInfo["appointments"]:
        processServicesOnAppointment(i, verb, cursor=cursor)

def processServicesOnAppointment(appt, verb, cursor = None):
    apptInfo = getResourceFromServiceTrade("/appointment/"+str(appt["id"]))
    servicesOnAppt = [serv["id"] for serv in apptInfo["serviceRequests"]]
    for serv in apptInfo["serviceRequests"]:
        serv["appointment_id"] = apptInfo["id"]
        serv["job_id"] = apptInfo["job"]["id"]
        if s.serviceExistsInDB(serv["id"], cursor):
            if serv["status"] == "void" or serv["status"] == "canceled":
                verb = "delete"
            else:
                verb = "post"
            
            print(verb, serv["status"])

            if verb == "delete":
                s.deleteService(serv["id"], cursor=cursor)
            else:
                s.updateService(serv["id"],serv, cursor=cursor)
        else:
            if verb == "delete":
                s.deleteService(serv["id"], cursor=cursor)
            else:
                s.addService(serv, cursor=cursor)

    servicesOnApptInDB = s.getServicesOnAppt(appt["id"], cursor=cursor)
    for service in servicesOnApptInDB:
        if service["id"] not in servicesOnAppt:
            print(service["id"],"not part of",appt["id"],"... deleting")
            s.deleteService(service["id"], cursor=cursor)

global volatileObjectVariable
volatileObjectVariable = set()
global volatileLocationIdVariable
volatileLocationIdVariable = set()

def run(inputJson):
    for item in range(len(inputJson["data"])):
        response = None
        item = inputJson["data"][item]
        print(item)
        entity = item["entity"]["type"]
        try:
            response = makeAPIURIRequest(item["entity"]["uri"]).replace("\n","<NEWLINE>").replace("\t","<TAB>").replace("\r","<RETURN>")
            library = json.loads(response)
        except json.decoder.JSONDecodeError:
            doPanic()
            response = makeAPIURIRequest(item["entity"]["uri"]).replace("\n","<NEWLINE>").replace("\t","<TAB>").replace("\r","<RETURN>")
            library = json.loads(response) 
        library = library["data"]

        newSerialized = ""
        # based on what the entity is, use these if statements to create the necessary volatile object and modify the worker thread to 
        #   work off of
        if (entity == "location" and item["action"] == "deleted") or (entity == "location" and library["status"] == "inactive"):
            locId = str(library["id"])
            newSerialized += "delete"
            newSerialized += "$%$"
            newSerialized += entity
            newSerialized += "$%$"
            newSerialized += json.dumps(library)
            newSerialized += "$%$"
            newSerialized += locId
            volatileObjectVariable.add(locId)
        elif entity == "location":
            locId = str(library["id"])
            if volatileLocationIdVariable.__contains__(locId):
                print("passed on something on location ", locId)
                return None
            newSerialized += "post"
            newSerialized += "$%$"
            newSerialized += entity
            newSerialized += "$%$"
            newSerialized += json.dumps(library)
            newSerialized += "$%$"
            newSerialized += locId
            volatileLocationIdVariable.add(locId)
            volatileObjectVariable.add(newSerialized)
        elif entity == "job":
            locId = str(library["location"]["id"])
            if volatileLocationIdVariable.__contains__(locId):
                print("passed on something on location ", locId)
                return None
            newSerialized += "post"
            newSerialized += "$%$"
            newSerialized += entity
            newSerialized += "$%$"
            newSerialized += json.dumps(library)
            newSerialized += "$%$"
            newSerialized += locId
            volatileLocationIdVariable.add(locId)
            volatileObjectVariable.add(newSerialized)
        elif entity == "appointment":
            locId = str(library["location"]["id"])
            if volatileLocationIdVariable.__contains__(locId):
                print("passed on something on location ", locId)
                return None       
            newSerialized += "post"
            newSerialized += "$%$"
            newSerialized += entity
            newSerialized += "$%$"
            newSerialized += json.dumps(library)
            newSerialized += "$%$"
            newSerialized += locId
            volatileLocationIdVariable.add(locId)
            volatileObjectVariable.add(newSerialized)

def auditFromCSV():
    with open("locations.csv", newline="\n") as file:
        reader = csv.DictReader(file)
        passIn = {"entity" : {"type" : "location"}, "data" : []}
        for row in reader:
            passIn["data"].append({"action" : "update", "entity" : {"type" : "location", "uri" : "https://app.servicetrade.com/api/location/"+str(row["id"])}})
        run(passIn)


def workerThread():
    try:
        print("started thread")
        MYCursor = s.Wrapper()
        while True:
            try:
                try:
                    parsed = volatileObjectVariable.pop().split("$%$")
                except KeyError:
                    time.sleep(10)
                    continue
                action = parsed[0]
                entity = parsed[1]
                library = json.loads(parsed[2])
                locId = parsed[3]
                currentID = library["id"]
                if (entity == "location" and action == "deleted") or (entity == "location" and library["status"] == "inactive"):
                    processAssetsOnLocation(library, "delete", MYCursor)
                    processServicesOnLocation(library, "delete", MYCursor)
                    print("Deleted location #", currentID,"'s assets")

                elif entity == "location":
                    print("Adding services from loc #", currentID)
                    processServicesOnLocation(library, "post",MYCursor)
                    print("Adding assets from loc #", currentID)
                    processAssetsOnLocation(library, "post",MYCursor)


                elif entity == "job":
                    print("Adding services from job #", currentID)
                    processServicesOnJob(library, "post",MYCursor)
                    print("Adding assets from job #", currentID)
                    processAssetsOnJob(library, "post",MYCursor)

                elif entity == "appointment":
                    print("Adding services from appt #",currentID)
                    processServicesOnAppointment(library, "post",MYCursor)
                print("did a thing for location ", locId)
                time.sleep(5)
                volatileLocationIdVariable.remove(locId)
            except:
                print(traceback.format_exc())
    finally:
        print("Stopped thread")

Thread(target=workerThread).start()