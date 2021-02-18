# USAGE (for real case application):
#
# 	python human_recog.py --mode 2 --target cpu
# 	python human_recog.py -m 2 -t cpu

# import the necessary packages
from imutils.video import FPS
import argparse
import imagezmq
import socket
import signal
import time
import sys

import cv2
import dlib

from multiprocessing import Process
from multiprocessing import Queue
from multiprocessing import Value

from pymavlink import mavutil

import threading

#=======================================================================
# A thread that manage the acquisition of the GPS data
def getGPS_thread(out_q, mutex, verbose):
	i = 0

	while mainHR_v.value:
		mutex.acquire()
		msg = hoverGames.recv_match()
		mutex.release()
	
		if not msg:
			continue
		if msg.get_type() == 'GPS_RAW_INT':
			if verbose is not None: 
				print("\n\n*****Got message: %s*****"%msg.get_type())
				print("Message: %s"%msg)
				print("As dictionary: %s"%msg.to_dict())
				print("  Lat. : %s"%msg.lat)
				print("  Lon. : %s"%msg.lon)
				print("  eph. : %s"%msg.eph)

			if out_q.empty() is False:
				out_q.get()

			# an queue, to exchange GPS data safely 
			# with the main application 
			out_q.put([msg.lat, msg.lon])

		time.sleep(0.05)

	print("[INFO] : GPS thread end.")

#=======================================================================
# a function to handle keyboard interrupt
def signal_handler_CtrlC(sig, myFrame) :
	print ("")
	print ("[INFO] : You pressed Ctrl + C ...")
	#signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	#===============================================================
	# terminate main loop & GPS data acquisition loop
	mainHR_v.value = 0

	#===============================================================
	print ("[INFO] : Ctrl + C clean up end !!!")

#=======================================================================
# save the output data (where the human subject are recognized) to file
def write_video(outputPath, writeVideo, frameWQueue, W, H):
	# initialize the FourCC and video writer object
	# fourcc = 4-byte code used to specify the video codec:
	# DIVX, XVID, MJPG, X264, WMV1, WMV2
	print("[INFO] : Configuring writing process.")
	fourcc = cv2.VideoWriter_fourcc(*"MJPG")						
	writer = cv2.VideoWriter (outputPath, fourcc, 30.0, (W, H), True)
	
	# loop while the write flag is set or the output 
	# frame queue is not empty
	print("[INFO] : Starting writing process.")
	while writeVideo_v.value or not frameWQueue.empty():
		
		# check if the output frame queue is not empty
		if not frameWQueue.empty():
			# get the frame from the queue and write the frame
			frame = frameWQueue.get()
			#print("[myINFO] Right now I'm write data...")
			writer.write(frame)

	# release the video writer object
	writer.release()

	print("[INFO] : Writer process end.")
	
#=======================================================================
# stream the human recognition results through ZeroMQ to a server	
def stream_video(myServerIP, streamVideo, frameSQueue, jpeg_quality):
	# loop while the stram flag is set or 
	# the output frame queue is not empty
	print("[INFO] : Starting streaming process.")
	
	# initialize the ImageSender object with 
	# the socket address of the server
	sender = imagezmq.ImageSender(connect_to="tcp://{}:5555".format(myServerIP))	
	
	# get the host name
	navq_Name = socket.gethostname()

	# loop while the stream flag is set or   
	# the output frame queue is not empty
	while streamVideo.value or not frameSQueue.empty():
		
		# check if the output frame queue is not empty
		if not frameSQueue.empty():
			# get the frame from the queue and write the frame
			frame = frameSQueue.get()
			
			# flips the frame vertically
			# frame = cv2.flip(frame,0)                

			ret_code, jpg_buffer = cv2.imencode(".jpg", frame, 
				[int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])

			# send the jpeg image
			sender.send_jpg(navq_Name, jpg_buffer)  

	print("[INFO] : The streaming process end.")

#=======================================================================	
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-m", "--mode", type=int, required=True,
	choices=[0, 1, 2],
	help="Working mode: 0 - local, 1 - streaming, 2 - full")
ap.add_argument("-t", "--target", type=str, required=True,
	choices=["myriad", "cpu"],
	help="target processor for object detection")
ap.add_argument("-i", "--input", type=str,
	help="path to the input video file")
ap.add_argument("-o", "--output", type=str,
	help="path to optional output video file")	
ap.add_argument("-s", "--server-ip", 
	help="ip address of the server to which the client will connect")	
ap.add_argument("-v", "--verbose", nargs='?',
	help="provide various information to understand what is happening in the system")	
args = vars(ap.parse_args())

#=======================================================================
# initialize mainly the variable with global efect

#0 to 100, higher is better quality, 95 is cv2 default
jpeg_quality = 65 

# number of skip frames: 
#    * 1 detection performed with MobileNet-SSD in the first frame, 
#    * {skip_frames - 1} frames in which the tracking is done through 
#                        the correlation tracker algorithm
skip_frames  = 15

# the number of frames after a custom MAVlink message will be sent 
customMess_frames = 40

#=======================================================================
# check if the IP address of the server exist in the case of
#                selecting the streaming mode
if args["mode"] == 1:
	if args["server_ip"] is None:
		print(" ")
		print("[ERROR] : You selected the streaming mode, but no server IP")
		print(" ")
		sys.exit(0)

#=======================================================================
# initialize the list of class labels MobileNet SSD detects
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
	"bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
	"dog", "horse", "motorbike", "person", "pottedplant", "sheep",
	"sofa", "train", "tvmonitor"]

#=======================================================================
# load our serialized model from disk
print("[INFO] : Loading dnn MobileNet model...")
net = cv2.dnn.readNetFromCaffe("mobilenet_ssd/MobileNetSSD_deploy.prototxt",
	"mobilenet_ssd/MobileNetSSD_deploy.caffemodel")

#=======================================================================
# check if the target processor is myriad, if so, then set the
# preferable target to myriad
if args["target"] == "myriad":
	net.setPreferableTarget  (cv2.dnn.DNN_TARGET_MYRIAD)

# otherwise, the target processor is CPU
else:
	# set the preferable target processor to CPU and 
	# preferable backend to OpenCV
	net.setPreferableTarget  (cv2.dnn.DNN_TARGET_CPU)
	net.setPreferableBackend (cv2.dnn.DNN_BACKEND_OPENCV)

# the DNN just processed the frame 
dnnWork = 0

#=======================================================================
# MAVLink2
# create a  connection to FMU
if args["mode"] == 2:
	mavutil.set_dialect("video_monitor")

	# create a connection to FMU
	hoverGames = mavutil.mavlink_connection("/dev/ttymxc2", baud=921600)	# input=False

	# wait for the heartbeat message to find the system id
	hoverGames.wait_heartbeat()

	if args["verbose"] is not None:
		print("[INFO] : Heartbeat from system (system %u component %u)"%(hoverGames.target_system, hoverGames.target_component))

#=======================================================================
# Based on the input grab, a reference to the video file or to camera
# If no input video file. get data from Google Coral camera
if not args.get("input", False):
	print("[INFO] : Starting camera video stream...")
	vs = cv2.VideoCapture('v4l2src ! video/x-raw,width=640,height=480 ! decodebin ! videoconvert ! appsink', cv2.CAP_GSTREAMER)

	# allow the camera sensor to warmup
	time.sleep(2.0)
else:
	print("[INFO] : Opening input video file...")
	vs = cv2.VideoCapture(args["input"])
	
#=======================================================================
# INIT
#=====================================================
# initialize the frame dimensions
W = None
H = None

# initialize the number of frames processed up to now
noFrames    = 0
confidence  = 0
myLatitude  = 0
myLongitude = 0

#=======================================================================
writerProcess = None
streamProcess = None

threadGPS     = None

writeVideo_v  = None
streamVideo_v = None
threadGPS_v   = None	
mainHR_v      = None	

getgpsQueue   = None	# the GPS data frame queue
frameWQueue   = None	# the frame queue for avi file writing
frameSQueue   = None	# the frame queue for the video streaming

mainHR_v      = Value('i', 1)

#=======================================================================
# begin writing the video to disk if required
if args["mode"] == 2 and threadGPS is None:
	print("[INFO] : Configuring the process used to get GPS data")
	
	# initialize a frame queue
	getgpsQueue = Queue()

	# intialize a mutex
	mutexGPS = threading.Lock()

	#=======================================================================
	threadGPS = threading.Thread(target=getGPS_thread, args=(getgpsQueue, mutexGPS, args["verbose"], ))
	threadGPS.start()


#=======================================================================
# signal trap to handle keyboard interrupt
signal.signal(signal.SIGINT, signal_handler_CtrlC)

#=======================================================================
print("[INFO] : Starting human detection...")

# start the frames per second throughput estimator
fps = FPS().start()

#=======================================================================
# loop over frames from the video stream
while mainHR_v.value:
	# grab the next frame
	if not args.get("input", False):
		# read the frame from the camera 
		ret, frame = vs.read()

		if ret == False:
			print ("[Error] It was was impossible to aquire a frame!")
		else:        
			# flips the frame vertically to compensate the camera mount
			frame = cv2.flip(frame,0)   
	else: 
		frame = vs.read()
		frame = frame[1]

	# Having a video and we did not grab a frame then we
	# have reached the end of the video
	if frame is None:
		break
		
	# convert the frame from BGR to RGB for dlib
	rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)		

	# check to see if the frame dimensions are not set
	if W is None or H is None:
		# set the frame dimensions
		(H, W) = frame.shape[:2]
		
	#===================================================================
	# begin writing the video to disk if required
	if args["output"] is not None and writerProcess is None:
		print("[INFO] : Configuring the writing process")
		
		# set the value of the write flag (used here 
		# to start the imgs writing)
		writeVideo_v = Value('i', 1)	
	
		# initialize a frame queue and start the video writer
		frameWQueue = Queue()
		writerProcess = Process(target=write_video, 
			args=(args["output"], writeVideo_v, frameWQueue, W, H))
		writerProcess.start()	
		
	#===================================================================
	# begin streaming the video to the server if required
	if args["mode"] == 1 and streamProcess is None:
		print("[INFO] : Configuring the streaming process")
		
		# set the value of the write flag (used here 
		# to start the imgs streaming)
		streamVideo_v = Value('i', 1)	
	
		# initialize a frame queue and start the video writer
		frameSQueue = Queue()
		streamProcess = Process(target=stream_video, 
			args=(args["server_ip"], streamVideo_v, frameSQueue, jpeg_quality))
		streamProcess.start()			

	if noFrames % skip_frames == 0:
		dnnWork = 1

		# initialize a new set of detected human
		trackers = []
		confidences = []

		if args["verbose"] is not None:
			print(" ")
			print("[INFO] : Starting DNN ... ")

		# convert the frame to a blob 
		blob = cv2.dnn.blobFromImage(frame, size=(300, 300), ddepth=cv2.CV_8U)
		# print("First Blob: {}".format(blob.shape))
	
		# send the blob to the network
		net.setInput(blob, scalefactor=1.0/127.5, mean=[127.5, 127.5, 127.5])
	
		# pass the blob through the network and obtain the detections	
		networkOutput = net.forward()

		if args["verbose"] is not None:
			print("[INFO] : End DNN ... ")

		for detection in networkOutput[0, 0]:
				
			humanClass = int(detection[1])
			if CLASSES[humanClass] != "person":
				continue
		
			confidence = float(detection[2])
		
			# require a minimum confidence to reject fals positive detection
			if confidence > 0.35:
				
				confidences.append(confidence)
				
				# work on the current frame
				#====================================
				left   = int(detection[3]*W)
				top    = int(detection[4]*H)
				right  = int(detection[5]*W)
				bottom = int(detection[6]*H)
				
				#draw a red rectangle around detected objects
				cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), thickness=2)
				
				label = "{}: {:.2f}%".format("Confidence", confidence*100)
				y = top - 15 if top - 15 > 15 else top + 15
				cv2.putText(frame, label, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
				
				# prepare the following skip frames
				#====================================
				# construct a dlib rectangle object from the bounding
				# box coordinates and then start the dlib correlation
				# tracker
				tracker = dlib.correlation_tracker()
				rect = dlib.rectangle(left, top, right, bottom)
				tracker.start_track(rgb, rect)

				# add the tracker to our list of trackers so we can
				# utilize it during skip frames
				trackers.append(tracker)				
	else:
		dnnWork = 0
		i = 0
		# loop over the trackers
		for tracker in trackers:
			# update the tracker and grab the updated position
			tracker.update(rgb)
			pos = tracker.get_position()

			# unpack the position object
			left   = int(pos.left())
			top    = int(pos.top())
			right  = int(pos.right())
			bottom = int(pos.bottom())
			
			#draw a red rectangle around detected objects
			cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), thickness=2)
				
			label = "{}: {:.2f}%".format("Confidence", confidences[i]*100)
			y = top - 15 if top - 15 > 15 else top + 15
			cv2.putText(frame, label, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
			
			i +=1
		
	if args["mode"] == 0:
		if args["output"] is not None:
			# writing the video frame to the writing queue
			frameWQueue.put(frame)
		else:	
			# show the output frame
			cv2.imshow("Frame", frame)

	if args["mode"] == 1:
		# writing the video frame to the streaming queue
		frameSQueue.put(frame)

	if args["mode"] == 2:
		# if customMess_frames passed then send the custom message
		if noFrames % customMess_frames == 0:
			if dnnWork == 1:
				infoL = b'DNN'	
			else:
				infoL = b'tracking'

			if getgpsQueue.empty() is False:
				lat_lon_GPS = getgpsQueue.get()
				myLatitude  = lat_lon_GPS[0]
				myLongitude = lat_lon_GPS[1]

				if args["verbose"] is not None:
					print(" [Info] : Main prg. Lat. %s"%lat_lon_GPS[0]) 
					print(" [Info] : Main prg. Lon. %s"%lat_lon_GPS[1]) 

			#send custom mavlink message: video_monitor
			mutexGPS.acquire()
			hoverGames.mav.video_monitor_send(
				timestamp  = int(time.time() * 1e6),     # time in microseconds
				info       = infoL,
				lat        = myLatitude,
				lon        = myLongitude,
				no_people  = len(confidences),
				confidence = max(confidences) if len(confidences) != 0 else 0)
			mutexGPS.release()

	key = cv2.waitKey(1) & 0xFF
	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break

	# increment the total number of frames processed up to now
	noFrames += 1
	# update the FPS counter
	fps.update()

# stop the timer and display FPS information
fps.stop()
print("[INFO] : Elapsed time: {:.2f}".format(fps.elapsed()))
print("[INFO] : Approx. FPS:  {:.2f}".format(fps.fps()))

#=======================================================================
# release the video file pointer or video input stream
vs.release()

#=======================================================================
# terminate the video writer process
if writerProcess is not None and args["output"] is not None:
	writeVideo_v.value = 0
	writerProcess.join()

#=======================================================================
# terminate the video streaming process
if streamProcess is not None and args["mode"] == 1:
	streamVideo_v.value = 0
	streamProcess.join()

#=======================================================================
# close any open windows if exist
if args["output"] is None and args["mode"] == 0:
	print("[INFO] : Destroying the main graphical window.")
	cv2.destroyAllWindows()

#=======================================================================
# terminate all loop
mainHR_v.value = 0
threadGPS.join()
	
#=======================================================================
net.setPreferableTarget  (cv2.dnn.DNN_TARGET_CPU)
net.setPreferableBackend (cv2.dnn.DNN_BACKEND_OPENCV)	

print(" ")
print("[INFO] : The human recognition program finished!!!!")
