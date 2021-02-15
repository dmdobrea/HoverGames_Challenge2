# USAGE:
#
# python human_recog.py --target cpu    --input videos/example_02.mp4
# python human_recog.py --target myriad --input videos/example_02.mp4

# import the necessary packages
from imutils.video import FPS
import argparse
import time
import cv2

from multiprocessing import Process
from multiprocessing import Queue
from multiprocessing import Value
import psutil

#=======================================================================
# Defines the affinities for main program & for the writting function
# So, main_prg => to core 2
#     main_wrt => to core 3
main_prg_core_affinity = 2
main_wrt_core_affinity = 3

#=======================================================================
def write_video(outputPath, writeVideo, frameQueue, W, H):
	p = psutil.Process()
	print(f"[INFO] : Writing process: {p}, affinity {p.cpu_affinity()}", flush=True)
	p.cpu_affinity([main_wrt_core_affinity])
        print(f"[INFO] : Writing process: {p}, affinity {p.cpu_affinity()}", flush=True)
	
	# initialize the FourCC and video writer object
	# fourcc = 4-byte code used to specify the video codec:
	# DIVX, XVID, MJPG, X264, WMV1, WMV2
	print("[INFO] : Configuring writing process.")
	fourcc = cv2.VideoWriter_fourcc(*"MJPG")						
	writer = cv2.VideoWriter (outputPath, fourcc, 30.0, (W, H), True)
	
	# loop while the write flag is set or the output frame queue is
	# not empty
	print("[INFO] : Starting writing process.")
	while writeVideo.value or not frameQueue.empty():
		# check if the output frame queue is not empty
		if not frameQueue.empty():
			# get the frame from the queue and write the frame
			frame = frameQueue.get()
			#print("[myINFO] Right now I'm write data...")
			writer.write(frame)

	# release the video writer object
	writer.release()
	print("[INFO] : Writer process => ended.")

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-t", "--target", type=str, required=True,
	choices=["myriad", "cpu"],
	help="target processor for object detection")
ap.add_argument("-i", "--input", type=str, required=True,
	help="path to the input video file")
ap.add_argument("-o", "--output", type=str,
	help="path to optional output video file")	
args = vars(ap.parse_args())

#=======================================================================
# Set afinity for main program
p = psutil.Process()
print(f"[INFO] : Main process: {p}, affinity {p.cpu_affinity()}", flush=True)
p.cpu_affinity([main_prg_core_affinity])
print(f"[INFO] : Main process: {p}, affinity {p.cpu_affinity()}", flush=True)

#=======================================================================
# initialize the list of class labels MobileNet SSD detects
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
	"bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
	"dog", "horse", "motorbike", "person", "pottedplant", "sheep",
	"sofa", "train", "tvmonitor"]

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

#=======================================================================
# Based on the input grab a reference to the video file
print("[INFO] : Opening input video file...")
vs = cv2.VideoCapture(args["input"])
	
#=======================================================================
# initialize the frame dimensions
W = None
H = None

#=======================================================================
writerProcess = None
writeVideo    = None
#frameQueue    = None
		
print("[INFO] : Starting human detection...")

# start the frames per second throughput estimator
fps = FPS().start()

#=======================================================================
# loop over frames from the video stream
while True:
	# grab the next frame and handle if we are reading from either
	# VideoCapture or VideoStream
	frame = vs.read()
	frame = frame[1]

	# Having a video and we did not grab a frame then we
	# have reached the end of the video
	if frame is None:
		break

	# check to see if the frame dimensions are not set
	if W is None or H is None:
		# set the frame dimensions
		(H, W) = frame.shape[:2]
		
	#===================================================================
	# begin writing the video to disk if required
	if args["output"] is not None and writerProcess is None:
		# set the value of the write flag (used here 
		# to start the imgs writing)
		writeVideo = Value('i', 1)	
	
		# initialize a frame queue and start the video writer
		frameQueue = Queue()
		writerProcess = Process(target=write_video, 
			args=(args["output"], writeVideo, frameQueue, W, H))
		writerProcess.start()		

	# convert the frame to a blob 
	blob = cv2.dnn.blobFromImage(frame, size=(300, 300), ddepth=cv2.CV_8U)
	# print("First Blob: {}".format(blob.shape))
	
	# send the blob to the network
	net.setInput(blob, scalefactor=1.0/127.5, mean=[127.5, 127.5, 127.5])
	
	# pass the blob through the network and obtain the detections	
	networkOutput = net.forward()

	for detection in networkOutput[0, 0]:
		
		humanClass = int(detection[1])
		if CLASSES[humanClass] != "person":
			continue
		
		confidence = float(detection[2])
		
		if confidence > 0.40:
			left   = detection[3]*W
			top    = detection[4]*H
			right  = detection[5]*W
			bottom = detection[6]*H
			
			#draw a red rectangle around detected objects
			cv2.rectangle(frame, (int(left), int(top)), (int(right), 
				int(bottom)), (0, 0, 255), thickness=2)
				
			label = "{}: {:.2f}%".format("Confidence", confidence*100)
			y = top - 15 if top - 15 > 15 else top + 15
			cv2.putText(frame, label, (int(left), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

	if args["output"] is not None:
		# writing the video frame to the queue
		frameQueue.put(frame)
	else:	
		# show the output frame
		cv2.imshow("Frame", frame)
		
	key = cv2.waitKey(1) & 0xFF
	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break

	# update the FPS counter
	fps.update()

# stop the timer and display FPS information
fps.stop()
print("[INFO] : Elapsed time: {:.2f}".format(fps.elapsed()))
print("[INFO] : Approx. FPS:  {:.2f}".format(fps.fps()))

#=======================================================================
# release the video file pointer
vs.release()

#=======================================================================
# terminate the video writer process
if writerProcess is not None:
	writeVideo.value = 0
	writerProcess.join()
	print("[INFO] : Init writer process end.")

# close any open windows
if args["output"] is None:
	print("[INFO] : Destroying the main graphical window.")
	cv2.destroyAllWindows()
	
	
net.setPreferableTarget  (cv2.dnn.DNN_TARGET_CPU)
net.setPreferableBackend (cv2.dnn.DNN_BACKEND_OPENCV)	

print(" ")
print("[INFO] : The human recognition program finished!!!!")
