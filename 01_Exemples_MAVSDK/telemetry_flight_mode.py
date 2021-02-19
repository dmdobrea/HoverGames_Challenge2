#!/usr/bin/env python3

import asyncio
from mavsdk import System


async def print_flight_mode():
    drone = System(mavsdk_server_address='localhost', port=50051)
    await drone.connect(system_address="serial:///dev/ttymxc2:921600")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"Drone discovered with UUID: {state.uuid}")
            break

    async for flight_mode in drone.telemetry.flight_mode():
        print("FlightMode:", flight_mode)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(print_flight_mode())
