import time
import cv2
import numpy as np
import platform

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

def main():
    
  #Read image to file
  
  with open("test1.thr", "rb") as img_file:
      header = np.fromfile(img_file, dtype=np.dtype('uint16'), count=3)

      #Create empty image array
      img_data = np.empty(shape=(header[1], header[0]), dtype=np.dtype('uint16'))
  
      #Read image contain (from file) to array
      for i in range(header[1]):
        img_data[i] = np.fromfile(img_file, dtype=np.dtype('uint16'), count=header[0])
  
  #Resize data from 160x120 pixels to whatever
  data = cv2.resize(img_data[:,:], (320, 240))
          
  #Find minimu and maximum temperature-point
  minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
      
  img = raw_to_8bit(data)
          
  display_temperature(img, minVal, minLoc, (255, 0, 0))
  display_temperature(img, maxVal, maxLoc, (0, 0, 255))
  cv2.imshow('Lepton 3.5 Radiometry', img)
  
  while(True):
    cv2.waitKey(1)
          
  cv2.destroyAllWindows()

if __name__ == '__main__':
  main()
