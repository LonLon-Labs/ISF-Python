"""Convert the ripped Lingo data handlers + member tables into JSON the Python port loads.

Usage (from the repo root):
    python tools/convert_data.py --exports "..\\F Exports" --out data

Produces in <out>/:
    script_ids.json   {"131097": "GAME", ...}   (castLib<<16 | member -> script name, castLib 2 = BHP code cast)
    handlers.json     {"getGameDaddy": {...}, "getQuitDialogue": {...}, ...}   (every `get*` data handler in the movie scripts)
    members_main.json {"<member number>": {"type":..., "name":..., "reg":[x,y]}}  (ISPYMAIN7 internal cast)
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lingo_data import parse_handler_file, to_json_safe  # noqa: E402


def read_members(path):
    out = {}
    with open(path, newline='', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            try:
                n = int(row['Number'])
            except (KeyError, ValueError):
                continue
            reg = re.findall(r'-?\d+', row.get('Registration Point') or '')
            out[n] = {
                'type': row.get('Type'),
                'name': row.get('Name') or '',
                'reg': [int(reg[0]), int(reg[1])] if len(reg) >= 2 else [0, 0],
            }
    return out


HANDLER = re.compile(r'^on\s+(\w+)[^\n]*\n(.*?)^end\s*$', re.M | re.S)


def convert_handlers(cast_dir):
    result, failures = {}, []
    for fn in sorted(os.listdir(cast_dir)):
        if not fn.startswith('MovieScript') or not fn.endswith('.ls'):
            continue
        text = open(os.path.join(cast_dir, fn), encoding='utf-8', errors='replace').read().replace('\r', '')
        for m in HANDLER.finditer(text):
            name, body = m.group(1), m.group(2)
            if not name.startswith('get') or '= [' not in body:
                continue
            try:
                result[name] = to_json_safe(parse_handler_file(body))
            except Exception as e:  # keep going, report at the end
                failures.append((fn, name, str(e)))
    return result, failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exports', required=True)
    ap.add_argument('--out', default='data')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    bhp = read_members(os.path.join(a.exports, 'BHP', 'Members.csv'))
    ids = {str((2 << 16) | n): m['name'] for n, m in bhp.items() if m['type'] == 'script' and m['name']}
    json.dump(ids, open(os.path.join(a.out, 'script_ids.json'), 'w'), indent=1)

    cast_dir = os.path.join(a.exports, 'BHP', 'casts', 'External')
    handlers, failures = convert_handlers(cast_dir)
    json.dump(handlers, open(os.path.join(a.out, 'handlers.json'), 'w'))
    print('handlers converted:', len(handlers))
    for f in failures:
        print('FAILED', f)

    main_members = read_members(os.path.join(a.exports, 'ISPYMAIN7', 'Members.csv'))
    json.dump({str(k): v for k, v in main_members.items()}, open(os.path.join(a.out, 'members_main.json'), 'w'))
    print('main-cast members:', len(main_members))


if __name__ == '__main__':
    main()
