import serial
import serial.tools.list_ports
import signal

"""
Exemple de trame :
$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
"""


def stop():
    exit()
signal.signal(signal.SIGINT, stop)

def verify_checksum(sentence):
    sentence = sentence.strip()

    if not sentence.startswith("$") or "*" not in sentence:
        return False, None, None

    data, received_checksum = sentence[1:].split("*")

    checksum = 0
    for c in data:
        checksum ^= ord(c)

    calculated = f"{checksum:02X}"
    received = received_checksum.upper()

    return calculated == received, calculated, received

def nmea_to_decimal(value, direction):
    if not value:
        return None

    raw = float(value)

    degrees = int(raw / 100)
    minutes = raw - (degrees * 100)

    decimal = degrees + minutes / 60

    if direction in ("S", "W"):
        decimal *= -1

    return decimal

### On fait une fonction par type de trame
def parse_gga(fields): # position brute
    lat = nmea_to_decimal(fields[2], fields[3])
    lon = nmea_to_decimal(fields[4], fields[5])

    return {
        "type": "GGA",
        "time": fields[1],
        "latitude": lat,
        "longitude": lon,
        "fix_quality": fields[6],
        "satellites_used": fields[7],
        "altitude_m": fields[9],
    }

def parse_rmc(fields): # navigation
    lat = nmea_to_decimal(fields[3], fields[4])
    lon = nmea_to_decimal(fields[5], fields[6])

    return {
        "type": "RMC",
        "time": fields[1],
        "status": fields[2],
        "latitude": lat,
        "longitude": lon,
        "speed_knots": fields[7],
        "course_deg": fields[8],
        "date": fields[9],
    }

def parse_gsv(fields): # GSV = satellite visible
    sats = []

    # Les satellites commencent à l'index 4 et occupent 4 champs
    for i in range(4, len(fields) - 3, 4):

        try:
            sat = {
                "prn": fields[i],
                "elevation": fields[i + 1],
                "azimuth": fields[i + 2],
                "snr": fields[i + 3],
            }

            sats.append(sat)

        except IndexError:
            break

    return sats

def process_nmea(sentence):
    valid, calc, recv = verify_checksum(sentence)

    print("=" * 70)
    print(sentence.strip())

    if not valid:
        print(f"[ERREUR] Checksum invalide ({recv} != {calc})")
        return

    print(f"[OK] Checksum valide : {recv}")

    # Supprime $ et checksum
    body = sentence[1:sentence.find("*")]
    fields = body.split(",")

    msg_type = fields[0][-3:]

    if msg_type == "GGA":

        data = parse_gga(fields)

        print("Position récepteur :")
        print(f"  Latitude  : {data['latitude']}")
        print(f"  Longitude : {data['longitude']}")
        print(f"  Altitude  : {data['altitude_m']} m")
        print(f"  Satellites utilisés : {data['satellites_used']}")

    elif msg_type == "RMC":

        data = parse_rmc(fields)

        print("Navigation :")
        print(f"  Latitude  : {data['latitude']}")
        print(f"  Longitude : {data['longitude']}")
        print(f"  Vitesse   : {data['speed_knots']} noeuds")
        print(f"  Date      : {data['date']}")

    elif msg_type == "GSV":

        sats = parse_gsv(fields)

        print("Satellites visibles :")

        for sat in sats:
            print(
                f"  PRN={sat['prn']}  "
                f"Elev={sat['elevation']}°  "
                f"Azimut={sat['azimuth']}°  "
                f"SNR={sat['snr']}"
            )

    else:
        print(f"Type de trame non géré : {msg_type}")

if __name__ == '__main__':
    ports = serial.tools.list_ports.comports()
    if not len(ports):
        print('Aucun COM connecté.')
        exit(1)
    elif len(ports) > 1:
        ser = serial.Serial(input('Port : '), 4800, timeout=1)
    else:
        ser = serial.Serial(ports[0][0], 4800, timeout=1)
    print(f"Connected to {ser.name}")
    # Read everything currently in the buffer
    while True:
        if ser.in_waiting > 0:
            try:
                bytes = ser.readline()
                process_nmea(bytes.decode('ascii'))
            except:
                continue
    