from   pymavlink import mavutil
import time

# create a  connection to FMU
hoverGames = mavutil.mavlink_connection("/dev/ttymxc2", baud=921600)

# wait for the heartbeat message to find the system id
hoverGames.wait_heartbeat()

print("Received heartbeat message from FMUK66...")

# Get some information !
while True:
	msg = hoverGames.recv_match()
	
	if not msg:
		continue
	if msg.get_type() == 'GPS_RAW_INT':
		print("\n\n*****Got message: %s*****"%msg.get_type())
		#print("Message: %s"%msg)
		#print("\nAs dictionary: %s"%msg.to_dict())

		print("\n Lat : %s"%msg.lat)
		print("\n Lon : %s"%msg.lat)
		print("\n eph : %s"%msg.eph)



