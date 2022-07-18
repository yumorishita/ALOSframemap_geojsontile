#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create GeoJSON of ALOS frame map at ZL=1 for GSIMaps from GeoJSON tiles.

"""


# %% Import
import argparse
import sys
import os
import time
import datetime
import glob
import json
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import numpy as np


# %% latlon2tileid
def latlon2tileid(lat, lon, zl):
    # https://www.trail-note.net/tech/coordinate/
    # https://note.sngklab.jp/?p=72

    x = int((lon/180+1)*2**zl/2)
    y = int(((-np.log(np.tan(np.deg2rad(45+lat/2)))+np.pi)*2**zl/(2*np.pi)))

    return x, y


# %% add_feature
def add_feature(feature, geojson):
    if not os.path.exists(geojson):
        os.makedirs(os.path.dirname(geojson), exist_ok=True)
        with open(geojson, 'x') as f:
            json.dump({'type': 'FeatureCollection', 'features': []}, f)

    with open(geojson, 'r') as f:
        json_dict = json.load(f)
        features_list = json_dict['features']

    features_list.append(feature)

    with open(geojson, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': features_list}, f)


# %% Main
def main(argv=None):

    # %% Settings
    color = "#ff0000"
    line_opacity = 0.4
    line_width = 1
    fill_opacity = 0.1
    tolerance = 0.05


    # %% Read arg
    start = time.time()
    prog = os.path.basename(sys.argv[0])
    description = 'Create ZL=1 GeoJSON of ALOS frame map.'
    print(f"\n{prog} ver1.0.0 20220718 Y. Morishita")
    print(f"{prog} {' '.join(sys.argv[1:])}\n")

    parser = argparse.ArgumentParser(description=description)
    addarg = parser.add_argument
    addarg('-i', '--input_dir', type=str, required=True,
            help='Input directory containing GeoJSON tiles to be dissolved')
    addarg('-z', '--zoomlevel', type=int, default=6,
            help='Input zoom level')
    args = parser.parse_args()

    input_dir = args.input_dir
    zl = args.zoomlevel
    zldir = os.path.join(input_dir, str(zl))

    if not os.path.exists(zldir):
        raise FileNotFoundError(f'No {zldir} exists!')


    # %% Output geojson tile dirs
    zl1dir = os.path.join(input_dir, '1', '1') # For ZL=1
    os.makedirs(zl1dir, exist_ok=True)
    out_jsonfile = os.path.join(zl1dir, '0.geojson')


    # %% For each input geojson files
    polygons = [] # For dissolved geojson
    for _json in glob.glob(os.path.join(zldir, '*', '*.geojson')):
        with open(_json, 'r') as f:
            json_dict = json.load(f)
        features_list = json_dict['features']

        for feature in features_list:
            geometry = feature['geometry']
            lat = geometry['coordinates'][0][0][1]
            if lat > 84 or lat < -84: # cannot display on web map
                continue

            polygons.append(Polygon(feature['geometry']['coordinates'][0]))


    # %% Make dissolved geojson
    dissolved_poly = unary_union(MultiPolygon(polygons))
    if dissolved_poly.type == 'Polygon': # 1 segment
        dissolved_poly = [dissolved_poly]
    for _poly in dissolved_poly:
        poly2 = _poly.simplify(tolerance)
        poly2_list = [list(i) for i in poly2.exterior.coords[:]]
        print(f'Number of nodes: {len(poly2_list)}')
        geometry2 = {'type': 'Polygon', 'coordinates': [poly2_list]}
        properties2 = {"name": input_dir,
                      "_color": color, "_opacity": line_opacity,
                        "_weight": line_width, "_fillColor": color,
                        "_fillOpacity": fill_opacity}
        out_feature = {'type': 'Feature', 'properties': properties2,
                       'geometry': geometry2}

        # Add feature
        add_feature(out_feature, out_jsonfile)


    # %% Finish
    elapsed_time = datetime.timedelta(seconds=(time.time()-start))
    print(f"\nElapsed time: {elapsed_time}")
    print(f'\n{prog} Successfully finished!!\n')

    print(f"Output: {out_jsonfile}\n")


# %% main
if __name__ == "__main__":
    sys.exit(main())
