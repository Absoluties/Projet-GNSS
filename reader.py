import serial
import serial.tools.list_ports
from queue import Queue
from threading import Thread
from time import sleep
import socket

class SerialReader():
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


class TcpReader:
    def __init__(self, out: Queue, host="172.20.10.1", port=11000):
        self.out: Queue = out
        self.host = host
        self.port = port
        self.worker = Thread(target=self.read_loop, daemon=True)

    def read_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"Connexion à {self.host}:{self.port}...")
        
        try:
            sock.connect((self.host, self.port))
            print("Connecté au smartphone !")
        except ConnectionRefusedError:
            print(f"Échec de connexion. Vérifie l'IP, le port et l'application.")
            return

        buffer = ""
        while True:
            try:
                data = sock.recv(4096).decode(errors="ignore")
                print(f"Données : {data}")
                if not data:
                    break

                buffer += data

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line.startswith("$"):
                        self.out.put(line)
                        # print(line) # Décommenter pour debug
            except Exception as e:
                print("Erreur de lecture TCP:", e)
                break