from ctypes import *
import time
import cv2
import numpy as np
import Queue
import platform
import socket
from threading import Thread

#Constant definition
AGC_UNIT_ID = 3
OEM_UNIT_ID = 4
RAD_UNIT_ID = 5
SYS_UNIT_ID = 6
VID_UNIT_ID = 7

UVC_FRAME_FORMAT_UYVY = 4
UVC_FRAME_FORMAT_I420 = 5
UVC_FRAME_FORMAT_RGB = 7
UVC_FRAME_FORMAT_BGR = 8
UVC_FRAME_FORMAT_Y16 = 13

#Definition of c-type classes
class uvc_context(Structure):
    _fields_ = [("usb_ctx", c_void_p),
                ("own_usb_ctx", c_uint8),
                ("open_devices", c_void_p),
                ("handler_thread", c_ulong),
                ("kill_handler_thread", c_int)]

class uvc_device(Structure):
    _fields_ = [("ctx", POINTER(uvc_context)),
                ("ref", c_int),
                ("usb_dev", c_void_p)]

class uvc_stream_ctrl(Structure):
    _fields_ = [("bmHint", c_uint16),
                ("bFormatIndex", c_uint8),
                ("bFrameIndex", c_uint8),
                ("dwFrameInterval", c_uint32),
                ("wKeyFrameRate", c_uint16),
                ("wPFrameRate", c_uint16),
                ("wCompQuality", c_uint16),
                ("wCompWindowSize", c_uint16),
                ("wDelay", c_uint16),
                ("dwMaxVideoFrameSize", c_uint32),
                ("dwMaxPayloadTransferSize", c_uint32),
                ("dwClockFrequency", c_uint32),
                ("bmFramingInfo", c_uint8),
                ("bPreferredVersion", c_uint8),
                ("bMinVersion", c_uint8),
                ("bMaxVersion", c_uint8),
                ("bInterfaceNumber", c_uint8)]

class uvc_format_desc(Structure):
    pass

class timeval(Structure):
    _fields_ = [("tv_sec", c_long), ("tv_usec", c_long)]

class uvc_frame(Structure):
    _fields_ = [# /** Image data for this frame */
                ("data", POINTER(c_uint8)),
                # /** Size of image data buffer */
                ("data_bytes", c_size_t),
                # /** Width of image in pixels */
                ("width", c_uint32),
                # /** Height of image in pixels */
                ("height", c_uint32),
                # /** Pixel data format */
                ("frame_format", c_uint), # enum uvc_frame_format frame_format
                # /** Number of bytes per horizontal line (undefined for compressed format) */
                ("step", c_size_t),
                # /** Frame number (may skip, but is strictly monotonically increasing) */
                ("sequence", c_uint32),
                # /** Estimate of system time when the device started capturing the image */
                ("capture_time", timeval),
                # /** Handle on the device that produced the image.
                #  * @warning You must not call any uvc_* functions during a callback. */
                ("source", POINTER(uvc_device)),
                # /** Is the data buffer owned by the library?
                #  * If 1, the data buffer can be arbitrarily reallocated by frame conversion
                #  * functions.
                #  * If 0, the data buffer will not be reallocated or freed by the library.
                #  * Set this field to zero if you are supplying the buffer.
                #  */
                ("library_owns_data", c_uint8)]

class uvc_device_handle(Structure):
    _fields_ = [("dev", POINTER(uvc_device)),
                ("prev", c_void_p),
                ("next", c_void_p),
                ("usb_devh", c_void_p),
                ("info", c_void_p),
                ("status_xfer", c_void_p),
                ("status_buf", c_ubyte * 32),
                ("status_cb", c_void_p),
                ("status_user_ptr", c_void_p),
                ("button_cb", c_void_p),
                ("button_user_ptr", c_void_p),
                ("streams", c_void_p),
                ("is_isight", c_ubyte)]

class lep_oem_sw_version(Structure):
    _fields_ = [("gpp_major", c_ubyte),
                ("gpp_minor", c_ubyte),
                ("gpp_build", c_ubyte),
                ("dsp_major", c_ubyte),
                ("dsp_minor", c_ubyte),
                ("dsp_build", c_ubyte),
                ("reserved", c_ushort)]
#End of class definition

#Check with system, and use library appropiately
try:
    if platform.system() == 'Darwin':
        libuvc = cdll.LoadLibrary("libuvc.dylib")
    elif platform.system() == 'Linux':
        libuvc = cdll.LoadLibrary("libuvc.so")
    else:
        libuvc = cdll.LoadLibrary("libuvc")
except OSError:
    print "Error: could not find libuvc!"
    exit(1)

def call_extension_unit(devh, unit, control, data, size):
    return libuvc.uvc_get_ctrl(devh, unit, control, data, size, 0x81)


#Intialize buffer for image frame
BUF_SIZE = 2
q = Queue.Queue(BUF_SIZE)

def print_device_info(devh):
    vers = lep_oem_sw_version()
    call_extension_unit(devh, OEM_UNIT_ID, 9, byref(vers), 8)
    print("Version gpp: {0}.{1}.{2} dsp: {3}.{4}.{5}".format(vers.gpp_major, vers.gpp_minor, vers.gpp_build,vers.dsp_major, vers.dsp_minor, vers.dsp_build,))

    flir_pn = create_string_buffer(32)
    call_extension_unit(devh, OEM_UNIT_ID, 8, flir_pn, 32)
    print("FLIR part #: {0}".format(flir_pn.raw))
    flir_sn = create_string_buffer(8)
    call_extension_unit(devh, SYS_UNIT_ID, 3, flir_sn, 8)
    print("FLIR serial #: {0}".format(repr(flir_sn.raw)))

#Function to receive image from video stream when the image frame is ready
def py_frame_callback(frame, userptr):
    array_pointer = cast(frame.contents.data, POINTER(c_uint16 * (frame.contents.width * frame.contents.height)))
    #data = np.frombuffer(array_pointer.contents, dtype=np.dtype(np.uint16)).reshape(frame.contents.height, frame.contents.width)
    
    data = array_pointer.contents
    
    #Check whether returned buffer is valid
    if frame.contents.data_bytes != (2 * frame.contents.width * frame.contents.height):
        return

    if not q.full():
        #Put image data to queue, when slot is empty
        q.put(data)
    else:
        #Take previous data out
        discard_data = q.get_nowait()
        #Put new data into queue
        q.put(data)

PTR_PY_FRAME_CALLBACK = CFUNCTYPE(None, POINTER(uvc_frame), c_void_p)(py_frame_callback)

###################### End server thread ######################

def main():
    ctx = POINTER(uvc_context)()
    dev = POINTER(uvc_device)()
    devh = POINTER(uvc_device_handle)()
    ctrl = uvc_stream_ctrl()
    
    #Intiailze libuvc
    res = libuvc.uvc_init(byref(ctx), 0)
    
    #Do not proceed anything if there is any error
    if res < 0:
        print("uvc_init error")
        exit(1)

    #Find purethermal camera
    try:
        res = libuvc.uvc_find_device(ctx, byref(dev), 0, 0, 0)
        if res < 0:
            print("uvc_find_device error")
            exit(1)
    except:
        print("Unknown error --> uvc_find_device")
        exit(1)
        
    #Connect camera
    try:
        res = libuvc.uvc_open(dev, byref(devh))
        if res < 0:
            print("uvc_open error")
            exit(1)
    except:
        print("Unknown error --> uvc_open")
        exit(1)

    #Camera is connected
    print("Thermal camera connected!")
    print_device_info(devh)

    #Set image width, height and pixel formatting
    libuvc.uvc_get_stream_ctrl_format_size(devh, byref(ctrl), UVC_FRAME_FORMAT_Y16, 160, 120, 9)

    #Start video streaming
    try:
        res = libuvc.uvc_start_streaming(devh, byref(ctrl), PTR_PY_FRAME_CALLBACK, None, 0)
        if res < 0:
            print("uvc_start_streaming failed: {0}".format(res))
            exit(1)
    except:
        print("Unknown error --> uvc_start_streaming")
        exit(1)


    # Create socket and listen on port 5005
    server_address = ('192.168.10.1', 5005)
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #Connect server
    for trial in range(10):
        try:
            sock.connect(server_address)
        except socket.error, msg:
            sock.close()
            time.sleep(10)
    else:
        sock = None
        exit(1)

    #After connect to server, just wait for server to call image
    print ("Server connected...")
        
    while(True):
    #{
        #Waiting for server request
        msg = sock.recv(7)
        if (msg == 'request'):
        #{
            print ("Server requested %d"%time.time())
            
            #Get image data from queue
            data = q.get(True, 500)
            
            if data is None:
            #{
                print("Error...")
            #}
            else:
            #{
                #Encode data and send to server
                header = np.getbuffer(np.array([160,120,2], 'uint16'))
                img_data = header + data
                #Send image to client
                client_socket.send(img_data)
            #}
        #}
    #}


if __name__ == '__main__':
  main()
