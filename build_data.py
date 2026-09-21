#!/usr/bin/env python3
# build_data.py - pull FEHD dengue gravidtrap index (CSDI FEHD_OVITRAP_INDEX_POLY) and emit data.js
# Source: https://portal.csdi.gov.hk/server/rest/services/common/fehd_rcd_1629966670823_4638/FeatureServer/0/query
import json, gzip, urllib.request, math, datetime, sys

BASE = ('https://portal.csdi.gov.hk/server/rest/services/common/'
        'fehd_rcd_1629966670823_4638/FeatureServer/0/query')

def fetch(offset=0, where='1%3D1', n=10000):
    url = f'{BASE}?f=geojson&where={where}&outFields=*&outSR=4326&resultRecordCount={n}'
    if offset:
        url += f'&resultOffset={offset}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read()
        if r.headers.get('Content-Encoding') == 'gzip':
            raw = gzip.decompress(raw)
    return json.loads(raw)['features']

def pull_all():
    feats = fetch(0)
    # server caps one request at 3000 records -> paginate until exhausted
    while len(feats) % 3000 == 0:
        more = fetch(len(feats))
        if not more:
            break
        feats.extend(more)
        if len(more) < 3000:
            break
    return feats

# --- projection: local mercator, y = -lat mercator so north is -z ---
R = 6378137.0
LAT0 = math.radians(22.3)
COS0 = math.cos(LAT0)
def proj(lon, lat):
    x = R * math.radians(lon) * COS0
    z = R * math.log(math.tan(math.pi/4 + math.radians(lat)/2))   # north = +z in data
    return (round(x, 2), round(z, 2))

def signed_area(ring):
    a = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]; x2, y2 = ring[(i+1) % n]
        a += x1*y2 - x2*y1
    return a / 2.0

def point_in_ring(pt, ring):
    # ray casting, ring = [(x,z)...]
    x, z = pt
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, zi = ring[i]; xj, zj = ring[j]
        if ((zi > z) != (zj > z)) and (x < (xj-xi)*(z-zi)/(zj-zi) + xi):
            inside = not inside
        j = i
    return inside

def ring_centroid(ring):
    x = sum(p[0] for p in ring) / len(ring)
    z = sum(p[1] for p in ring) / len(ring)
    return (x, z)

def build_parts(geom):
    """geom -> [{'ring': [...], 'holes': [[...],...]}] projected; dedupe consecutive dup points."""
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    parts = []
    for poly in polys:
        rings = []
        for ring in poly:
            pr = [proj(lon, lat) for lon, lat in ring]
            # drop consecutive duplicates & closing dup
            dedup = []
            for p in pr:
                if not dedup or p != dedup[-1]:
                    dedup.append(p)
            if len(dedup) > 2 and dedup[0] == dedup[-1]:
                dedup = dedup[:-1]
            if len(dedup) < 3:
                continue
            rings.append(dedup)
        if not rings:
            continue
        # sort by |area| desc -> ring0 = biggest outer
        rings.sort(key=lambda r: abs(signed_area(r)), reverse=True)
        outer = rings[0]
        if signed_area(outer) < 0:          # make outer counter-clockwise (positive in math y-up)
            outer = outer[::-1]
        holes = []
        for r in rings[1:]:
            c = ring_centroid(r)
            if point_in_ring(c, outer) and abs(signed_area(r)) < abs(signed_area(outer)) * 0.99:
                if signed_area(r) > 0:
                    r = r[::-1]            # holes clockwise (opposite to outer)
                holes.append(r)
            else:
                # separate island inside same polygon: treat as its own part
                if signed_area(r) < 0:
                    r = r[::-1]
                parts.append({'ring': r, 'holes': []})
        parts.append({'ring': outer, 'holes': holes})
    return parts

def center_of(parts):
    xs, zs = [], []
    for p in parts:
        for rx, rz in p['ring']:
            xs.append(rx); zs.append(rz)
    return (round(sum(xs)/len(xs), 2), round(sum(zs)/len(zs), 2))

def main():
    feats = pull_all()
    periods = sorted({f['properties']['PERIOD'] for f in feats})
    # geometry from the latest available period
    latest = periods[-1]
    by_loc = {}
    for f in feats:
        p = f['properties']
        key = p['LOCATION_C'] or p['LOCATION']
        ent = by_loc.setdefault(key, {
            'name_tc': p['LOCATION_C'], 'name_en': p['LOCATION'],
            'district_tc': p['DISTRICT_C'], 'district_en': p['DISTRICT'],
            'geom': None, 'series': {}
        })
        if p['PERIOD'] == latest and ent['geom'] is None:
            ent['geom'] = f['geometry']
        ent['series'][p['PERIOD']] = (p['AGI'], p['ADI'])
    # fallback: any area missing geometry in the latest period -> use the most recent period that has it
    for key, ent in by_loc.items():
        if ent['geom'] is not None:
            continue
        for per in sorted(ent['series'], reverse=True):
            for f in feats:
                p = f['properties']
                if (p['LOCATION_C'] or p['LOCATION']) == key and p['PERIOD'] == per and f['geometry'] is not None:
                    ent['geom'] = f['geometry']
                    break
            if ent['geom'] is not None:
                print(f'  fallback geom: {ent["name_tc"]} <- {per}', file=sys.stderr)
                break
    areas = []
    for key, ent in sorted(by_loc.items()):
        parts = build_parts(ent['geom'])
        if not parts:
            print(f'!! no parts for {key}', file=sys.stderr)
            continue
        series = []
        for i, per in enumerate(periods):
            agi, adi = ent['series'].get(per, (None, None))
            series.append([i, round(agi, 2) if agi is not None else None,
                           round(adi, 2) if adi is not None else None])
        areas.append({
            'id': key,
            'name': {'tc': ent['name_tc'], 'en': ent['name_en']},
            'district': {'tc': ent['district_tc'], 'en': ent['district_en']},
            'parts': parts,
            'center': center_of(parts),
            'series': series,
        })
    out = {
        'updated': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        'latest': latest,
        'periods': periods,
        'areas': areas,
    }
    # offset coordinates to bbox center -> keeps float32 precision in three.js
    xs = [p[0] for a in areas for pt in a['parts'] for r in [pt['ring']] + pt['holes'] for p in r]
    zs = [p[1] for a in areas for pt in a['parts'] for r in [pt['ring']] + pt['holes'] for p in r]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    for a in areas:
        a['center'] = [round(a['center'][0] - cx, 2), round(a['center'][1] - cz, 2)]
        for pt in a['parts']:
            pt['ring'] = [[round(p[0] - cx, 2), round(p[1] - cz, 2)] for p in pt['ring']]
            for i, hole in enumerate(pt['holes']):
                pt['holes'][i] = [[round(p[0] - cx, 2), round(p[1] - cz, 2)] for p in hole]
    with open('data.js', 'w') as fh:
        fh.write('window.DENGUE_DATA = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';')
    print(f'areas={len(areas)} periods={len(periods)} latest={latest} '
          f'verts={sum(len(p["ring"]) for a in areas for p in a["parts"])}')

if __name__ == '__main__':
    main()