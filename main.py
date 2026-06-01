from os import _exit
import signal
from queue import Queue
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.axes import Axes
from time import sleep
from datetime import datetime
from sys import argv

from reader import SerialReader, TcpReader, FileReader
from parser import Parser
from math import radians, cos, sin

def kill(sig, frame):
    _exit(1)

signal.signal(signal.SIGINT, kill)


import math
from matplotlib.axes import Axes

import serial
import serial.tools.list_ports
from queue import Queue
from threading import Thread
from time import sleep

import socket
from queue import Queue
from threading import Thread

import numpy as np


def plot_position(ax: Axes, positions: list):
    if not positions:
        return

    # 1. INITIALISATION
    if not hasattr(ax, "_init"):
        ax._init = True
        ax._processed = 0
        ax._x = []
        ax._y = []
        
        ax._lat0 = None
        ax._lon0 = None
        
        ax.set_title("Trajectoire GPS (Repère métrique local)")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        ax.set_aspect('equal', adjustable='box')
        ax.grid()
        ax._line, = ax.plot([], [], 'ro', markersize=2)

    new_points = positions[ax._processed:]
    if not new_points:
        return

    if ax._lat0 is None:
        ax._lat0 = new_points[0].lat
        ax._lon0 = new_points[0].lon

    R = 6371000.0
    
    psi0 = radians(16)    # Angle à prendre en orientant le téléphone "vers l'avant" au moment de l'acquisition des données
    cos_lat0 = cos(radians(ax._lat0))

    # On prend les points relatifs à l'origine (point initial)
    for p in new_points:
        dx = round(R * (cos(psi0) * cos_lat0 * radians(p.lon - ax._lon0) - sin(psi0) * radians(p.lat - ax._lat0)),2)
        dy = round(R * (sin(psi0) * cos_lat0 * radians(p.lon - ax._lon0) + cos(psi0) * radians(p.lat - ax._lat0)),2)
        
        ax._x.append(dx)
        ax._y.append(dy)

    ax._line.set_data(ax._x, ax._y)
    ax.relim()
    ax.autoscale_view()
    
    ax._processed = len(positions)


def plot_sat_histogramme(ax: Axes, sats: dict):
    timestamps:list[datetime] = sats.get("timestamps", [])
    visibles = sats.get("visibles", [])

    if not timestamps:
        return

    if not hasattr(ax, "_init"):
        ax._init = True
        ax._processed = 0
        ax._timestamps = {}
        ax._lines = {}
        
        ax.set_title("Visibilité satellites")
        ax.set_xlabel("Temps")
        ax.set_ylabel("PRN")
        ax.grid()

    new_timestamps:list[datetime] = timestamps[ax._processed:]
    new_visibles = visibles[ax._processed:]

    if not new_timestamps:
        return

    satellites_mis_a_jour = set()

    for t, sat_list in zip(new_timestamps, new_visibles):
        for sat_id in sat_list:
            if sat_id not in ax._timestamps:
                ax._timestamps[sat_id] = []
                ax._lines[sat_id], = ax.plot([], [], 'go', markersize=3)
            
            ax._timestamps[sat_id].append(t)
            satellites_mis_a_jour.add(sat_id)

    sorted_ids = sorted(list(ax._timestamps.keys()))
    y_ticks = {sat_id: i for i, sat_id in enumerate(sorted_ids)}

    for sat_id in satellites_mis_a_jour:
        t = ax._timestamps[sat_id]
                
        index_y = y_ticks[sat_id]
        ordonnees_y = [index_y] * len(t)
        
        ax._lines[sat_id].set_data(t, ordonnees_y)

    if satellites_mis_a_jour:
        ax.relim()
        ax.autoscale_view()  
        ax.set_yticks(range(len(sorted_ids)))
        ax.set_yticklabels([str(sat_id) for sat_id in sorted_ids])
        locator = mdates.AutoDateLocator(maxticks=10)
        ax.xaxis.set_major_locator(locator)
        formatter = mdates.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(formatter)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    ax._processed = len(timestamps)


def plot_sat_geoide(ax, sats):
    data = sats.get("data", {})
    if not data:
        return

    if not hasattr(ax, "_init"):
        ax._init = True
        ax._azimuths = {}
        ax._elevations = {}
        ax._lines = {}
        ax.set_title("Skyplot satellites")
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_rlim(90, 0)

    has_new_data = False
    has_new_satellite = False

    for sat_id, measurements in data.items():
        if sat_id not in ax._azimuths:
            ax._azimuths[sat_id] = []
            ax._elevations[sat_id] = []
            # On crée l'unique ligne dédiée à CE satellite lors de sa première apparition
            ax._lines[sat_id], = ax.plot([], [], 'o', markersize=3, label=f"SAT {sat_id}")
            has_new_satellite = True

        existing = len(ax._azimuths[sat_id])

        new_points = measurements[existing:]

        if new_points:
            has_new_data = True
            new_az = [s.azimuth * 3.1415926535 / 180.0 for s in new_points]
            new_el = [s.elevation for s in new_points]
            
            ax._azimuths[sat_id].extend(new_az)
            ax._elevations[sat_id].extend(new_el)
            
            ax._lines[sat_id].set_data(ax._azimuths[sat_id], ax._elevations[sat_id])

    if has_new_data:
        ax.relim()
        ax.autoscale_view()
        
        if has_new_satellite:
            ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))


if __name__ == "__main__":
    trames = Queue()

    if len(argv) == 2:
        reader = FileReader(trames, argv[1])
    else:
        reader = SerialReader(trames)
    reader.worker.start()
    
    parser = Parser(trames)
    parser.worker.start()

    plt.ion()

    fig = plt.figure(figsize=(15, 5))
    ax1 = fig.add_subplot(131)
    ax2 = fig.add_subplot(132)
    ax3 = fig.add_subplot(133, projection="polar")

    plt.show()

    while True:
        plot_position(ax1, parser.positions)
        plot_sat_histogramme(ax2, parser.satellites)
        plot_sat_geoide(ax3, parser.satellites)
        
        fig.canvas.draw_idle()
        fig.canvas.flush_events()
        
        sleep(0.1)