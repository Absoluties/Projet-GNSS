from datetime import datetime, timedelta
import serial
import serial.tools.list_ports
import signal
import sys
import time
import tkinter as tk

# Intégration de Matplotlib dans Tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# Dictionnaire global pour stocker le dernier timestamp d'apparition : { prn: timestamp }
satellites_status = {}


def stop():
    sys.exit(0)


signal.signal(signal.SIGINT, stop)


def verify_checksum(sentence):
    sentence = sentence.strip()
    if not sentence.startswith("$") or "*" not in sentence:
        return False, None, None
    try:
        data, received_checksum = sentence[1:].split("*")
    except ValueError:
        return False, None, None

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


def parse_gga(fields):
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


def parse_rmc(fields):
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


def parse_gsv(fields):
    sats = []
    for i in range(4, len(fields) - 3, 4):
        try:
            if not fields[i]:
                continue
            sat = {
                "prn": fields[i].zfill(2),
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
    if not valid:
        return

    body = sentence[1 : sentence.find("*")]
    fields = body.split(",")
    msg_type = fields[0][-3:]

    if msg_type == "GGA":
        pass  # Traitement GGA (si besoin de print, décommentez votre ancien code)
    elif msg_type == "RMC":
        pass  # Traitement RMC
    elif msg_type == "GSV":
        sats = parse_gsv(fields)
        for sat in sats:
            # Enregistrement du timestamp exact de détection
            satellites_status[sat["prn"]] = time.time()


class Interface:

    def __init__(self, root, serial_port):
        self.root = root
        self.ser = serial_port
        self.root.title("Chronogramme de Visibilité des Satellites GPS")
        self.root.geometry("800x600")

        # Heure de démarrage de l'application (sert de point de départ pour l'axe X)
        self.start_time_dt = datetime.now()

        # Structure pour stocker l'historique des segments temporels { "01": [[début, fin], [début, fin]], ... }
        self.sat_history = {f"{i:02d}": [] for i in range(1, 33)}
        # Pour savoir si un satellite est en cours d'enregistrement d'un segment continu
        self.active_segments = {f"{i:02d}": None for i in range(1, 33)}

        # --- Configuration de la figure Matplotlib ---
        # Style sombre/propre proche de votre image
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(expand=True, fill="both", padx=10, pady=10)

        # Initialisation du dessin fixe des axes
        self.setup_axes()

        # Boucles de rafraîchissement
        self.check_serial()
        self.update_plot()

    def setup_axes(self):
        """Configure les étiquettes fixes de l'axe Y (G01 à G32)"""
        self.ax.set_yticks(range(1, 33))
        self.ax.set_yticklabels([f"G{i:02d}" for i in range(1, 33)], fontsize=9)
        self.ax.set_ylim(0.5, 32.5)
        self.ax.invert_yaxis()  # Pour avoir G01 en haut et G32 en bas
        self.ax.set_ylabel("SATELLITE NO", fontweight="bold")
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        self.fig.autofmt_xdate()

    def check_serial(self):
        """Lit les trames GPS en arrière-plan sans geler la fenêtre"""
        if self.ser and self.ser.in_waiting > 0:
            try:
                while self.ser.in_waiting > 0:
                    line = self.ser.readline()
                    process_nmea(line.decode("ascii", errors="ignore"))
            except Exception as e:
                print(f"Erreur série : {e}")
        self.root.after(10, self.check_serial)

    def update_plot(self):
        """Calcule les présences et met à jour le graphique (toutes les 1s)"""
        now_ts = time.time()
        now_dt = datetime.now()
        timeout_threshold = 10.0  # Tolérance de 10s pour éviter le clignotement

        # 1. Mise à jour des segments temporels de présence
        for i in range(1, 33):
            prn = f"{i:02d}"
            last_seen = satellites_status.get(prn, 0)
            is_visible = (now_ts - last_seen) < timeout_threshold if last_seen > 0 else False

            if is_visible:
                if self.active_segments[prn] is None:
                    # Le satellite vient d'apparaître : on crée un nouveau segment [Début, Fin]
                    new_segment = [now_dt, now_dt]
                    self.sat_history[prn].append(new_segment)
                    self.active_segments[prn] = new_segment
                else:
                    # Toujours présent : on étire la fin du segment actuel jusqu'à maintenant
                    self.active_segments[prn][1] = now_dt
            else:
                # Le satellite a disparu (ou n'a pas encore été vu) : on ferme le segment actif
                self.active_segments[prn] = None

        # 2. Redessiner les lignes sur le graphique
        self.ax.clear()
        self.setup_axes()

        for i in range(1, 33):
            prn = f"{i:02d}"
            y_value = i
            for start, end in self.sat_history[prn]:
                # Si le segment est un point unique (court), on s'assure qu'il soit visible
                if start == end:
                    end = start + timedelta(seconds=1)
                # On trace la barre horizontale en vert fluo (comme sur votre image)
                self.ax.plot(
                    [start, end],
                    [y_value, y_value],
                    color="#00FF00",
                    linewidth=4,
                    solid_capstyle="butt",
                )

        # 3. Modification dynamique de l'échelle de temps (Axe X)
        # On affiche de l'heure de démarrage jusqu'à l'heure actuelle (avec une marge de 2 secondes)
        end_view = max(now_dt, self.start_time_dt + timedelta(seconds=10))
        self.ax.set_xlim(self.start_time_dt, end_view)

        # Rafraîchissement du composant graphique
        self.canvas.draw_idle()

        # On planifie la prochaine mise à jour dans 1 seconde
        self.root.after(1000, self.update_plot)
        
    def on_closing(self):
        # Sauvegarde simple du graphique
        self.fig.savefig("chronogramme.png", bbox_inches="tight")
        # Fermeture propre du port série et de la fenêtre
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()


if __name__ == "__main__":
    ports = serial.tools.list_ports.comports()
    ser = None

    if not len(ports):
        print("Aucun COM connecté.")
        sys.exit(1)
    elif len(ports) > 1:
        print("Ports disponibles :")
        for p in ports:
            print(f" - {p.device}")
        chosen_port = input("Port : ")
        ser = serial.Serial(chosen_port, 4800, timeout=0.1)
    else:
        ser = serial.Serial(ports[0][0], 4800, timeout=0.1)

    print(f"Connected to {ser.name}")

    root = tk.Tk()
    app = Interface(root, ser)

    # Fermeture propre lors du clic sur la croix rouge
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()