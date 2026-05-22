import time
import serial

# --- CONFIGURATION ---
SERIAL_PORT = 'COM3' 
BAUD_RATE = 4800
DURATION_SECONDS = 10
OUTPUT_FILE = "trajet_pur.kml"
# ---------------------

def nmeatodecimal(nmea_string, direction):
    """
    Convertit le format NMEA (DDMM.MMMM) en Degrés Décimaux
    """
    if not nmea_string:
        return None   
    # On trouve le point décimal pour séparer les minutes des degrés
    dot_index = nmea_string.find('.')
    
    # Les minutes occupent toujours 2 chiffres avant le point (MM.MMMM)
    minutes_start = dot_index - 2
    
    degrees = float(nmea_string[:minutes_start])
    minutes = float(nmea_string[minutes_start:])
    
    decimal_degrees = degrees + (minutes / 60.0)
    
    # Si c'est le Sud ou l'Ouest, la coordonnée doit être négative
    if direction in ['S', 'W']:
        decimal_degrees = -decimal_degrees
        
    return decimal_degrees

def generate_kml(coordinates, filename):
    """Génère le fichier KML"""
    kml_coords = "\n".join([f"{lon},{lat},0" for lon, lat in coordinates])
    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Trajet G-Star IV (Code Pur)</name>
    <Placemark>
      <name>Mon Trajet</name>
      <LineString>
        <coordinates>
{kml_coords}
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(kml_content)
    print(f"\n🎉 Fichier KML enregistré : '{filename}'")

def main():
    positions = []
    
    print(f"Connexion à {SERIAL_PORT}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    except Exception as e:
        print(f"❌ Erreur port : {e}")
        return

    print(f"Écoute du flux NMEA pendant {DURATION_SECONDS}s...")
    start_time = time.time()

    try:
        while time.time() - start_time < DURATION_SECONDS:
            # 1. Lire la ligne brute du port série
            line_bytes = ser.readline()
            
            try:
                # Décodage des octets en texte
                line = line_bytes.decode('ascii', errors='ignore').strip()
            except:
                continue

            # 2. On filtre uniquement la phrase qui contient les données complètes ($GPGGA)
            if line.startswith('$GPGGA'):
                # On découpe la ligne à chaque virgule
                parts = line.split(',')
                
                # Sécurité : On vérifie que la ligne est complète (au moins 7 éléments)
                if len(parts) > 6:
                    raw_lat = parts[2]
                    lat_dir = parts[3]
                    raw_lon = parts[4]
                    lon_dir = parts[5]
                    gps_quality = parts[6]
                    
                    # Si la qualité est à '0', le GPS n'a pas encore fixé les satellites
                    if gps_quality == '0':
                        print("📡 En attente du signal satellite (Fix)...")
                        continue
                        
                    # 3. Conversion manuelle si les données sont présentes
                    if raw_lat and raw_lon:
                        lat = nmeatodecimal(raw_lat, lat_dir)
                        lon = nmeatodecimal(raw_lon, lon_dir)
                        
                        if lat is not None and lon is not None:
                            positions.append((lon, lat))
                            print(f"📍 Point capturé -> Lat: {lat:.6f}, Lon: {lon:.6f}")
                            
    except KeyboardInterrupt:
        print("\nInterrompu.")
    finally:
        ser.close()

    if positions:
        generate_kml(positions, OUTPUT_FILE)
    else:
        print("❌ Aucun point valide enregistré. Vérifiez que la LED du boîtier clignote.")

if __name__ == "__main__":
    main()