import serial
import serial.tools.list_ports
from queue import Queue
from threading import Thread
from time import sleep

class Reader():
    def __init__(self, out:Queue):
        self.out:Queue = out
        ports = serial.tools.list_ports.comports()
        while not len(ports):
            self.ser = None
            print('Aucun COM connecté...')
            sleep(3)
        if len(ports) > 1:
            self.ser = serial.Serial(input('Donnez le nom du port serial à utiliser : '), 4800, timeout=1)
        else:
            self.ser = serial.Serial(ports[0][0], 4800, timeout=1)

        if self.ser is not None:
            print(f"Connected to {self.ser.name}")
            self.worker = Thread(target=self.job)

    def job(self):
        while True:
            self.readline_serial()

    def readline_serial(self):
        try:
            bytes = self.ser.readline()
            if bytes:
                self.out.put(bytes.decode('ascii'))
        except:
            pass
