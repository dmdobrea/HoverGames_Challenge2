# USAGE
# python client.py --server-ip SERVER_IP
#     or
# python client.py -s SERVER_IP

# import the necessary packages
import argparse
import imagezmq
import socket
import time
import cv2
import signal

min = 100
max = 0
i   = 0
dt_mean = 0


# function to handle keyboard interrupt
def signal_handler(sig, frame) :
    print ("")
    print ("[INFO] You pressed Ctrl + C ...")
    print ("[INFO] Min dt  = " + str(min))
    print ("[INFO] Max dt  = " + str(max))
    print ("[INFO] Mean dt = " + str(dt_mean/i))
    print ("[INFO] No. pic = " + str(i))
    print ("")

    sys.exit(0)


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-s", "--server-ip", required=True,
	help="ip address of the server to which the client will connect")
args = vars(ap.parse_args())

# signal trap to handle keyboard interrupt
signal.signal(signal.SIGINT, signal_handler)

# initialize the ImageSender object with the socket address of the server
sender = imagezmq.ImageSender(connect_to="tcp://{}:5555".format(args["server_ip"]))

# get the host name
navq_Name = socket.gethostname()

# initialize the video stream
#cap = cv2.VideoCapture('v4l2src ! video/x-raw,width=640,height=480 ! decodebin ! videoconvert ! appsink', cv2.CAP_GSTREAMER)
cap = cv2.VideoCapture('v4l2src ! video/x-raw,width=1280,height=720 ! decodebin ! videoconvert ! appsink', cv2.CAP_GSTREAMER)

# allow the camera sensor to warmup
time.sleep(2.0)

# loop over frames from the camera
while True:
    start = time.time()
 
    # read the frame from the camera 
    ret,frame = cap.read()
    
    # flips the frame vertically
    frame = cv2.flip(frame, 0)  

    # send the frame to the server
    sender.send_image(navq_Name, frame)   # without this line 0.06[s]; with this line 0.33...0.6 [s]

    end = time.time()

    dt = end-start
    print ("Running time:" + str (dt))

    if dt < min:
        min = dt
    if dt > max:
        max = dt

    i = i + 1
    dt_mean = dt_mean + dt