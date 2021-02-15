from   pymavlink import mavutil
#import time

mavutil.set_dialect("video_monitor")

# create a  connection to FMU
hoverGames = mavutil.mavlink_connection("/dev/ttymxc2", baud=921600)

# wait for the heartbeat message to find the system id
hoverGames.wait_heartbeat()

print("Heartbeat from system (system %u component %u)" %(hoverGames.target_system, hoverGames.target_component))

while (True) :
    msg = hoverGames.recv_match(type='VIDEO_MONITOR', blocking=True)

    #check that the message is valid before attempting to use it
    if not msg:
        print('No message!\n')
        continue        
    if msg.get_type() == "BAD_DATA":
        if mavutil.all_printable(msg.data):
            sys.stdout.write(msg.data)
            sys.stdout.flush()
    else:
        #Message is valid, so use the attribute
        print('Info: %s'       % msg.info)
        print('Latitude : %d'  % msg.lat)
        print('Longitude: %d'  % msg.lon)
        print('No.people: %d'  % msg.no_people)
        print('Confidence: %f' % msg.confidence)
        print('\n')

#time.sleep(1.0):
