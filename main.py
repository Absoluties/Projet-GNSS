from os import _exit
import signal
from queue import Queue
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from time import sleep
from datetime import datetime
from sys import argv
from math import radians, cos, sin

import numpy as np

from reader import SerialReader, TcpReader, FileReader
from parser import Parser

def kill(sig, frame):
    _exit(1)
signal.signal(signal.SIGINT, kill)



def _make_hdop_segments(xs, ys, hdops, n=32):
    """Segments de tous les cercles HDOP, vectorisé. (N*n, 2, 2)"""
    rs    = hdops * 5.0
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    cx = xs[:, None] + rs[:, None] * np.cos(theta)   # (N, n)
    cy = ys[:, None] + rs[:, None] * np.sin(theta)   # (N, n)
    pts  = np.stack([cx, cy], axis=2)                # (N, n, 2)
    segs = np.stack([pts, np.roll(pts, -1, axis=1)], axis=2)  # (N, n, 2, 2)
    return segs.reshape(-1, 2, 2)


def init_position(ax: Axes, parser: Parser):
    ax._processed = 0
    ax._lat0 = None
    ax._lon0 = None
    ax._xs    = np.empty(0, dtype=np.float64)
    ax._ys    = np.empty(0, dtype=np.float64)
    ax._hdops = np.empty(0, dtype=np.float32)
    ax._n = 0
    ax._mean_x = 0.0
    ax._mean_y = 0.0
    ax._M2_x = 0.0
    ax._M2_y = 0.0

    ax.set_title("Trajectoire GPS (Repère métrique local)")
    ax.set_xlabel("X (m)"); ax.set_ylabel("Y (m)")
    ax.set_aspect('equal', adjustable='box'); ax.grid()

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


def plot_position(ax: Axes, parser: Parser):
    n = parser.pos_count
    if n == 0 or n == ax._processed:
        return

    new_lats  = parser.pos_lat [ax._processed:n]
    new_lons  = parser.pos_lon [ax._processed:n]
    new_hdops = parser.pos_hdop[ax._processed:n]

    if ax._lat0 is None:
        ax._lat0 = float(new_lats[0])
        ax._lon0 = float(new_lons[0])

    R        = 6371000.0
    psi0     = radians(16)
    cos_lat0 = cos(radians(ax._lat0))

    dlat = np.radians(new_lats - ax._lat0)
    dlon = np.radians(new_lons - ax._lon0)
    dxs  = np.round(R * ( cos(psi0) * cos_lat0 * dlon - sin(psi0) * dlat), 2)
    dys  = np.round(R * ( sin(psi0) * cos_lat0 * dlon + cos(psi0) * dlat), 2)

    # welford
    for x, y in zip(dxs, dys):
        ax._n += 1
        dx = x - ax._mean_x
        dy = y - ax._mean_y
        ax._mean_x += dx / ax._n
        ax._mean_y += dy / ax._n
        ax._M2_x += dx * (x - ax._mean_x)
        ax._M2_y += dy * (y - ax._mean_y)

    ax._xs    = np.concatenate([ax._xs,    dxs])
    ax._ys    = np.concatenate([ax._ys,    dys])
    ax._hdops = np.concatenate([ax._hdops, new_hdops])

    ax._line.set_data(ax._xs, ax._ys)

    segs = _make_hdop_segments(ax._xs, ax._ys, ax._hdops)
    ax._hdop_lc.set_segments(segs)

    ax._barycenter_point.set_data([ax._mean_x], [ax._mean_y])
    if ax._n > 1:
        std = float(np.sqrt(ax._M2_x / ax._n + ax._M2_y / ax._n))
        ax._std_circle.set_center((ax._mean_x, ax._mean_y))
        ax._std_circle.set_radius(std)
        ax._std_circle.set_visible(True)

    ax.relim(); ax.autoscale_view()
    ax._processed = n


def init_hdop(ax: Axes):
    ax._processed = 0
    ax._times_num = np.empty(0, dtype=np.float64)
    ax._hdop_vals = np.empty(0, dtype=np.float32)
    ax.set_title("Erreur horizontale (HDOP × 5 m)")
    ax.set_xlabel("Temps"); ax.set_ylabel("Erreur estimée (m)")
    ax.grid()
    ax._line, = ax.plot([], [], 'b-', linewidth=1)
    ax._fill = None


def plot_hdop(ax: Axes, parser: Parser):
    n = parser.pos_count
    if n == 0 or n == ax._processed:
        return

    new_times = parser.pos_time[ax._processed:n].astype('datetime64[ms]').astype(np.float64) / 86400000 + mdates.date2num(np.datetime64('1970-01-01'))
    new_hdops = parser.pos_hdop[ax._processed:n].astype(np.float32) * 5.0

    ax._times_num = np.concatenate([ax._times_num, new_times])
    ax._hdop_vals = np.concatenate([ax._hdop_vals, new_hdops])

    ax._line.set_data(ax._times_num, ax._hdop_vals)

    if ax._fill is not None:
        ax._fill.remove()
    ax._fill = ax.fill_between(ax._times_num, ax._hdop_vals, alpha=0.2, color='blue')

    ax.relim(); ax.autoscale_view()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    ax._processed = n


def init_sat_histogramme(ax: Axes):
    ax._processed = 0
    ax._times_num = {}
    ax._lines = {}
    ax.set_title("Visibilité satellites")
    ax.set_xlabel("Temps"); ax.set_ylabel("PRN")
    ax.grid()


def plot_sat_histogramme(ax: Axes, sats: dict):
    timestamps = sats.get("timestamps", [])
    visibles   = sats.get("visibles",   [])
    new_ts  = timestamps[ax._processed:]
    new_vis = visibles  [ax._processed:]
    if not new_ts:
        return

    updated = set()
    for t, sat_list in zip(new_ts, new_vis):
        t_num = mdates.date2num(t)
        for sat_id in sat_list:
            if sat_id not in ax._times_num:
                ax._times_num[sat_id] = []
                ax._lines[sat_id], = ax.plot([], [], 'go', markersize=3)
            ax._times_num[sat_id].append(t_num)
            updated.add(sat_id)

    sorted_ids = sorted(ax._times_num)
    y_pos = {sid: i for i, sid in enumerate(sorted_ids)}

    for sid in updated:
        t_arr = np.asarray(ax._times_num[sid])
        y_arr = np.full(len(t_arr), y_pos[sid])
        ax._lines[sid].set_data(t_arr, y_arr)

    ax.relim(); ax.autoscale_view()
    ax.set_yticks(range(len(sorted_ids)))
    ax.set_yticklabels([str(s) for s in sorted_ids])
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    ax._processed = len(timestamps)


def init_sat_geoide(ax):
    ax._processed = {}
    ax._az  = {}
    ax._el  = {}
    ax._lines = {}
    ax.set_title("Skyplot satellites")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_rlim(90, 0)


def plot_sat_geoide(ax, sats):
    data = sats.get("data", {})
    if not data:
        return
    has_new = False; new_sat = False
    for sat_id, measurements in data.items():
        existing = ax._processed.get(sat_id, 0)
        new_pts  = measurements[existing:]
        if not new_pts:
            continue
        has_new = True
        if sat_id not in ax._lines:
            ax._az[sat_id]  = np.empty(0)
            ax._el[sat_id]  = np.empty(0)
            ax._lines[sat_id], = ax.plot([], [], 'o', markersize=3, label=f"SAT {sat_id}")
            new_sat = True
        new_az = np.deg2rad([s.azimuth   for s in new_pts])
        new_el = np.array  ([s.elevation for s in new_pts])
        ax._az[sat_id] = np.concatenate([ax._az[sat_id], new_az])
        ax._el[sat_id] = np.concatenate([ax._el[sat_id], new_el])
        ax._lines[sat_id].set_data(ax._az[sat_id], ax._el[sat_id])
        ax._processed[sat_id] = existing + len(new_pts)
    if has_new:
        ax.relim(); ax.autoscale_view()
        if new_sat:
            ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))


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

    parser = Parser(trames)

    init_position(ax1, parser)
    init_sat_histogramme(ax2)
    init_sat_geoide(ax3)
    init_hdop(ax4)

    if len(argv) == 2:
        reader = FileReader(trames, argv[1])
    else:
        reader = SerialReader(trames)
    reader.worker.start()
    parser.worker.start()

    while True:
        plot_position(ax1, parser)
        plot_sat_histogramme(ax2, parser.satellites)
        plot_sat_geoide(ax3, parser.satellites)
        plot_hdop(ax4, parser)

        fig.canvas.draw_idle()
        fig.canvas.flush_events()
        sleep(0.1)