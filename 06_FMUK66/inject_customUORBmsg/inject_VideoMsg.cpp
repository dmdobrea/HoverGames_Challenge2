#include <px4_platform_common/px4_config.h>
#include <px4_platform_common/posix.h>

#include <unistd.h>
#include <stdio.h>
#include <poll.h>
#include <string.h>

#include <uORB/uORB.h>
#include <uORB/topics/video_monitor.h>

extern "C" __EXPORT int inject_myUORB_main(int argc, char *argv[]);

int inject_myUORB_main(int argc, char *argv[])
{
	PX4_INFO("Hello, I am only a test program able to inject VIDEO_MONITOR messages.");

	// Declare structure to store data that will be sent
	struct video_monitor_s videoMon;

	// Clear the structure by filling it with 0s in memory
	memset(&videoMon, 0, sizeof(videoMon));

	// Create a uORB topic advertisement
	orb_advert_t video_monitor_pub = orb_advertise(ORB_ID(video_monitor), &videoMon);

	for (int i=0; i<40; i++)
		{
		char myStr[]={"Salut !!"};
		videoMon.timestamp  = hrt_absolute_time();
		videoMon.lat        = i;
		videoMon.lon        = 12345678;
		videoMon.no_people  = i+5;
		videoMon.confidence = 0.369;
		memcpy(videoMon.info, myStr, 9);

		orb_publish(ORB_ID(video_monitor), video_monitor_pub, &videoMon);

		//sleep for 2s
		usleep (2000000);
		}

	PX4_INFO("inject_myUORB finished!");

	return 0;
}
