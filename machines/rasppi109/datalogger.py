""" Pressure and temperature logger """
# pylint: disable=R0904, C0103

import threading
import time
import logging
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.xgs600 as xgs600
import credentials

class PressureReader(threading.Thread):
    """ Pressure reader """
    def __init__(self, xgs):
        threading.Thread.__init__(self)
        self.xgs = xgs
        self.main_chamber = None
        self.flight_tube = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            self.main_chamber = None
            self.flight_tube = None
        else:
            if channel == 0:
                return self.flight_tube
            if channel == 1:
                return self.main_chamber
        return(self.pressure)

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(0.5)
            press = self.xgs.read_all_pressures()
            try:
                self.flight_tube = press[0]
                self.main_chamber = press[1]
            except IndexError:
                print "av"

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

xgs_instance = xgs600.XGS600Driver('/dev/ttyUSB0')
print xgs_instance.read_all_pressures()

pressure = PressureReader(xgs_instance)
pressure.start()

time.sleep(2.5)

codenames = ['tof_iongauge_ft', 'tof_iongauge_main']
loggers = {}
loggers[codenames[0]] = ValueLogger(pressure, comp_val = 0.1,
                                    comp_type = 'log', channel = 0)
loggers[codenames[0]].start()
loggers[codenames[1]] = ValueLogger(pressure, comp_val = 0.1,
                                    comp_type = 'log', channel = 1)
loggers[codenames[1]].start()

livesocket = LiveSocket('TOF data logger', codenames, 2)
livesocket.start()

db_logger = ContinuousLogger(table='dateplots_tof',
                             username=credentials.user,
                             password=credentials.passwd,
                             measurement_codenames=codenames)
db_logger.start()

while pressure.isAlive():
    time.sleep(0.25)
    for name in codenames:
        v = loggers[name].read_value()
        livesocket.set_point_now(name, v)
        if loggers[name].read_trigged():
            print v
            db_logger.enqueue_point_now(name, v)
            loggers[name].clear_trigged()