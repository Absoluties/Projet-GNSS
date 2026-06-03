from os import _exit
import signal
from queue import Queue
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.dates as mdates
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from time import sleep
from datetime import datetime
from sys import argv

from reader import SerialReader, TcpReader, FileReader
from parser import Parser
from math import radians, cos, sin

import numpy as np

def kill(sig, frame):
    _exit(1)

signal.signal(signal.SIGINT, kill)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _circle_segments(cx, cy, r, n=32):
    """Retourne les segments d'un cercle sous forme (2, n, 2) pour LineCollection."""
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pts = np.stack([cx + r * np.cos(theta), cy + r * np.sin(theta)], axis=1)  # (n, 2)
    return np.stack([pts, np.roll(pts, -1, axis=0)], axis=1)                  # (n, 2, 2)


def _make_hdop_segments(xs, ys, hdops, n=32):
    """Construit les segments de tous les cercles HDOP en une seule opération vectorisée."""
    xs = np.asarray(xs)
    ys = np.asarray(ys)
    rs = np.asarray(hdops) * 5.0
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    cos_t = np.cos(theta)   # (n,)
    sin_t = np.sin(theta)   # (n,)
    # (N, n) pour x et y
    cx = xs[:, None] + rs[:, None] * cos_t[None, :]
    cy = ys[:, None] + rs[:, None] * sin_t[None, :]
    pts = np.stack([cx, cy], axis=2)                  # (N, n, 2)
    segs = np.stack([pts, np.roll(pts, -1, axis=1)], axis=2)  # (N, n, 2, 2)
    return segs.reshape(-1, 2, 2)                     # (N*n, 2, 2)


# ---------------------------------------------------------------------------
# Trajectoire GPS
# ---------------------------------------------------------------------------

def init_position(ax: Axes):
    ax._lat0 = None
    ax._lon0 = None
    ax._processed = 0
    # Accumulateurs numpy
    ax._xs = np.empty(0)
    ax._ys = np.empty(0)
    ax._hdops = np.empty(0)
    # Stats incrémentales (Welford)
    ax._n = 0
    ax._mean_x = 0.0
    ax._mean_y = 0.0
    ax._M2_x = 0.0
    ax._M2_y = 0.0

    ax.set_title("Trajectoire GPS (Repère métrique local)")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_aspect('equal', adjustable='box')
    ax.grid()

    ax._line, = ax.plot([], [], 'ro', markersize=2, zorder=3)
    ax._hdop_lc = LineCollection([], colors='#c08080', linewidths=0.5, alpha=0.15, zorder=2)
    ax.add_collection(ax._hdop_lc)
    ax._barycenter_point, = ax.plot([], [], 'b+', markersize=10, markeredgewidth=2,
                                    label='Barycentre', zorder=5)
    ax._std_circle = plt.Circle((0, 0), 0, color='blue', fill=False,
                                linestyle='--', linewidth=1.2, label='Écart-type', zorder=4)
    ax.add_patch(ax._std_circle)
    ax._std_circle.set_visible(False)
    ax.legend(loc='upper left', fontsize=7)


def plot_position(ax: Axes, positions: list):
    new_points = positions[ax._processed:]
    if not new_points:
        return

    R = 6371000.0
    psi0 = radians(16)

    if ax._lat0 is None:
        ax._lat0 = new_points[0].lat
        ax._lon0 = new_points[0].lon

    cos_lat0 = cos(radians(ax._lat0))

    # Calcul vectorisé des nouveaux points
    lats = np.array([p.lat  for p in new_points])
    lons = np.array([p.lon  for p in new_points])
    hdops = np.array([p.hdop for p in new_points])

    dlat = np.radians(lats - ax._lat0)
    dlon = np.radians(lons - ax._lon0)
    dxs = np.round(R * ( cos(psi0) * cos_lat0 * dlon - sin(psi0) * dlat), 2)
    dys = np.round(R * ( sin(psi0) * cos_lat0 * dlon + cos(psi0) * dlat), 2)

    # Mise à jour Welford incrémentale (moyenne + variance sans tout recalculer)
    for x, y in zip(dxs, dys):
        ax._n += 1
        dx = x - ax._mean_x
        ax._mean_x += dx / ax._n
        ax._M2_x   += dx * (x - ax._mean_x)
        dy = y - ax._mean_y
        ax._mean_y += dy / ax._n
        ax._M2_y   += dy * (y - ax._mean_y)

    ax._xs    = np.concatenate([ax._xs,    dxs])
    ax._ys    = np.concatenate([ax._ys,    dys])
    ax._hdops = np.concatenate([ax._hdops, hdops])

    ax._line.set_data(ax._xs, ax._ys)

    # Cercles HDOP via LineCollection (un seul objet graphique)
    segs = _make_hdop_segments(ax._xs, ax._ys, ax._hdops)
    ax._hdop_lc.set_segments(segs)

    # Barycentre
    ax._barycenter_point.set_data([ax._mean_x], [ax._mean_y])

    # Écart-type 2D (Welford)
    if ax._n > 1:
        std = float(np.sqrt(ax._M2_x / ax._n + ax._M2_y / ax._n))
        ax._std_circle.set_center((ax._mean_x, ax._mean_y))
        ax._std_circle.set_radius(std)
        ax._std_circle.set_visible(True)

    ax.relim()
    ax.autoscale_view()
    ax._processed = len(positions)


# ---------------------------------------------------------------------------
# Erreur horizontale HDOP
# ---------------------------------------------------------------------------

def init_hdop(ax: Axes):
    ax._processed = 0
    ax.set_title("Incertitude horizontale (HDOP × 5 m)")
    ax.set_xlabel("Temps")
    ax.set_ylabel("Incertitude estimée (m)")
    ax.grid()
    ax._line, = ax.plot([], [], 'b-', linewidth=1)
    ax._times_num = np.empty(0)   # dates en float (mdates)
    ax._hdop_vals = np.empty(0)
    ax._fill = None


def plot_hdop(ax: Axes, positions: list):
    new_points = positions[ax._processed:]
    if not new_points:
        return

    new_nums  = np.array([mdates.date2num(p.time) for p in new_points])
    new_hdops = np.array([p.hdop * 5.0            for p in new_points])

    ax._times_num = np.concatenate([ax._times_num, new_nums])
    ax._hdop_vals = np.concatenate([ax._hdop_vals, new_hdops])

    ax._line.set_data(ax._times_num, ax._hdop_vals)

    # Mise à jour fill_between sans recréer l'objet
    if ax._fill is not None:
        ax._fill.remove()
    ax._fill = ax.fill_between(ax._times_num, ax._hdop_vals, alpha=0.2, color='blue')

    ax.relim()
    ax.autoscale_view()
    locator = mdates.AutoDateLocator(maxticks=10)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    ax._processed = len(positions)


# ---------------------------------------------------------------------------
# Visibilité satellites
# ---------------------------------------------------------------------------

def init_sat_histogramme(ax: Axes):
    ax._processed = 0
    ax._timestamps = {}
    ax._times_num  = {}
    ax._lines = {}
    ax.set_title("Visibilité satellites")
    ax.set_xlabel("Temps")
    ax.set_ylabel("PRN")
    ax.grid()


def plot_sat_histogramme(ax: Axes, sats: dict):
    timestamps = sats.get("timestamps", [])
    visibles   = sats.get("visibles",   [])

    new_timestamps = timestamps[ax._processed:]
    new_visibles   = visibles[ax._processed:]
    if not new_timestamps:
        return

    satellites_mis_a_jour = set()
    for t, sat_list in zip(new_timestamps, new_visibles):
        t_num = mdates.date2num(t)
        for sat_id in sat_list:
            if sat_id not in ax._times_num:
                ax._times_num[sat_id] = []
                ax._lines[sat_id], = ax.plot([], [], 'go', markersize=3)
            ax._times_num[sat_id].append(t_num)
            satellites_mis_a_jour.add(sat_id)

    sorted_ids = sorted(ax._times_num.keys())
    y_ticks = {sat_id: i for i, sat_id in enumerate(sorted_ids)}

    for sat_id in satellites_mis_a_jour:
        idx = y_ticks[sat_id]
        t_arr = np.array(ax._times_num[sat_id])
        y_arr = np.full(len(t_arr), idx)
        ax._lines[sat_id].set_data(t_arr, y_arr)

    if satellites_mis_a_jour:
        ax.relim()
        ax.autoscale_view()
        ax.set_yticks(range(len(sorted_ids)))
        ax.set_yticklabels([str(s) for s in sorted_ids])
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    ax._processed = len(timestamps)


# ---------------------------------------------------------------------------
# Skyplot
# ---------------------------------------------------------------------------

def init_sat_geoide(ax):
    ax._processed = {}   # {sat_id: nb points déjà tracés}
    ax._lines = {}
    ax.set_title("Skyplot satellites")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_rlim(90, 0)


def plot_sat_geoide(ax, sats):
    data = sats.get("data", {})
    if not data:
        return

    has_new_data = False
    has_new_satellite = False

    for sat_id, measurements in data.items():
        existing = ax._processed.get(sat_id, 0)
        new_pts  = measurements[existing:]
        if not new_pts:
            continue

        has_new_data = True
        if sat_id not in ax._lines:
            ax._lines[sat_id], = ax.plot([], [], 'o', markersize=2, label=f"SAT {sat_id}")
            has_new_satellite = True

        # Récupérer les données déjà tracées depuis la line
        prev_az, prev_el = ax._lines[sat_id].get_data()
        new_az = np.deg2rad([s.azimuth   for s in new_pts])
        new_el = [s.elevation for s in new_pts]

        all_az = np.concatenate([np.atleast_1d(prev_az), new_az])
        all_el = np.concatenate([np.atleast_1d(prev_el), new_el])
        ax._lines[sat_id].set_data(all_az, all_el)
        ax._processed[sat_id] = existing + len(new_pts)

    if has_new_data:
        ax.relim()
        ax.autoscale_view()
        if has_new_satellite:
            ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    trames = Queue()

    plt.ion()
    fig = plt.figure(figsize=(16, 10))
    ax1 = fig.add_subplot(221)
    ax2 = fig.add_subplot(222)
    ax3 = fig.add_subplot(223, projection="polar")
    ax4 = fig.add_subplot(224)
    plt.tight_layout(pad=3.0)
    plt.show()

    init_position(ax1)
    init_sat_histogramme(ax2)
    init_sat_geoide(ax3)
    init_hdop(ax4)

    if len(argv) == 2:
        reader = FileReader(trames, argv[1])
    else:
        reader = SerialReader(trames)
    reader.worker.start()

    parser = Parser(trames)
    parser.worker.start()

    while True:
        plot_position(ax1, parser.positions)
        plot_sat_histogramme(ax2, parser.satellites)
        plot_sat_geoide(ax3, parser.satellites)
        plot_hdop(ax4, parser.positions)

        fig.canvas.draw_idle()
        fig.canvas.flush_events()

        sleep(0.1)