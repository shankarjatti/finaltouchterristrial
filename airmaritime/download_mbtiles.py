#!/usr/bin/env python3
"""
download_mbtiles.py
─────────────────────────────────────────────────────────────────
Downloads real dark map tile PNG images (Esri Dark Canvas) 
for San Francisco & West Coast Bay Area (zoom levels 0 to 12)
and populates them into world_zoom12.mbtiles database.
"""

import os
import math
import sqlite3
import urllib.request
import time

MBTILES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_zoom12.mbtiles")
TILE_URL_TEMPLATE = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"

def lon2tile(lon, zoom):
    return int(math.floor((lon + 180.0) / 360.0 * (1 << zoom)))

def lat2tile(lat, zoom):
    lat_rad = math.radians(lat)
    return int(math.floor((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * (1 << zoom)))

def download_tiles():
    if not os.path.exists(MBTILES_PATH):
        print(f"[MBTILES] Database {MBTILES_PATH} not found!")
        return

    conn = sqlite3.connect(MBTILES_PATH)
    cur = conn.cursor()

    tiles_to_download = []
    
    # Zoom 0 to 3 (Global World)
    for z in range(0, 4):
        for x in range(0, 1 << z):
            for y in range(0, 1 << z):
                tiles_to_download.append((z, x, y))

    # Zoom 4 to 12 (San Francisco Bay Area & US West Coast)
    lat, lon = 37.7749, -122.4194
    for z in range(4, 13):
        cx = lon2tile(lon, z)
        cy = lat2tile(lat, z)
        # Expand bounding box around center for wide screen coverage
        if z <= 6:
            span_x, span_y = (1 << z), (1 << z) # Full world/US for low zoom
        elif z <= 8:
            span_x, span_y = 12, 12
        else:
            span_x, span_y = 10, 10 # 21x21 tiles per zoom level = 5376px wide coverage
            
        for dx in range(-span_x, span_x + 1):
            for dy in range(-span_y, span_y + 1):
                x = cx + dx
                y = cy + dy
                if 0 <= x < (1 << z) and 0 <= y < (1 << z):
                    tiles_to_download.append((z, x, y))

    print(f"[MBTILES-DOWNLOADER] Downloading {len(tiles_to_download)} real tile images into {MBTILES_PATH}...")

    count = 0
    headers = {'User-Agent': 'Mozilla/5.0'}
    for z, x, y in tiles_to_download:
        tms_y = (1 << z) - 1 - y
        
        # Check if already in DB
        cur.execute("SELECT 1 FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?", (z, x, tms_y))
        if cur.fetchone():
            continue

        url = TILE_URL_TEMPLATE.format(z=z, x=x, y=y)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                tile_data = response.read()
                if len(tile_data) > 500: # Ensure valid image
                    cur.execute("INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)", (z, x, tms_y, tile_data))
                    count += 1
                    if count % 15 == 0:
                        conn.commit()
                        print(f"  [+] Downloaded {count} tiles... (latest: z={z}, x={x}, y={y})", flush=True)
        except Exception as e:
            pass
        time.sleep(0.04)

    conn.commit()
    conn.close()
    print(f"[MBTILES-DOWNLOADER] Done! Total {count} new real map tiles added to {MBTILES_PATH}")

if __name__ == "__main__":
    download_tiles()
