from dataclasses import dataclass
from queue import Queue
from datetime import datetime, date
from threading import Thread

@dataclass
class Satellite:
    id:int
    elevation:float
    azimuth:float
    snr:float

@dataclass
class Position:
    time:datetime
    fix_quality:int
    lat:float
    lon:float
    altitude:float
    hdop:float

class Parser:
    def __init__(self, queue:Queue):
        self.queue = queue

        self.positions:list = []
        self.satellites:dict = {
            'timestamps': [],
            'visibles': [],
            'data': {}
        }
        self.gsv_buffer:list[Satellite] = []

        self.worker = Thread(target=self.job)
    
    def verify_checksum(self, sentence):
        sentence = sentence.strip()

        if not sentence.startswith("$") or "*" not in sentence:
            return False

        data, received_checksum = sentence[1:].split("*")

        checksum = 0
        for c in data:
            checksum ^= ord(c)

        calculated = f"{checksum:02X}"
        received = received_checksum.upper()

        return calculated == received

    def nmea_to_decimal(self, value, direction):
        if not value:
            return None

        raw = float(value)

        degrees = int(raw / 100)
        minutes = raw - (degrees * 100)

        decimal = degrees + minutes / 60

        if direction in ("S", "W"):
            decimal *= -1

        return decimal

    def parse_gga(self, fields:list[str]): # position brute
        time = datetime.combine(date.today(), datetime.strptime(fields[0], "%H%M%S.%f").time())
        fix_quality:int = int(fields[5])
        lat = self.nmea_to_decimal(fields[1], fields[2])
        lon = self.nmea_to_decimal(fields[3], fields[4])
        altitude = float(fields[8]) if fields[8] else 0.0
        hdop = float(fields[7]) if fields[7] else 1

        if lat and lon:
            self.positions.append(Position(time, fix_quality, lat, lon, altitude, hdop))

    def parse_gsv(self, fields:list[str]): # GSV = satellite visible
        message_amount:int = int(fields[0])
        message_number:int = int(fields[1])
        # satellites_amount:int = int(fields[2])
        n = (len(fields) - 3) // 4
        for i in range(n):
            j = 3 + 4 * i
            try:
                self.gsv_buffer.append(
                    Satellite(
                        int(fields[j]),
                        float(fields[j+1]),
                        float(fields[j+2]),
                        float(fields[j+3])
                    )
                )
            except Exception:
                print(f'Erreur dans la trame {fields}')
        
        if message_amount == message_number:
            self.satellites['timestamps'].append(datetime.now())
            self.satellites['visibles'].append([sat.id for sat in self.gsv_buffer])
            for sat in self.gsv_buffer:
                data = self.satellites['data']
                if sat.id not in data:
                    data[sat.id] = []
                data[sat.id].append(sat)
            self.gsv_buffer.clear()

    # def parse_rmc(fields): # navigation
    #     lat = nmea_to_decimal(fields[3], fields[4])
    #     lon = nmea_to_decimal(fields[5], fields[6])
    #
    #     return {
    #         "type": "RMC",
    #         "time": fields[1],
    #         "status": fields[2],
    #         "latitude": lat,
    #         "longitude": lon,
    #         "speed_knots": fields[7],
    #         "course_deg": fields[8],
    #         "date": fields[9],
    #     }

    def job(self):
        while True:
            self.parse()

    def parse(self):
        trame = self.queue.get()

        if not self.verify_checksum(trame):
            print('Invalid checksum.')
            return

        body = trame[1:trame.index('*')]
        fields = body.split(",")
        type_trame = fields[0][-3:]

        match type_trame:
            case "GGA":
                self.parse_gga(fields[1:])
            # case "RMC":
            #     self.parse_rmc(fields[:1])
            case "GSV":
                self.parse_gsv(fields[1:])
            case _:
                print(f"Type de trame non géré : {type_trame}")


