#include <px4_platform_common/px4_config.h>
#include <px4_platform_common/posix.h>

#include <unistd.h>
#include <stdio.h>
#include <poll.h>
#include <string.h>

#include <uORB/uORB.h>
#include <uORB/topics/video_monitor.h>

extern "C" __EXPORT int uorb_mavlink_main(int argc, char *argv[]);

int uorb_mavlink_main(int argc, char *argv[])
{
	int poll_ret;
	int getOut = 1;
	//char c;

	PX4_INFO("Hello, I am only a test program able to receive VIDEO_MONITOR messages.");

	// Subscirbe to "video_monitor", then set a polling interval of 200ms
	int video_sub_fd = orb_subscribe(ORB_ID(video_monitor));
	orb_set_interval(video_sub_fd, 200);

	// Configure a POSIX POLLIN system to sleep the current thread until data appears on the topic
	px4_pollfd_struct_t fds_video;
	fds_video.fd     = video_sub_fd;
	fds_video.events = POLLIN;

	while (getOut)
	{
		poll_ret = px4_poll (&fds_video, 1, 2000);

		if ( poll_ret == 0 )
			{
			PX4_ERR ("Got no data within a second !");
			}
		// If it didn't return 0, we got data!
		else
		    // Double check that the data we recieved was in the right format (I think - need to check)
		    if(fds_video.revents & POLLIN)
		    	{
		    	// declare a video_monitor_s variable to store the data we will receive
		    	struct video_monitor_s videoMon;

		    	// Copy the obtaned data into the struct
		    	orb_copy(ORB_ID(video_monitor), video_sub_fd, &videoMon);

		    	printf ("lat = %d | long = %d | no. people = %d | confidence = %1.3f | %s \n",
		    			videoMon.lat, videoMon.lon, videoMon.no_people, (double)videoMon.confidence, videoMon.info);

		    	// Read stdin. If CTRL-C is entered, stop the loop  
		    	//read(0, &c, 1);
		    	//if (c == 0x03 || c == 0x63 || c == 'q')
				//	{ getOut = 0; }
			    }
	}

	return 0;
}
