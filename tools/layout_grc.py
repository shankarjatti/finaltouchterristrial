#!/usr/bin/env python3
"""Lay out allinone.grc so it reads like the system: one row per protocol, left to right.

  top     : options, variables and Qt controls in a grid
  rows    : one per protocol chain, in band order (DMR, NXDN96, P25, TETRA, NXDN48,
            D-STAR, X2-TDMA, ProVoice); each block's column is its depth from the
            TCP source, so a row reads source -> channelizer -> ... -> tap / speaker
  bottom  : displays shared by several chains (combined spectrum, audio plot)

Only block coordinates change; the generated Python is functionally identical.

  python3 tools/layout_grc.py allinone.grc
"""
import collections
import sys

import yaml

ORDER = ['dmr', 'nxdn', 'p25', 'tetra', 'nxdn48', 'dstar', 'x2tdma', 'provoice']
COL_W = 300          # horizontal spacing between chain stages
GRID_W, GRID_H, GRID_COLS = 300, 130, 8
ROW_GAP = 120
X0, Y0 = 16, 16


def block_height(n_ports):
    # GRC draws ports ~20 px apart; a 32-output channelizer is ~700 px tall
    return max(110, 40 + 22 * n_ports)


def main():
    path = sys.argv[1]
    g = yaml.safe_load(open(path))
    blocks = {b['name']: b for b in g['blocks']}
    conns = [(c[0], int(c[1]) if str(c[1]).isdigit() else 0, c[2], int(c[3]) if str(c[3]).isdigit() else 0)
             for c in g['connections']]
    connected = {a for a, *_ in conns} | {c[2] for c in conns}
    nports = collections.Counter()
    for a, ap, b, bp in conns:
        nports[a] = max(nports[a], ap + 1)
        nports[b] = max(nports[b], bp + 1)

    # chains = connected components, ignoring Qt sinks (several chains feed them)
    parent = {n: n for n in connected}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n
    is_gui = lambda n: blocks[n]['id'].startswith('qtgui_')
    for a, _, b, _ in conns:
        if not is_gui(a) and not is_gui(b):
            parent[find(a)] = find(b)
    chain_of_root = {}
    for key in ORDER:
        src = f'network_tcp_source_{key}'
        if src in blocks:
            chain_of_root[find(src)] = key
    members = collections.defaultdict(list)
    shared = []
    for n in connected:
        if is_gui(n):
            srcs = {chain_of_root.get(find(a)) for a, _, b, _ in conns if b == n}
            srcs.discard(None)
            (members[srcs.pop()] if len(srcs) == 1 else shared).append(n)
        else:
            members[chain_of_root.get(find(n), 'other')].append(n)

    # header grid: everything not connected (options, variables, Qt ranges, imports)
    loose = sorted((n for n in blocks if n not in connected), key=lambda n: (blocks[n]['id'] != 'options', blocks[n]['id'], n))
    for i, n in enumerate(loose):
        blocks[n]['states']['coordinate'] = [X0 + (i % GRID_COLS) * GRID_W, Y0 + (i // GRID_COLS) * GRID_H]
    y = Y0 + ((len(loose) + GRID_COLS - 1) // GRID_COLS) * GRID_H + ROW_GAP

    def place_row(names, y):
        names = set(names)
        depth = {n: 0 for n in names}
        for _ in range(len(names)):            # longest path from the row's sources
            changed = False
            for a, _, b, _ in conns:
                if a in names and b in names and depth[b] < depth[a] + 1:
                    depth[b] = depth[a] + 1
                    changed = True
            if not changed:
                break
        cols = collections.defaultdict(list)
        for n in sorted(names):
            cols[depth[n]].append(n)
        tallest = 0
        for d, col in cols.items():
            yy = y
            for n in col:
                blocks[n]['states']['coordinate'] = [X0 + d * COL_W, yy]
                yy += block_height(nports[n]) + 30
            tallest = max(tallest, yy - y)
        return y + tallest + ROW_GAP

    for key in ORDER + ['other']:
        if members.get(key):
            y = place_row(members[key], y)
    for i, n in enumerate(sorted(shared)):
        blocks[n]['states']['coordinate'] = [X0 + i * 2 * COL_W, y]

    with open(path, 'w') as f:
        yaml.safe_dump(g, f, default_flow_style=False, sort_keys=False, width=1000)
    print(f'{path}: {len(loose)} controls in the header grid, rows: '
          + ', '.join(f'{k} ({len(members[k])})' for k in ORDER + ['other'] if members.get(k))
          + f', shared displays: {len(shared)}')


if __name__ == '__main__':
    main()
