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

# Cache for generated tactical grid fallback tiles & parent crop tiles
TILE_CACHE = {}

def generate_dark_grid_tile(z, x, y):
    """Generates a dark 256x256 tactical radar grid PNG tile."""
    key = ('grid', z, x % 4, y % 4)
    if key in TILE_CACHE:
        return TILE_CACHE[key]

    img = Image.new("RGBA", (256, 256), color=(11, 15, 25, 255))
    draw = ImageDraw.Draw(img)

    # Dark Grid Lines
    grid_color = (42, 52, 69, 255)
    for pos in range(0, 256, 32):
        draw.line([(pos, 0), (pos, 256)], fill=grid_color, width=1)
        draw.line([(0, pos), (256, pos)], fill=grid_color, width=1)

    # Sub-grid ticks
    tick_color = (51, 65, 85, 255)
    draw.rectangle([0, 0, 255, 255], outline=tick_color, width=1)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    tile_bytes = buf.getvalue()
    TILE_CACHE[key] = tile_bytes
    return tile_bytes


def get_tile_with_fallback(conn, z, x, y):
    """Fetches exact tile or crops and scales parent zoom level tile if missing."""
    cache_key = ('tile', z, x, y)
    if cache_key in TILE_CACHE:
        return TILE_CACHE[cache_key]

    cur = conn.cursor()
    # 1. Try exact match first
    tms_y = (1 << z) - 1 - y
    cur.execute("SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?", (z, x, tms_y))
    row = cur.fetchone()
    if row and row[0]:
        TILE_CACHE[cache_key] = row[0]
        return row[0]

    # 2. Parent tile fallback (recursively check up to 6 parent zoom levels up)
    curr_z, curr_x, curr_y = z, x, y
    for level in range(1, 7):
        if curr_z <= 0:
            break
        curr_z -= 1
        curr_x //= 2
        curr_y //= 2
        curr_tms_y = (1 << curr_z) - 1 - curr_y
        cur.execute("SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?", (curr_z, curr_x, curr_tms_y))
        prow = cur.fetchone()
        if prow and prow[0]:
            try:
                parent_img = Image.open(io.BytesIO(prow[0])).convert("RGBA")
                rel_z = z - curr_z
                denom = 1 << rel_z
                sub_x = x % denom
                sub_y = y % denom
                w, h = parent_img.size
                qw, qh = w / denom, h / denom
                box = (sub_x * qw, sub_y * qh, (sub_x + 1) * qw, (sub_y + 1) * qh)
                cropped = parent_img.crop(box).resize((256, 256), Image.BICUBIC)
                buf = io.BytesIO()
                cropped.save(buf, format="PNG")
                tile_bytes = buf.getvalue()
                TILE_CACHE[cache_key] = tile_bytes
                return tile_bytes
            except Exception:
                pass

    return None


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server for high performance tile serving."""
    daemon_threads = True


class MBTilesHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        match = re.match(r"^/tiles/(\d+)/(\d+)/(\d+)\.png$", self.path)
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
                tile_bytes = get_tile_with_fallback(conn, z, x, y)
                conn.close()
            except Exception:
                pass

        if not tile_bytes:
            tile_bytes = generate_dark_grid_tile(z, x, y)

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
    print(f"[MBTILES-SERVER] Database: {MBTILES_PATH} (Zoom Level 0 to 18 with auto-fallback)")
    server = ThreadedHTTPServer(("127.0.0.1", PORT), MBTilesHandler)
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[MBTILES-SERVER] Server stopped.")
