# USAGE: python server_jpg.py

# import the necessary packages
import imagezmq
import cv2
import numpy as np

# initialize the ImageHub object
imageHub = imagezmq.ImageHub()

# start an infinit loop over all the frames
while True:
    # receive name and frame from the NavQ 
    navq_Name, jpg_buffer = imageHub.recv_jpg()
    imageHub.send_reply(b'OK')
    print("[INFO] receiving data from {}...".format(navq_Name))

    frame = cv2.imdecode(np.frombuffer(jpg_buffer, dtype='uint8'), -1)

    # draw the sending device name on the frame
    cv2.putText(frame, navq_Name, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # display and capture keypresses
    cv2.imshow(navq_Name, frame)

    # if the `q` key was pressed, break from the loop
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

# do basic cleanup
cv2.destroyAllWindows()
