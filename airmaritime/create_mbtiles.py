#!/usr/bin/env python3
"""
create_mbtiles.py
─────────────────────────────────────────────────────────────────
Creates world_zoom12.mbtiles SQLite database according to the 
MBTiles 1.3 Specification for offline tile storage up to zoom level 12.
"""

import os
import sqlite3

MBTILES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_zoom12.mbtiles")

def init_mbtiles():
    if os.path.exists(MBTILES_PATH):
        print(f"[MBTILES] Database already exists at {MBTILES_PATH}")
        return

    conn = sqlite3.connect(MBTILES_PATH)
    cur = conn.cursor()

    # Create MBTiles standard tables
    cur.execute("CREATE TABLE metadata (name text, value text);")
    cur.execute("CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob);")
    cur.execute("CREATE UNIQUE INDEX tile_index on tiles (zoom_level, tile_column, tile_row);")

    # Insert MBTiles metadata
    metadata = [
        ("name", "World Offline Map (Zoom 12)"),
        ("type", "baselayer"),
        ("version", "1.3"),
        ("description", "Offline MBTiles tactical map database up to zoom level 12"),
        ("format", "png"),
        ("bounds", "-180.0,-85.0,180.0,85.0"),
        ("minzoom", "0"),
        ("maxzoom", "12")
    ]
    cur.executemany("INSERT INTO metadata VALUES (?, ?);", metadata)
    conn.commit()
    conn.close()

    print(f"[MBTILES] Created offline database up to zoom level 12 at:\n  {MBTILES_PATH}")

if __name__ == "__main__":
    init_mbtiles()
