from os import _exit
from signal import signal, SIGINT
from queue import Queue
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from time import sleep
from sys import argv
from math import radians, cos, sin
from pyproj import Transformer
import numpy as np

from reader import SerialReader, TcpReader, FileReader
from parser import Parser

def kill(sig, frame):
    _exit(1)
signal(SIGINT, kill)



def _make_hdop_segments(xs, ys, hdops, n=32):
    """Segments de tous les cercles HDOP, vectorisé. (N*n, 2, 2)"""
    rs    = hdops * 5.0
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    cx = xs[:, None] + rs[:, None] * np.cos(theta)   # (N, n)
    cy = ys[:, None] + rs[:, None] * np.sin(theta)   # (N, n)
    pts  = np.stack([cx, cy], axis=2)                # (N, n, 2)
    segs = np.stack([pts, np.roll(pts, -1, axis=1)], axis=2)  # (N, n, 2, 2)
    return segs.reshape(-1, 2, 2)


def init_position(ax: Axes, parser: Parser, bornes=None):
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
    ax._bornes = bornes          # coordonnées Lambert-93 (E, N, H)
    ax._bornes_local = None      # coordonnées dans le repère local (calculées à la 1ʳᵉ position)
    ax._nearest_borne_idx = None # indice de la borne la plus proche du barycentre

    ax.set_title("Trajectoire GPS (Repère métrique local)")
    ax.set_xlabel("X (m)"); ax.set_ylabel("Y (m)")
    ax.set_aspect('equal', adjustable='box'); ax.grid()

    ax._line, = ax.plot([], [], 'ro', markersize=2, zorder=3)
    ax._hdop_lc = LineCollection([], colors='#c08080', linewidths=0.5, alpha=0.15, zorder=2)
    ax.add_collection(ax._hdop_lc)
    ax._barycenter_point, = ax.plot([], [], 'b+', markersize=10, markeredgewidth=2,
                                    label='Barycentre', zorder=5)
    ax._std_circle = plt.Circle((0, 0), 0, color='blue', fill=False,
                                linestyle='--', linewidth=1.2, zorder=4)
    ax.add_patch(ax._std_circle)
    ax._std_circle.set_visible(False)
    # Borne la plus proche (carré noir)
    ax._nearest_borne_plot, = ax.plot([], [], 'ks', markersize=10,
                                      markeredgewidth=2, label='Borne la plus proche', zorder=7)
    ax.legend(loc='best', ncol=1, fontsize=7, borderaxespad=0)


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
        # Convertir les bornes Lambert-93 → repère métrique local dès que l'origine est connue
        if ax._bornes:
            transformer_EN_latlon = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
            R_c = 6371000.0; ps0 = radians(16)
            clat0 = cos(radians(ax._lat0))
            bxs, bys = [], []
            for borne in ax._bornes:
                blon, blat = transformer_EN_latlon.transform(borne[0], borne[1])
                dl = radians(blat - ax._lat0)
                dg = radians(blon  - ax._lon0)
                bxs.append(round(R_c * ( cos(ps0) * clat0 * dg - sin(ps0) * dl), 2))
                bys.append(round(R_c * ( sin(ps0) * clat0 * dg + cos(ps0) * dl), 2))
            ax._bornes_local = (np.array(bxs), np.array(bys))

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

    # segs = _make_hdop_segments(ax._xs, ax._ys, ax._hdops)
    # ax._hdop_lc.set_segments(segs)

    ax._barycenter_point.set_data([ax._mean_x], [ax._mean_y])
    if ax._n > 1:
        std = float(np.sqrt(ax._M2_x / ax._n + ax._M2_y / ax._n))
        ax._std_circle.set_center((ax._mean_x, ax._mean_y))
        ax._std_circle.set_radius(std)
        ax._std_circle.set_visible(True)

    # Mettre à jour la borne la plus proche du barycentre courant
    if ax._bornes_local is not None:
        bxs, bys = ax._bornes_local
        dists = np.hypot(bxs - ax._mean_x, bys - ax._mean_y)
        idx = int(np.argmin(dists))
        if idx != ax._nearest_borne_idx:
            ax._nearest_borne_idx = idx
        ax._nearest_borne_plot.set_data([bxs[idx]], [bys[idx]])

    ax.relim(); ax.autoscale_view()
    ax._processed = n


def init_position_suivi(ax: Axes, parser: Parser):
    ax._processed = 0
    ax._lat0 = None
    ax._lon0 = None
    ax._xs = np.empty(0, dtype=np.float64)
    ax._ys = np.empty(0, dtype=np.float64)

    ax.set_title("Trajectoire GPS")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.locator_params(axis='both', nbins=6)
    
    cmap = LinearSegmentedColormap.from_list("blue_green", ["dodgerblue", "lightseagreen"])
    norm = Normalize(vmin=0, vmax=1)

    ax._gradient_lc = LineCollection([], cmap=cmap, norm=norm, linewidths=2, zorder=3)
    ax.add_collection(ax._gradient_lc)

    cbar = ax.figure.colorbar(ax._gradient_lc, ax=ax, fraction=0.046, pad=0.04)
    
    # On force uniquement deux graduations aux extrémités
    cbar.set_ticks([0, 1])
    cbar.set_ticklabels([r'$t_i$', r'$t_f$'])
    
    cbar.outline.set_edgecolor('white')
    cbar.ax.yaxis.set_tick_params(colors='white')


def plot_position_suivi(ax: Axes, parser: Parser):
    """Met à jour le graphique avec la trajectoire en dégradé de couleur."""
    n = parser.pos_count
    if n == 0 or n == ax._processed:
        return

    new_lats = parser.pos_lat[ax._processed:n]
    new_lons = parser.pos_lon[ax._processed:n]

    if ax._lat0 is None:
        ax._lat0 = float(new_lats[0])
        ax._lon0 = float(new_lons[0])

    R = 6371000.0
    psi0 = radians(270)
    cos_lat0 = cos(radians(ax._lat0))

    dlat = np.radians(new_lats - ax._lat0)
    dlon = np.radians(new_lons - ax._lon0)
    
    dxs = np.round(R * (cos(psi0) * cos_lat0 * dlon - sin(psi0) * dlat), 2)
    dys = np.round(R * (sin(psi0) * cos_lat0 * dlon + cos(psi0) * dlat), 2)

    ax._xs = np.concatenate([ax._xs, dxs])
    ax._ys = np.concatenate([ax._ys, dys])

    # Mise à jour de la ligne avec le dégradé
    if len(ax._xs) > 1:
        # Création des segments liant les points
        points = np.array([ax._xs, ax._ys]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        ax._gradient_lc.set_segments(segments)

        # On applique un tableau de valeurs allant de 0 (bleu, point le plus vieux) à 1 (vert, point le plus récent)
        ax._gradient_lc.set_array(np.linspace(0, 1, len(segments)))

    # Maintien dynamique de la vue
    if len(ax._xs) > 0:
        min_x_m = np.min(ax._xs) - 2.0
        max_x_m = np.max(ax._xs) + 2.0
        min_y_m = np.min(ax._ys) - 2.0
        max_y_m = np.max(ax._ys) + 2.0

        width = max_x_m - min_x_m
        height = max_y_m - min_y_m
        span = max(width, height)
        
        if span == 0:
            span = 4.0

        center_x = (min_x_m + max_x_m) / 2
        center_y = (min_y_m + max_y_m) / 2

        ax.set_xlim(center_x - span / 2, center_x + span / 2)
        ax.set_ylim(center_y - span / 2, center_y + span / 2)

    ax._processed = n


def init_donnees_parcours():
    """
    Initialise et retourne un dictionnaire contenant l'état des grandeurs physiques.
    Plus besoin de passer un objet graphique (ax) en paramètre.
    """
    return {
        "processed": 0,
        "distance_totale": 0.0,
        "denivele_positif": 0.0,
        "denivele_negatif": 0.0,
        "temps_ecoule": 0.0,
        "vitesse": 0.0,
        "vitesse_max": 0.0,
        "last_lat": None,
        "last_lon": None,
        "last_alt": None,
        "last_time": None,
        "start_time": None
    }


def donnees_parcours(etat: dict, parser: Parser):
    """
    Calcule l'évolution des grandeurs depuis le dernier appel.
    Retourne la distance, le temps (en secondes), le D+ et le D-.
    """
    n = parser.pos_count
    
    # S'il n'y a pas de nouveaux points, on retourne les valeurs actuelles
    if n == 0 or n == etat["processed"]:
        return etat["temps_ecoule"], etat["vitesse"], etat["vitesse_max"], etat["distance_totale"], etat["denivele_positif"], etat["denivele_negatif"]

    # Extraction des nouvelles données
    new_lats = parser.pos_lat[etat["processed"]:n]
    new_lons = parser.pos_lon[etat["processed"]:n]
    new_alts = parser.pos_alt[etat["processed"]:n]
    new_times = parser.pos_time[etat["processed"]:n]

    R = 6371000.0 # Rayon de la Terre

    # On itère sur chaque nouveau point reçu pour calculer le différentiel pas à pas
    for i in range(len(new_lats)):
        lat = float(new_lats[i])
        lon = float(new_lons[i])
        alt = float(new_alts[i])
        t = new_times[i]

        # Initialisation lors de la réception du tout premier point
        if etat["last_lat"] is None:
            etat["start_time"] = t
        else:
            # 1. Calcul de la distance entre le point (i-1) et le point (i)
            dlat = np.radians(lat - etat["last_lat"])
            dlon = np.radians(lon - etat["last_lon"])
            mean_lat = np.radians((lat + etat["last_lat"]) / 2.0)
            
            # Approximation locale (équirectangulaire) plus performante que Haversine
            dx = R * dlon * cos(mean_lat)
            dy = R * dlat
            dist_step = np.sqrt(dx**2 + dy**2)
            etat["distance_totale"] += dist_step
            
            # Calcul du dt
            try:
                # Si format numpy.datetime64
                dt_td = t - etat["last_time"]
                dt_sec = dt_td / np.timedelta64(1, 's')
            except TypeError:
                # Si format datetime classique
                dt_td = t - etat["last_time"]
                dt_sec = dt_td.total_seconds()
            
            if dt_sec > 0:
                vitesse = dist_step / dt_sec
                etat["vitesse"] = vitesse * 3.6
            else:
                etat["vitesse"] = 0.0
                
            if vitesse > etat["vitesse_max"]:
                etat["vitesse_max"] = vitesse * 3.6

            # 2. Calcul du dénivelé entre (i-1) et (i)
            dalt = alt - etat["last_alt"]
            if dalt > 0:
                etat["denivele_positif"] += dalt
            elif dalt < 0:
                etat["denivele_negatif"] += abs(dalt)

        etat["last_lat"] = lat
        etat["last_lon"] = lon
        etat["last_alt"] = alt
        etat["last_time"] = t
        
    # 3. Calcul du temps total écoulé (Dernier point reçu - Premier point reçu)
    if etat["start_time"] is not None:
        last_t = new_times[-1]
        try:
            # Si parser.pos_time stocke des numpy.datetime64 (le standard souvent utilisé)
            dt = last_t - etat["start_time"]
            etat["temps_ecoule"] = dt / np.timedelta64(1, 's')
        except TypeError:
            # Si ce sont des objets datetime.datetime natifs de Python
            dt = last_t - etat["start_time"]
            etat["temps_ecoule"] = dt.total_seconds()

    etat["processed"] = n

    return etat["temps_ecoule"], etat["vitesse"], etat["vitesse_max"], etat["distance_totale"], etat["denivele_positif"], etat["denivele_negatif"]


def init_hdop(ax: Axes):
    ax._processed = 0
    ax._times_num = np.empty(0, dtype=np.float64)
    ax._hdop_vals = np.empty(0, dtype=np.float32)

    ax.set_title("HDOP")
    ax.set_xlabel("Temps")
    ax.set_ylabel("HDOP")
    ax.grid()

    ax._line, = ax.plot([], [], 'b-', linewidth=1)
    ax._fill = None

    locator = mdates.AutoDateLocator(maxticks=10)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))


def plot_hdop(ax: Axes, parser: Parser):
    n = parser.pos_count
    if n == 0 or n == ax._processed:
        return

    new_times = parser.pos_time[ax._processed:n].astype('datetime64[ms]').astype(np.float64) / 86400000 + mdates.date2num(np.datetime64('1970-01-01'))
    new_hdops = parser.pos_hdop[ax._processed:n].astype(np.float32)

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
    parser = Parser(trames)

    # Positions géoréférencées Lambert-93 (E, N, H) — définies ici pour être
    # disponibles à l'initialisation du graphe et en fin de traitement.
    bornes = (
        (147_865.270, 6_839_340.067, 88.90-1), # 2
        (147_789.012, 6_839_356.525, 88.85-1), # 3
        (147_807.631, 6_839_347.831, 88.91-1), # 5
    )

    if '--noplot' not in argv:
        plt.ion()
        fig = plt.figure(figsize=(16, 10))
        ax1 = fig.add_subplot(221)
        ax2 = fig.add_subplot(222)
        ax3 = fig.add_subplot(223, projection="polar")
        ax4 = fig.add_subplot(224)
   
        plt.tight_layout(pad=3.0)
        plt.show()
        init_position(ax1, parser, bornes=bornes)
        init_sat_histogramme(ax2)
        init_sat_geoide(ax3)
        init_hdop(ax4)
        
    if '-f' in argv:
        reader = FileReader(trames, argv[argv.index('-f')+1])
    else:
        reader = SerialReader(trames)
    reader.worker.start()
    parser.worker.start()

    if '--noplot' not in argv:
        last_run = True
        while last_run:
            if reader.finish and trames.empty():
                last_run = False

            plot_position(ax1, parser)
            plot_sat_histogramme(ax2, parser.satellites)
            plot_sat_geoide(ax3, parser.satellites)
            plot_hdop(ax4, parser)

            fig.canvas.draw_idle()
            fig.canvas.flush_events()
            
            sleep(1)
    
        plt.ioff()
        plt.show()

    while not (reader.finish and trames.empty()):
        sleep(1)

    transformer_latlon_EN    = Transformer.from_crs("EPSG:4326",  "EPSG:2154", always_xy=True)  # WGS84 → Lambert-93

    xys = np.array(transformer_latlon_EN.transform(parser.pos_lon[:parser.n], parser.pos_lat[:parser.n]))
    zs = np.array(parser.pos_alt[:parser.n])

    def calcul_masque_filtre(donnees, seuil=3.0): # on utilise https://en.wikipedia.org/wiki/Median_absolute_deviation pour filtrer les valeurs aberrantes
        mediane = np.median(donnees)
        mad = np.median(np.abs(donnees - mediane))
        if mad == 0:  # Évite la division par zéro si toutes les valeurs sont identiques
            return np.ones(len(donnees), dtype=bool)
        score_z = 0.6745 * (donnees - mediane) / mad
        return np.abs(score_z) < seuil

    masque_x = calcul_masque_filtre(xys[0])
    masque_y = calcul_masque_filtre(xys[1])
    masque_z = calcul_masque_filtre(zs)
    masque = masque_x & masque_y & masque_z

    xys = xys[:, masque]
    zs = zs[masque]

    # horizontal
    barycentre_xy = xys.mean(axis=1)
    moyenne_z = zs.mean()
    std_xy = xys.std(axis=1)
    std_z = zs.std()
    distances_bornes = [np.linalg.norm([barycentre_xy[0]-borne[0], barycentre_xy[1]-borne[1]]) for borne in bornes]
    i = np.argmin(distances_bornes)
    distance_borne = distances_bornes[i]
    erreur_verticale_z = moyenne_z - bornes[i][2]

    print(f'Distance horizontal borne : {distance_borne} m, Écart-type des mesures : {100 * np.linalg.norm(std_xy)} cm')
    print(f'Distance vertical borne : {erreur_verticale_z} m, Écart-type des mesures : {100 * std_z} cm')
