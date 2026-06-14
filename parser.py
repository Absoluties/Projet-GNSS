from dataclasses import dataclass
from queue import Queue
from datetime import datetime, date
from threading import Thread
import numpy as np

_INIT_CAPACITY = 65536

@dataclass
class Satellite:
    id:int
    elevation:float
    azimuth:float
    snr:float

class Parser:
    def __init__(self, queue:Queue):
        self.queue = queue

        cap = _INIT_CAPACITY
        self._pos_cap   = cap
        self.n     = 0          # nombre de points valides
        self.pos_time   = np.empty(cap, dtype='datetime64[ms]')
        self.pos_fix    = np.empty(cap, dtype=np.int8)
        self.pos_lat    = np.empty(cap, dtype=np.float64)
        self.pos_lon    = np.empty(cap, dtype=np.float64)
        self.pos_alt    = np.empty(cap, dtype=np.float32)
        self.pos_hdop   = np.empty(cap, dtype=np.float32)

        self.satellites:dict = {
            'timestamps': [],
            'visibles':   [],
            'data':       {}
        }
        self.gsv_buffer = []

        self.last_gga_time:datetime = None
        self._rmc_date:date         = None

        self.worker = Thread(target=self.job, daemon=True)

    @property
    def pos_count(self) -> int:
        return self.n

    def _grow_pos(self):
        new_cap = self._pos_cap * 2
        for attr, arr in [
            ('pos_time',  self.pos_time),
            ('pos_fix',   self.pos_fix),
            ('pos_lat',   self.pos_lat),
            ('pos_lon',   self.pos_lon),
            ('pos_alt',   self.pos_alt),
            ('pos_hdop',  self.pos_hdop),
        ]:
            new_arr = np.empty(new_cap, dtype=arr.dtype)
            new_arr[:self._pos_cap] = arr
            setattr(self, attr, new_arr)
        self._pos_cap = new_cap

    def verify_checksum(self, sentence):
        sentence = sentence.strip()
        if not sentence.startswith("$") or "*" not in sentence:
            return False
        data, received = sentence[1:].split("*")
        chk = 0
        for c in data:
            chk ^= ord(c)
        return f"{chk:02X}" == received.upper()

    def nmea_to_decimal(self, value, direction):
        if not value:
            return None
        raw     = float(value)
        degrees = int(raw / 100)
        decimal = degrees + (raw - degrees * 100) / 60
        if direction in ("S", "W"):
            decimal *= -1
        return decimal

    def parse_gga(self, fields):
        t = datetime.strptime(fields[0], "%H%M%S.%f").time()
        d = self._rmc_date if self._rmc_date is not None else date.today()
        dt = datetime.combine(d, t)

        fix_quality = int(fields[5])
        lat  = self.nmea_to_decimal(fields[1], fields[2])
        lon  = self.nmea_to_decimal(fields[3], fields[4])
        alt  = float(fields[8]) if fields[8] else 0.0
        hdop = float(fields[7]) if fields[7] else 1.0

        if lat and lon:
            if self.n >= self._pos_cap:
                self._grow_pos()
            i = self.n
            self.pos_time[i]  = np.datetime64(dt, 'ms')
            self.pos_fix[i]   = fix_quality
            self.pos_lat[i]   = lat
            self.pos_lon[i]   = lon
            self.pos_alt[i]   = alt
            self.pos_hdop[i]  = hdop
            self.n      += 1
            self.last_gga_time = dt

    def parse_rmc(self, fields):
        if fields[1] != 'A':
            return
        self._rmc_date = datetime.strptime(fields[8], "%d%m%y").date()

    def parse_gsv(self, fields):
        message_amount = int(fields[0])
        message_number = int(fields[1])
        n = (len(fields) - 3) // 4
        for i in range(n):
            j = 3 + 4 * i
            try:
                self.gsv_buffer.append(Satellite(
                    int(fields[j]),
                    float(fields[j+1]),
                    float(fields[j+2]),
                    float(fields[j+3])
                ))
            except Exception:
                pass

        if message_amount == message_number:
            ts = self.last_gga_time if self.last_gga_time is not None else datetime.now()
            self.satellites['timestamps'].append(ts)
            self.satellites['visibles'].append([s.id for s in self.gsv_buffer])
            for sat in self.gsv_buffer:
                if sat.id not in self.satellites['data']:
                    self.satellites['data'][sat.id] = []
                self.satellites['data'][sat.id].append(sat)
            self.gsv_buffer.clear()

    def job(self):
        while True:
            self.parse()

    def parse(self):
        trame = self.queue.get()
        if not self.verify_checksum(trame):
            return
        body   = trame[1:trame.index('*')]
        fields = body.split(",")
        match fields[0][-3:]:
            case "GGA": self.parse_gga(fields[1:])
            case "RMC": self.parse_rmc(fields[1:])
            case "GSV": self.parse_gsv(fields[1:])