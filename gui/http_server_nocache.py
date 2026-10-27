#!/usr/bin/env python3
"""Serve the console like `python3 -m http.server`, but tell browsers not to cache it.

With the plain server, browsers kept showing an old securecom_gui.html after it was
updated (e.g. the 8-colour palette) until a hard refresh. Recordings are served the
same way, so a re-recorded .wav is never played from cache either.

  python3 http_server_nocache.py 8788 --bind 127.0.0.1
"""
import argparse
import http.server


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.send_header('Expires', '0')
        super().end_headers()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('port', type=int)
    ap.add_argument('--bind', default='127.0.0.1')
    a = ap.parse_args()
    http.server.ThreadingHTTPServer((a.bind, a.port), NoCacheHandler).serve_forever()


if __name__ == '__main__':
    main()
