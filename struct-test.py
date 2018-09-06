import numpy as np
import cv2

#Convert raw format to 8 bit pixel data (greyscale)
def raw_to_8bit(data):
    cv2.normalize(data, data, 0, 65535, cv2.NORM_MINMAX)
    np.right_shift(data, 8, data)
    return cv2.cvtColor(np.uint8(data), cv2.COLOR_GRAY2RGB)

#Make thread to capture image data from thermal camera here
#Test with statis buffer
with open("test1.thr", "rb") as img_file:
    img_data1 = img_file.read()
img_file.close()

img_buf = bytearray(len(img_data1))
for i in range(len(img_data1)):
    img_buf[i] = img_data1[i]

header = np.frombuffer(img_buf, dtype=np.dtype('uint16'), count=3)

#Create empty image array
img_data = np.empty(shape=(header[1], header[0]), dtype=np.dtype('uint16'))

#Decode image contain  to array
for i in range(header[1]):
    offset_num = 2*i*header[0] +6
    img_data[i] = np.frombuffer(img_buf, dtype=np.dtype('uint16'), count=header[0], offset=offset_num)


header_buf = np.getbuffer(header)

print(header_buf)

'''
#Resize data from 160x120 pixels to whatever
data = cv2.resize(img_data[:,:], (320, 240))

img = raw_to_8bit(data)

cv2.imshow('Lepton 3.5 Radiometry', img)

while(True):
    cv2.waitKey(1)

cv2.destroyAllWindows()
'''
