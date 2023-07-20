#!/usr/bin/python3

# Author: Aidan Wright

from flask import Flask,request,json
from flask_cors import CORS
import sqlinterface as s
import handler, hmac, os
import time, socket, hashlib, threading, random

def read(fname):
	out  =""
	with open(fname) as a:
		out = a.read()
	return out

version = {"version" : "0.1"}
app = Flask(__name__)
CORS(app)

class InvalidLoginError(Exception):
	pass

@app.route("/")

def hello():
	return "Device Magic DB"

@app.route("/devicemagic/process", methods=["POST"])

def getthedevicemagic():
	print(request.json)
	with open("/home/ubuntu/dmi-dev/devicemagic_submissions.log", "a") as file:
		file.write(json.dumps(request.json, indent=2))
		file.write("\n\n\n")
	return '{"status": true}'

@app.route("/servicetradeingest",methods=["POST"])

def stHandle():
	data = request.json
	threading.Thread(target = handler.run, args=[data]).start()
	return '''{ "status": "received" }'''
