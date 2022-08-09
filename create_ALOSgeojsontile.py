#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create GeoJSON tile of AIST ALOS frames for GSIMaps.

"""

# %% Import
import argparse
import sys
import os
import time
import datetime
import json
import subprocess
import numpy as np
import requests

os.environ['LANG'] = 'en_US.UTF-8'

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

# %%
def download_txt(url, n_retry=10):
    for i in range(n_retry):
        try:
            with requests.get(url) as res:
                res.raise_for_status()
                _list = res.text.splitlines()
            return _list
        except:
            print(f'{i+1}st Download error')
            pass # try again

    raise Exception(f"Error while downloading from {url}")


# %% Main
def main(argv=None):

    # %% Settings
    line_colorA = "#0000ff"
    line_colorD = "#ff0000"
    line_opacity = 0.7
    line_width = 1
    fill_opacity = 0.5

    url_list_base = 'https://gsrt.digiarc.aist.go.jp/insarbrowser/doc'
    url_alltxt = os.path.join(url_list_base, 'all_products_list.txt')
    url_gunw_base = 'https://s3.abci.ai/palsar-insar-pds/P1INSAR/GUNW'


    # %% Read arg
    start = time.time()
    prog = os.path.basename(sys.argv[0])
    description = 'Create GeoJSON tile of AIST ALOS frame map for GSIMaps.'
    print(f"\n{prog} ver1.1.2 20220809 Y. Morishita")
    print(f"{prog} {' '.join(sys.argv[1:])}\n")

    parser = argparse.ArgumentParser(description=description)
    addarg = parser.add_argument
    addarg('-z', '--zoomlevel', type=int, default=5,
            help='Output zoom level')
    args = parser.parse_args()

    zl = args.zoomlevel


    # %% Output geojson tile dirs and network dirs
    bname = 'ALOSframe'
    for inc in ['343', 'others']:
        for AD in ['A', 'D']:
            bdir = bname+f'{AD}{inc}'
            if os.path.exists(bdir):
                subprocess.run(['rm', '-rf', bdir])
            zldir = os.path.join(bdir, str(zl))
            os.makedirs(zldir)


    # %% For each frames
    print('Get all_products_list.txt')
    all_list = download_txt(url_alltxt)
    n_all = len(all_list)

    print('For each frame ID')
    for i, plisttxt in enumerate(all_list):
        start1 = time.time()

        # %% Read info
        frameid = plisttxt.replace(url_list_base, '').replace(
            'products_list.txt', '').replace('/', '')
        print(f'{i+1}/{n_all} {frameid} {AD},', end='')

        path, frame, inc = frameid.split('_')
        if inc != '343': inc = 'others'
        if 1810 <= int(frame) <= 5400:
            AD = 'D'
            line_color = line_colorD
        else:
            AD = 'A'
            line_color = line_colorA

        products_list = download_txt(plisttxt)

        # Unwrap rate
        url_unwratetxt = os.path.join(url_list_base, frameid,
                                      'unwrap_rates_list.txt')
        unwrates = download_txt(url_unwratetxt)
        unwrates_dict = {}
        for l in unwrates:
            unwrates_dict[l.split(',')[0]] = float(l.split(',')[1])

        # bperp and number
        url_baselines = os.path.join(url_gunw_base, frameid,
                                     f'{frameid}_GUNW.baselines')
        baselines = download_txt(url_baselines)
        bperp_dict = {} # e.g. '20070312': 19.008
        for l in baselines:
            bperp_dict[l.split()[1]] = float(l.split()[-2])
            bperp_dict[l.split()[2]] = float(l.split()[-1])

        n_im = len(bperp_dict)
        n_ifg = len(baselines)

        if n_im >= 32:
            color = line_color
        else:
            color = line_color.replace('0000', hex(255-n_im*8)[2:].zfill(2)*2)

        # latlon
        url_gunwtxt = None
        for file in products_list:
            if 'GUNW.txt' in file:
                url_gunwtxt = file
                break
        gunwtxt = download_txt(url_gunwtxt)

        lat_sn = [float(s.split('=')[-1]) for s in gunwtxt
                 if 'SceneStartNearRangeLatitudeDegree' in s][0]
        lon_sn = [float(s.split('=')[-1]) for s in gunwtxt
                 if 'SceneStartNearRangeLongitudeDegre' in s][0]
        lat_sf = [float(s.split('=')[-1]) for s in gunwtxt
                 if 'SceneStartFarRangeLatitudeDegree' in s][0]
        lon_sf = [float(s.split('=')[-1]) for s in gunwtxt
                 if 'SceneStartFarRangeLongitudeDegree' in s][0]
        lat_en = [float(s.split('=')[-1]) for s in gunwtxt
                 if 'SceneEndNearRangeLatitudeDegree' in s][0]
        lon_en = [float(s.split('=')[-1]) for s in gunwtxt
                 if 'SceneEndNearRangeLongitudeDegree' in s][0]
        lat_ef = [float(s.split('=')[-1]) for s in gunwtxt
                 if 'SceneEndFarRangeLatitudeDegree' in s][0]
        lon_ef = [float(s.split('=')[-1]) for s in gunwtxt
                 if 'SceneEndFarRangeLongitudeDegree' in s][0]
        lat_c = [float(s.split('=')[-1]) for s in gunwtxt
                 if 'SceneCenterLatitudeDegree' in s][0]
        lon_c = [float(s.split('=')[-1]) for s in gunwtxt
                 if 'SceneCenterLongitudeDegree' in s][0]


        # %% Append geojson
        url_networkpng = os.path.join(url_list_base, frameid, 'network.png')
        coords = [[[lon_sn, lat_sn], [lon_sf, lat_sf], [lon_ef, lat_ef],
                   [lon_en, lat_en], [lon_sn, lat_sn]]]
        geometry = {"type": "Polygon", "coordinates": coords}
        descr = f'# epochs: {n_im}<br># ifgs: {n_ifg}<br>' \
                f'<a href="{plisttxt}" target="_blank">Product list</a><br>' \
                f'<a href="{url_networkpng}" target="_blank">' \
                f'<img src="{url_networkpng}" width="500"></a>'

        ### Add description? n_poch, n_ifg, url, networkpng
        properties = {"name": frameid, "description": descr,
                      "_color": line_color, "_opacity": line_opacity,
                       "_weight": line_width, "_fillColor": color,
                       "_fillOpacity": fill_opacity}
        out_feature = {'type': 'Feature', 'properties': properties,
                       'geometry': geometry}

        # Identify tile ID
        x, y = latlon2tileid(lat_c, lon_c, zl)

        # Add feature
        out_jsonfile = os.path.join(bname+f'{AD}{inc}', str(zl), str(x),
                                    str(y)+'.geojson')
        add_feature(out_feature, out_jsonfile)


        # %% Remove geojson
        elapsed_time1 = datetime.timedelta(seconds=(time.time()-start1))
        print(f"# im: {n_im}, Elapsed time: {elapsed_time1}")


    # %% Finish
    elapsed_time = datetime.timedelta(seconds=(time.time()-start))
    print(f"\nElapsed time: {elapsed_time}")
    print(f'\n{prog} Successfully finished!!\n')

    print(f"Output: {bname}[AD][inc]\n")


# %% main
if __name__ == "__main__":
    sys.exit(main())
