# USAGE: python server.py

# import the necessary packages
import imagezmq
import cv2

# initialize a ImageHub object
imageHub = imagezmq.ImageHub()

# start looping over all the frames
while True:
	# receive name and frame from the NavQ and acknowledge
	# the receipt
	(NavQ_name, frame) = imageHub.recv_image()
	imageHub.send_reply(b'OK')
	print("[INFO] receiving data from {}...".format(NavQ_name))

	# insert the sending device name on the frame
	cv2.putText(frame, NavQ_name, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

	# display the receiver image
	cv2.imshow(NavQ_name, frame)
    #  capture keypresses
	key = cv2.waitKey(1) & 0xFF

	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break

# do cleanup
cv2.destroyAllWindows()
