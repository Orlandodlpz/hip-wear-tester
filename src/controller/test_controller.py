from time import sleep
from tester_controller import TesterController, StationMode

tc = TesterController()
tc.set_station_mode(StationMode.S1)
tc.start_test()
print(tc.get_status_dict())

sleep(1.2)
tc.pause_test()
print(tc.get_status_dict())

sleep(0.5)
tc.resume_test()
sleep(0.7)
print(tc.get_status_dict())

tc.stop_test()
print(tc.get_status_dict())
