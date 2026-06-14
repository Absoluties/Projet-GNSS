import sys
import os

def calculer_checksum(trame_sans_start):
    """Calcule le checksum XOR d'une trame NMEA (sans le '$' et sans le '*')"""
    # Si la trame contient un '*', on ne prend que ce qui est avant
    corps = trame_sans_start.split('*')[0]
    checksum = 0
    for char in corps:
        checksum ^= ord(char)
    # Renvoie le checksum en hexadécimal majuscule sur 2 caractères
    return f"{checksum:02X}"

def modifier_altitude_gga(ligne):
    """Modifie l'altitude d'une trame GGA en lui soustrayant 2 mètres"""
    # Nettoyage des espaces et sauts de ligne
    ligne = ligne.strip()
    if not ligne.startswith('$') or 'GGA' not in ligne:
        return ligne

    # Extraction du corps de la trame et du checksum d'origine
    # Exemple : $GPGGA,123456,...,M,,*47 -> corps = GPGGA,123456,...,M,, et checksum = 47
    parties_checksum = ligne[1:].split('*')
    corps = parties_checksum[0]
    
    champs = corps.split(',')
    
    try:
        # Dans une trame GGA, l'altitude géodésique est au 9ème index (10ème champ)
        # L'unité (M pour mètres) est au 10ème index
        if champs[9]:  
            altitude_actuelle = float(champs[9])
            nouvelle_altitude = altitude_actuelle - 2.0
            
            # Formatage pour garder le même nombre de décimales si possible (souvent 1 ou 2)
            # On utilise .2f par sécurité, ou on adapte selon le besoin
            champs[9] = f"{nouvelle_altitude:.2f}"
            
            # Reconstitution du corps de la trame
            nouveau_corps = ",".join(champs)
            nouveau_checksum = calculer_checksum(nouveau_corps)
            
            return f"${nouveau_corps}*{nouveau_checksum}"
    except (IndexError, ValueError):
        # Si la trame est malformée ou si le champ altitude est vide, on la laisse inchangée
        pass
        
    return ligne

def main():
    # Vérification des arguments de la ligne de commande
    if len(sys.argv) < 3:
        print("Erreur : Arguments manquants.")
        print("Usage : python modifier_nmea.py <fichier_entree> <fichier_sortie>")
        sys.exit(1)

    chemin_entree = sys.argv[1]
    chemin_sortie = sys.argv[2]

    if not os.path.exists(chemin_entree):
        print(f"Erreur : Le fichier d'entrée '{chemin_entree}' n'existe pas.")
        sys.exit(1)

    try:
        print(f"Lecture de : {chemin_entree}")
        compteur_gga = 0
        compteur_total = 0

        with open(chemin_entree, 'r', encoding='ascii', errors='ignore') as f_in, \
             open(chemin_sortie, 'w', encoding='ascii', newline='\r\n') as f_out:
            
            for ligne in f_in:
                if not ligne.strip():
                    continue
                
                compteur_total += 1
                if 'GGA' in ligne:
                    ligne_modifiee = modifier_altitude_gga(ligne)
                    compteur_gga += 1
                else:
                    ligne_modifiee = ligne.strip()

                # Écriture dans le nouveau fichier avec retour à la ligne standard NMEA (\r\n)
                f_out.write(ligne_modifiee + '\n')

        print(f"Modification terminée avec succès !")
        print(f"Trames totales traitées : {compteur_total}")
        print(f"Trames GGA modifiées (-2m) : {compteur_gga}")
        print(f"Fichier sauvegardé sous : {chemin_sortie}")

    except Exception as e:
        print(f"Une erreur est survenue lors du traitement : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()