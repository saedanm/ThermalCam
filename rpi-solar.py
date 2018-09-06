import sys
import os
import socket
import numpy as np
import cv2

def FindNanoPi(ip_addr):
    try:
        hostname = socket.gethostbyaddr(ip_addr)
        if ("nanopi" in hostname[0]):
            return True
    except socket.herror:
        return False


#Scan all ip adress for NanoPi Mac address
for i in range(10,21):
    ip_addr = '192.168.10.' + str(i)
    if (FindNanoPi(ip_addr) == True):
        break
else:
    print ("No thermal camera found)")
    exit(1)

print(ip_addr)


