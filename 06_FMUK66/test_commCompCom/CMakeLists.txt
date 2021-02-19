px4_add_module(
	MODULE examples__test_commCompCom
	MAIN uorb_mavlink
	SRCS
		test_commCompCom.cpp
	DEPENDS
	)
