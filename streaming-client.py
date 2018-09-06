import sys
import socket
import numpy as np
import cv2
import time

def ktof(val):
    return (1.8 * ktoc(val) + 32.0)

def ktoc(val):
    return (val - 27315) / 100.0

#Convert raw format to 8 bit pixel data (greyscale)
def raw_to_8bit(data):
    cv2.normalize(data, data, 0, 65535, cv2.NORM_MINMAX)
    np.right_shift(data, 8, data)
    return cv2.cvtColor(np.uint8(data), cv2.COLOR_GRAY2RGB)

def display_temperature(img, val_k, loc, color):
    val = ktoc(val_k)
    cv2.putText(img,"{0:.1f} C".format(val), loc, cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
    x, y = loc
    cv2.line(img, (x - 2, y), (x + 2, y), color, 1)
    cv2.line(img, (x, y - 2), (x, y + 2), color, 1)


#Define server address
server_address = ('192.168.10.19', 5005)

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#Connect server
sock.connect(server_address)

while(True):
    #Send image request
    sock.sendall('request')
    #Let put waiting for 100 ms
    time.sleep(0.15)

    #Recieve image data from server
    #Get image in two chunks
    try:
        img_buf = sock.recv(4096)
        for i in range(9):
            img_buf = img_buf+sock.recv(4096)

        #Decode the image
        header = np.frombuffer(img_buf, dtype=np.dtype('uint16'), count=3)

        #Create empty image array
        img_data = np.empty(shape=(header[1], header[0]), dtype=np.dtype('uint16'))
            
        #Decode image contain  to array
        for i in range(header[1]):
            offset_num = 2*i*header[0] +6
            img_data[i] = np.frombuffer(img_buf, dtype=np.dtype('uint16'), count=header[0], offset=offset_num)
            
        #Resize data from 160x120 pixels to whatever
        data = cv2.resize(img_data[:,:], (320, 240))
        img = raw_to_8bit(data)
        cv2.imshow('Lepton 3.5 Radiometry', img)
        cv2.waitKey(1)
    except:
        pass

#End while
sock.close()
cv2.destroyAllWindows()

