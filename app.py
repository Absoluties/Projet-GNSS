import flet as ft
from flet_charts import MatplotlibChart

import asyncio
from queue import Queue

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager

from reader import TcpReader, FileReader
from parser import Parser
from main import init_position_suivi, plot_position_suivi
from main import init_donnees_parcours, donnees_parcours
import numpy as np

import os
import glob
from datetime import datetime
from PIL import ImageGrab

from datetime import datetime



def main(page: ft.Page):
    page.title = "Stravo"
    page.window.width = 450
    page.window.height = 800
    page.window.resizable = False
    page.window.always_on_top = True
    
    # Polices d'écriture
    page.fonts = {
        "GoogleSans-Regular": "GoogleSans-Regular.ttf" ,
        "GoogleSans-Medium": "GoogleSans-Medium.ttf",
        "GoogleSans-SemiBold": "GoogleSans-SemiBold.ttf",
        "GoogleSans-Bold": "GoogleSans-Bold.ttf",
        "GoogleSans-Regular-Italic": "GoogleSans-Regular-Italic.ttf",
        "CedarvilleCursive-Regular": "CedarvilleCursive-Regular.ttf"
    }
    
    async def open_mes_parcours(e):
        await page.push_route("/mes_parcours")
    
    async def open_nouveau_parcours(e):
        await page.push_route("/nouveau_parcours")
        
    # --- LA FONCTION DE CAPTURE DE L'ACCUEIL ---
    async def capture_accueil(e):
        try:
            await asyncio.sleep(0.2)
            
            # --- CORRECTION DU ROGNAGE ---
            
            # 1. Ajuste cette valeur selon le "Zoom" dans les paramètres d'affichage de Windows
            # Si tu es à 100%, mets 1.0. Si tu es à 125%, mets 1.25, etc.
            zoom = 1.5 
            
            # 2. Correction des bordures Windows (Barre de titre en haut, ombres sur les côtés)
            marge_haut = int(35 * zoom) # Hauteur moyenne de la barre Windows
            marge_cote = int(8 * zoom)  # Épaisseur de l'ombre/bordure
            
            # 3. Calcul des coordonnées physiques exactes de l'intérieur de l'app
            x = int(page.window.left * zoom) + marge_cote
            y = int(page.window.top * zoom) + marge_haut
            
            # Largeur et hauteur utiles
            w = int(page.window.width * zoom) - (marge_cote * 2)
            h = int(page.window.height * zoom) - marge_haut - marge_cote
            
            bbox = (x, y, x + w, y + h)
            capture = ImageGrab.grab(bbox)
            
            # -----------------------------
            
            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            nom_fichier = f"assets/accueil_{timestamp}.png"
            capture.save(nom_fichier)
            print(f"Capture de l'accueil réussie : {nom_fichier}")
            
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Capture de l'accueil sauvegardée !", color="#ff7800", font_family="GoogleSans-Bold"),
                bgcolor="#ffffff",
                duration=2000 
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as err:
            print(f"Erreur lors de la capture d'écran : {err}")
            
    # --- LA FONCTION DE CAPTURE DE "NOUVEAU PARCOURS" ---
    async def capture_nouveau_parcours(e):
        try:
            await asyncio.sleep(0.2)
            
            # --- CORRECTION DU ROGNAGE ---
            
            # 1. Ajuste cette valeur selon le "Zoom" dans les paramètres d'affichage de Windows
            # Si tu es à 100%, mets 1.0. Si tu es à 125%, mets 1.25, etc.
            zoom = 1.5 
            
            # 2. Correction des bordures Windows (Barre de titre en haut, ombres sur les côtés)
            marge_haut = int(35 * zoom) # Hauteur moyenne de la barre Windows
            marge_cote = int(8 * zoom)  # Épaisseur de l'ombre/bordure
            
            # 3. Calcul des coordonnées physiques exactes de l'intérieur de l'app
            x = int(page.window.left * zoom) + marge_cote
            y = int(page.window.top * zoom) + marge_haut
            
            # Largeur et hauteur utiles
            w = int(page.window.width * zoom) - (marge_cote * 2)
            h = int(page.window.height * zoom) - marge_haut - marge_cote
            
            bbox = (x, y, x + w, y + h)
            capture = ImageGrab.grab(bbox)
            
            # -----------------------------
            
            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            nom_fichier = f"assets/nouveau_parcours_{timestamp}.png"
            capture.save(nom_fichier)
            print(f"Capture du nouveau parcours réussie : {nom_fichier}")
            
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Capture du nouveau parcours sauvegardée !", color="#ff7800", font_family="GoogleSans-Bold"),
                bgcolor="#ffffff",
                duration=2000 
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as err:
            print(f"Erreur lors de la capture d'écran : {err}")
        
    # --- LA FONCTION DE CAPTURE DE "MES PARCOURS" ---
    async def capture_mes_parcours(e):
        try:
            await asyncio.sleep(0.2)
            
            # --- CORRECTION DU ROGNAGE ---
            
            # 1. Ajuste cette valeur selon le "Zoom" dans les paramètres d'affichage de Windows
            # Si tu es à 100%, mets 1.0. Si tu es à 125%, mets 1.25, etc.
            zoom = 1.5 
            
            # 2. Correction des bordures Windows (Barre de titre en haut, ombres sur les côtés)
            marge_haut = int(35 * zoom) # Hauteur moyenne de la barre Windows
            marge_cote = int(8 * zoom)  # Épaisseur de l'ombre/bordure
            
            # 3. Calcul des coordonnées physiques exactes de l'intérieur de l'app
            x = int(page.window.left * zoom) + marge_cote
            y = int(page.window.top * zoom) + marge_haut
            
            # Largeur et hauteur utiles
            w = int(page.window.width * zoom) - (marge_cote * 2)
            h = int(page.window.height * zoom) - marge_haut - marge_cote
            
            bbox = (x, y, x + w, y + h)
            capture = ImageGrab.grab(bbox)
            
            # -----------------------------
            
            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            nom_fichier = f"assets/mes_parcours_{timestamp}.png"
            capture.save(nom_fichier)
            print(f"Capture de mes parcours réussie : {nom_fichier}")
            
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Capture de l'accueil sauvegardée !", color="#ff7800", font_family="GoogleSans-Bold"),
                bgcolor="#ffffff",
                duration=2000 
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as err:
            print(f"Erreur lors de la capture d'écran : {err}")
    
    def route_change():
        page.views.clear()
        page.views.append(
            ft.View(
                bgcolor = "#ff7800",
                route = "/",
                
                # --- Le bouton flottant avec le paramètre universel 'content' ---
                floating_action_button = ft.FloatingActionButton(
                    content = ft.Text("", color="#ff7800", font_family="GoogleSans-Medium"),           
                    bgcolor = "#ffffff",         
                    shape = ft.RoundedRectangleBorder(radius=30),
                    width = 15,
                    height = 15,
                    elevation = 0,
                    hover_elevation = 0,
                    highlight_elevation = 0,
                    on_click = capture_accueil
                ),
                
                controls = [
                    ft.SafeArea(
                        expand = True,
                        
                        # Contenu de la page
                        content = ft.Column(
                            alignment = ft.MainAxisAlignment.CENTER,
                            horizontal_alignment = ft.CrossAxisAlignment.CENTER,
                            
                            controls = [

                                # Texte avant logo
                                ft.Text(
                                    "Merci pour les ...",
                                    color = "#ffffff",
                                    size = 15,
                                    font_family = "CedarvilleCursive-Regular"
                                ),
                                
                                # Logo
                                ft.Text(
                                    "Stravo",
                                    color = "#ffffff",
                                    size = 60,
                                    font_family = "GoogleSans-Medium",
                                    style = ft.TextStyle(
                                        height=0.75
                                    ),
                                ),
    
                                ft.Container(height = 30),
                                
                                # Boutons
                                ft.Row(
                                    alignment = ft.MainAxisAlignment.CENTER,
                                    controls = [
                                        
                                        # Bouton "Mes parcours"
                                         ft.OutlinedButton(
                                            on_click = open_mes_parcours,
                                            content = ft.Text(
                                                "Mes parcours",
                                                color = "#ffffff",
                                                size = 15,
                                                font_family = "GoogleSans-Regular"
                                            ),
                                            style = ft.ButtonStyle(
                                                color = "#ffffff",
                                                side = ft.BorderSide(width = 1, color = "#ffffff"),
                                                shape = ft.RoundedRectangleBorder(radius = 15), 
                                            )
                                        ),
                                        
                                        # Bouton "Nouveau parcours"
                                        ft.OutlinedButton(
                                            on_click = open_nouveau_parcours,
                                            content = ft.Text(
                                                "Nouveau parcours",
                                                color = "#ffffff",
                                                size = 15,
                                                font_family = "GoogleSans-Regular"
                                            ),
                                            style = ft.ButtonStyle(
                                                color = "#ffffff",
                                                side = ft.BorderSide(width = 1, color = "#ffffff"),
                                                shape = ft.RoundedRectangleBorder(radius = 15)
                                            )
                                        )
                                    ]
                                )
                            ]
                        )
                    )
                ]
            )
        )
        if page.route == "/mes_parcours":
            # --- 1. SCAN DU DOSSIER ---
            # On cherche tous les fichiers .png dans le dossier historique
            fichiers_sauvegardes = glob.glob("assets/nouveau_parcours*.png")
            
            # On les trie à l'envers pour avoir les captures les plus récentes en haut de l'écran
            fichiers_sauvegardes.sort(reverse=True) 

            def formater_nom_parcours(nom_fichier):
                # 1. On nettoie les préfixes ou extensions éventuels
                texte_brut = nom_fichier.replace("nouveau_parcours_", "").replace(".png", "")
                
                # 2. On transforme le texte "14-06-2026_18-32-09" en objet temporel compréhensible par Python
                dt = datetime.strptime(texte_brut, "%d-%m-%Y_%H-%M-%S")
                
                # 3. On crée un dictionnaire des mois en français (l'index 0 est vide pour que 1 = janvier)
                mois_fr = ["", "janvier", "février", "mars", "avril", "mai", "juin", 
                        "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
                
                # 4. Petite règle grammaticale française : on dit "1er" et non "1"
                jour = "1er" if dt.day == 1 else str(dt.day)
                
                # 5. On assemble la phrase finale (le :02d permet de forcer "09" au lieu de "9" pour les minutes)
                return f"Parcours du {jour} {mois_fr[dt.month]} {dt.year}, à {dt.hour}h{dt.minute:02d}"

            # --- 2. CRÉATION DES CARTES VISUELLES ---
            liste_cartes = []
            
            if not fichiers_sauvegardes:
                # S'il n'y a aucune image
                liste_cartes.append(
                    ft.Text("Aucun parcours enregistré pour le moment.", color="#ffffff", size=15, font_family="GoogleSans-Regular")
                )
            else:
                # On boucle sur chaque image trouvée pour créer un conteneur
                for chemin in fichiers_sauvegardes:
                    nom_fichier = os.path.basename(chemin)
                    
                    # Le chemin src pour Flet (qui part du dossier assets/)
                    src_flet = f"{nom_fichier}"
                    
                    # Nettoyage du nom pour faire un joli titre (ex: "parcours_12-06-2026.png" -> "12-06-2026")
                    titre_propre = formater_nom_parcours(nom_fichier)

                    carte = ft.Container(
                        bgcolor="#ffffff",
                        border_radius=15,
                        padding=5,
                        # margin=ft.margin.only(bottom=20), # Espace entre chaque parcours
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(height=2.5, width=0),
                                ft.Text(f"{titre_propre}", color="#ff7800", size=15, font_family="GoogleSans-Regular"),
                                # L'image elle-même
                                ft.Image(src=src_flet, width=350, fit="contain", border_radius=10)
                            ]
                        )
                    )
                    liste_cartes.append(carte)

            # --- 3. AFFICHAGE DE LA PAGE ---
            page.views.append(
                ft.View(
                    bgcolor = "#ff7800",
                    route="/mes_parcours",
                    
                    # --- Le bouton flottant avec le paramètre universel 'content' ---
                    floating_action_button = ft.FloatingActionButton(
                        content = ft.Text("", color="#ff7800", font_family="GoogleSans-Medium"),           
                        bgcolor = "#ffffff",         
                        shape = ft.RoundedRectangleBorder(radius=30),
                        width = 15,
                        height = 15,
                        elevation = 0,
                        hover_elevation = 0,
                        highlight_elevation = 0,
                        on_click = capture_mes_parcours
                    ),
                    
                    scroll=ft.ScrollMode.AUTO, # INDISPENSABLE : permet de faire défiler l'écran vers le bas
                    controls = [
                        ft.SafeArea(
                            expand = True,
                            content = ft.Column(
                                alignment = ft.MainAxisAlignment.START, # On aligne tout en haut
                                horizontal_alignment = ft.CrossAxisAlignment.CENTER,
                                controls = [
                                    ft.AppBar(
                                        title = ft.Text("Mes parcours", color="#ffffff", size=15, font_family="GoogleSans-Regular"),
                                        center_title = True,
                                        bgcolor = "#ff7800",
                                        color = "#ffffff"
                                    ),
                                    
                                    ft.Container(height=15),
                                    
                                    # On injecte ici notre liste de cartes générée plus haut !
                                    ft.Column(
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        spacing=30,
                                        controls=liste_cartes
                                    ),
                                    
                                    ft.Container(height=37.5)
                                ]
                            )
                        )
                    ]
                )
            )
        if page.route == "/nouveau_parcours":
            
            font_path = "assets/GoogleSans-Regular.ttf"
            font_manager.fontManager.addfont(font_path)
            custom_font = font_manager.FontProperties(fname=font_path).get_name()
            
            # On force tout le texte à utiliser cette police, cette taille et cette couleur
            plt.rcParams.update({
                'font.family': custom_font,
                'font.size': 12,             # Taille de base
                'axes.titlesize': 12,        # Taille du titre
                'axes.labelsize': 9,        # Taille des labels X et Y
                'xtick.labelsize': 9,       # Taille des nombres sur l'axe X
                'ytick.labelsize': 9,       # Taille des nombres sur l'axe Y
                'legend.fontsize': 9,       # Taille du texte de la légende
                'text.color': 'white',       # Couleur globale du texte
                'axes.labelcolor': 'white',  # Couleur des labels
                'xtick.color': 'white',      # Couleur des graduations X
                'ytick.color': 'white',      # Couleur des graduations Y
                'legend.facecolor': 'none',  # Fond de la légende transparent
                'legend.edgecolor': 'white', # Contour de la boîte de légende en blanc
                'legend.labelcolor': 'white', # Texte de la légende en blanc
                'axes.edgecolor': 'white'
            })
            # -------------------------------------------------------------
            
            trames_queue = Queue()
            reader = TcpReader(trames_queue, host="172.20.10.1", port=11000)
            parser_gnss = Parser(trames_queue)
            
            fig, ax1 = plt.subplots(figsize=(4, 4), layout='tight')
            
            ax1.set_xlim(-10, 10)
            ax1.set_ylim(-10, 10)
            
            # --- LA NOUVELLE ASTUCE TRANSPARENCE ---
            fig.patch.set_facecolor('none') # Rend le contour de la figure transparent
            ax1.set_facecolor('none')       # Rend le fond du quadrillage transparent
            ax1.grid(False)
            
            init_position_suivi(ax1, parser_gnss) # Ta fonction s'occupe de créer les axes, titres, points...
            
            # ax1.plot([-10, 10], [-10, 10], color='black')
            # -------------------------------

            gps_chart = MatplotlibChart(figure = fig, expand = True)

            # État du tracking (on utilise un dictionnaire pour le modifier facilement dans les fonctions imbriquées)
            tracking_state = {"running": False}
            reader_instance = {"reader": None}



            # 1. Création des variables de texte pour l'affichage dynamique
            text_dist = ft.Text("0.0 m", size=15, color="#ffffff", font_family="GoogleSans-Regular")
            text_temps = ft.Text("00:00", size=15, color="#ffffff", font_family="GoogleSans-Regular")
            text_dplus = ft.Text("+0.0 m", size=15, color="#ffffff", font_family="GoogleSans-Regular")
            text_dmoins = ft.Text("-0.0 m", size=15, color="#ffffff", font_family="GoogleSans-Regular")
            text_vitesse = ft.Text("0.0 km/h", size=15, color="#ffffff", font_family="GoogleSans-Regular")
            text_vitesse_max = ft.Text("0.0 km/h", size=15, color="#ffffff", font_family="GoogleSans-Regular")

            # 2. Structure du tableau avec largeur fixe (2 lignes, 3 colonnes)
            largeur_cellule = 110  # On fixe la largeur pour aligner les colonnes

            table_donnees = ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20, # Espace vertical entre les deux lignes
                controls=[
                    # --- PREMIÈRE LIGNE ---
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=15, # Espace horizontal entre les cellules
                        controls=[
                            ft.Container(
                                width=largeur_cellule,
                                content=ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=2,
                                    controls=[
                                        ft.Text("Temps", size=15, color="#ffffff", font_family="GoogleSans-Regular"),
                                        text_temps
                                    ]
                                )
                            ),
                            ft.Container(
                                width=largeur_cellule,
                                content=ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=2,
                                    controls=[
                                        ft.Text("Vitesse", size=15, color="#ffffff", font_family="GoogleSans-Regular"),
                                        text_vitesse
                                    ]
                                )
                            ),
                            ft.Container(
                                width=largeur_cellule,
                                content=ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=2,
                                    controls=[
                                        ft.Text("D+", size=15, color="#ffffff", font_family="GoogleSans-Regular"),
                                        text_dplus
                                    ]
                                )
                            )
                        ]
                    ),
                    # --- DEUXIÈME LIGNE ---
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=15,
                        controls=[
                            ft.Container(
                                width=largeur_cellule,
                                content=ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=2,
                                    controls=[
                                        ft.Text("Distance", size=15, color="#ffffff", font_family="GoogleSans-Regular"),
                                        text_dist
                                    ]
                                )
                            ),
                            ft.Container(
                                width=largeur_cellule,
                                content=ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=2,
                                    controls=[
                                        ft.Text("Vitesse max", size=15, color="#ffffff", font_family="GoogleSans-Regular"),
                                        text_vitesse_max
                                    ]
                                )
                            ),
                            ft.Container(
                                width=largeur_cellule,
                                content=ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=2,
                                    controls=[
                                        ft.Text("D-", size=15, color="#ffffff", font_family="GoogleSans-Regular"),
                                        text_dmoins
                                    ]
                                )
                            )
                        ]
                    )
                ]
            )



            # On sort le bouton de la liste 'controls' pour pouvoir y faire référence
            tracking_button = ft.OutlinedButton(
                content = ft.Text(
                    "Démarrer le tracking",
                    color = "#ffffff",
                    size = 15,
                    font_family = "GoogleSans-Regular"
                ),
                style = ft.ButtonStyle(
                    color = "#ffffff",
                    side = ft.BorderSide(width = 1, color = "#ffffff"),
                    shape = ft.RoundedRectangleBorder(radius = 15)
                )
            )

            async def update_gps_loop():
                reader_instance["reader"] = reader # Sauvegarde la référence
                
                reader.worker.start()
                parser_gnss.worker.start()

                # Importation et initialisation du dictionnaire d'état des grandeurs
                etat_tracker = init_donnees_parcours()

                while tracking_state["running"]:
                    points_avant = ax1._processed 
                    
                    plot_position_suivi(ax1, parser_gnss)
                    
                    # Récupération des données calculées pas à pas
                    temps, vitesse, vitesse_max, dist, d_plus, d_moins = donnees_parcours(etat_tracker, parser_gnss)
                    
                    # 1. Formatage de la distance (passage en km si supérieur à 1000m)
                    if dist < 1000:
                        text_dist.value = f"{dist:.1f} m"
                    else:
                        text_dist.value = f"{dist / 1000:.2f} km"
                        
                    # 2. Formatage du temps en MM:SS ou HH:MM:SS
                    minutes, secondes = divmod(int(temps), 60)
                    heures, minutes = divmod(minutes, 60)
                    if heures > 0:
                        text_temps.value = f"{heures:02d}:{minutes:02d}:{secondes:02d}"
                    else:
                        text_temps.value = f"{minutes:02d}:{secondes:02d}"
                        
                    # 3. Formatage des dénivelés
                    text_dplus.value = f"+{d_plus:.1f} m"
                    text_dmoins.value = f"-{d_moins:.1f} m"
                    
                    text_vitesse.value = f"{vitesse:.1f} km/h"
                    text_vitesse_max.value = f"{vitesse_max:.1f} km/h"
                    
                    # Rafraîchissement visuel du bloc de données
                    table_donnees.update()
                    
                    if ax1._processed > points_avant:
                        fig.canvas.draw_idle()
                        gps_chart.update()
                    
                    await asyncio.sleep(0.5)
                    
            async def stop_gps_loop():
                if reader_instance["reader"]:
                    reader_instance["reader"].stop()
                

            async def toggle_tracking(e):
                if not tracking_state["running"]:
                    # --- DÉMARRAGE ---
                    tracking_state["running"] = True
                    tracking_button.content.value = "Arrêter le tracking"
                    tracking_button.update()
                    page.run_task(update_gps_loop)
                else:
                    # --- ARRÊT ---
                    tracking_state["running"] = False
                    tracking_button.content.value = "Démarrer le tracking"
                    tracking_button.update()
                    page.run_task(stop_gps_loop)

            # On lie l'événement du clic à notre nouvelle fonction
            tracking_button.on_click = toggle_tracking
            
            page.views.append(
                ft.View(
                    bgcolor = "#ff7800",
                    route = "/nouveau_parcours",
                    
                    floating_action_button = ft.FloatingActionButton(
                    content = ft.Text("", color="#ff7800", font_family="GoogleSans-Medium"),           
                    bgcolor = "#ffffff",         
                    shape = ft.RoundedRectangleBorder(radius=30),
                    width = 15,
                    height = 15,
                    elevation = 0,
                    hover_elevation = 0,
                    highlight_elevation = 0,
                    on_click = capture_nouveau_parcours
                ),
                    
                    controls = [
                        ft.SafeArea(
                            expand = True,
                            
                            # Contenu de la page "Nouveau parcours"
                            content = ft.Column(
                                alignment = ft.MainAxisAlignment.CENTER,
                                horizontal_alignment = ft.CrossAxisAlignment.CENTER,
                                
                                controls = [
                                    ft.AppBar(
                                        title = ft.Text(
                                            "Nouveau parcours",
                                            color = "#ffffff",
                                            size = 15,
                                            font_family = "GoogleSans-Regular"
                                        ),
                                        center_title = True,
                                        bgcolor = "#ff7800",
                                        color = "#ffffff"
                                    ),
                                    
                                    ft.Container(height=22.5),
                                    
                                    table_donnees,
                                    
                                    ft.Container(
                                        expand = True,
                                        content=gps_chart,
                                        padding=10
                                    ),

                                    tracking_button,
                                    
                                    ft.Container(height=37.5)
                                ]
                            )
                        )
                    ]
                )
            )
        page.update()
        
    async def view_pop(e):
        if e.view is not None:
            page.views.remove(e.view)
            top_view = page.views[-1]
            await page.push_route(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    route_change()



if __name__ == "__main__":
    ft.run(main, assets_dir = "assets")
