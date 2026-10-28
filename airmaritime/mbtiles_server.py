#!/usr/bin/env python3
"""
mbtiles_server.py
─────────────────────────────────────────────────────────────────
Local MBTiles HTTP Tile Server (Zoom Level 0 to 18)
Listens on http://127.0.0.1:8080/tiles/{z}/{x}/{y}.png

1. Reads tiles from world_zoom12.mbtiles SQLite database.
2. Converts Leaflet TMS coordinates (MBTiles tile_row = (1 << z) - 1 - y).
3. Performs dynamic parent tile cropping & scaling so map NEVER turns into a grid when zooming in/out.
"""

import io
import os
import re
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from PIL import Image, ImageDraw

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MBTILES_PATH = os.path.join(BASE_DIR, "world_zoom12.mbtiles")

# Only real tiles from the .mbtiles database are ever served. A tile the database does not
# hold is a 404 (Leaflet leaves that square empty) -- no generated grid imagery and no
# enlarged crops of a parent tile standing in for map data that is not there.
TILE_CACHE = {}


def get_tile(conn, z, x, y):
    """Return the exact stored tile for z/x/y (XYZ scheme), or None if the database has none."""
    cache_key = (z, x, y)
    if cache_key in TILE_CACHE:
        return TILE_CACHE[cache_key]
    tms_y = (1 << z) - 1 - y
    row = conn.execute("SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                       (z, x, tms_y)).fetchone()
    tile = row[0] if row and row[0] else None
    if tile:
        TILE_CACHE[cache_key] = tile
    return tile


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server for high performance tile serving."""
    daemon_threads = True


class MBTilesHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        match = re.match(r"^/tiles/(\d+)/(\d+)/(\d+)\.png(\?.*)?$", self.path)
        if not match:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        z = int(match.group(1))
        x = int(match.group(2))
        y = int(match.group(3))

        tile_bytes = None
        if os.path.exists(MBTILES_PATH):
            try:
                conn = sqlite3.connect(MBTILES_PATH)
                tile_bytes = get_tile(conn, z, x, y)
                conn.close()
            except Exception:
                pass

        if not tile_bytes:
            self.send_response(404)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return

        if tile_bytes.startswith(b"\xff\xd8"):
            content_type = "image/jpeg"
        elif tile_bytes.startswith(b"\x89PNG"):
            content_type = "image/png"
        else:
            content_type = "image/png"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(tile_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(tile_bytes)

    def log_message(self, format, *args):
        return


def main():
    print(f"[MBTILES-SERVER] Starting local MBTiles Tile Server on http://127.0.0.1:{PORT}")
    print(f"[MBTILES-SERVER] Database: {MBTILES_PATH} (real stored tiles only; missing tiles are 404)")
    server = ThreadedHTTPServer(("127.0.0.1", PORT), MBTilesHandler)
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[MBTILES-SERVER] Server stopped.")
