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
from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import matplotlib as mpl

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


# %% plot_network
def plot_network(bperp_dict, unwrates_dict, pngfile):
    """
    Plot network of interferometric pairs with colors of unw_rate.
    """

    imdates = list(bperp_dict.keys())
    bperp = list(bperp_dict.values())
    bperp_center = (max(bperp)+min(bperp))/2
    n_im = len(imdates)
    imdates_dt = np.array(([datetime.datetime.strptime(imd, '%Y%m%d')
                            for imd in imdates]))

    # Plot fig
    fig = plt.figure(figsize=(12, 5))
    ax = fig.add_axes([0.08, 0.10, 0.87,0.88])

    cmap = plt.get_cmap('cividis_r', 100)

    for i, imd in enumerate(imdates):
        # Epochs
        ax.scatter(imdates_dt[i], bperp[i], c='k', alpha=0.6, zorder=101)
        if bperp[i] > bperp_center: va='bottom'
        else: va = 'top'
        ax.annotate(imd[4:6]+'/'+imd[6:],
                    (imdates_dt[i], bperp[i]), ha='center', va=va, zorder=102)

        # Interferograms
        for j in range(i+1, n_im):
            unwrate1 = int(unwrates_dict[f'{imd}_{imdates[j]}'])
            ax.plot([imdates_dt[i], imdates_dt[j]], [bperp[i], bperp[j]],
                     color=cmap(unwrate1), alpha=0.8, zorder=unwrate1,
                     linewidth=2)

    # Locater
    loc = ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))
    ax.grid(visible=True, which='major')

    # Add bold line every 1yr
    ax.xaxis.set_minor_locator(mdates.YearLocator())
    ax.grid(visible=True, which='minor', linewidth=2)

    ax.set_xlim((datetime.datetime.strptime('20060501', '%Y%m%d'),
                 datetime.datetime.strptime('20110430', '%Y%m%d')))

    # Labels and legend
    plt.xlabel('Time')
    plt.ylabel('Bperp [m]')

    # Colorbar
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="2%", pad=0.05)
    norm = mpl.colors.Normalize(vmin=0, vmax=100)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cbar = plt.colorbar(sm, cax=cax, alpha=0.8)
    cbar.set_label('Unwrap rate (%)')

    # Save
    plt.savefig(pngfile)
    plt.close()


# %% Main
def main(argv=None):

    # %% Settings
#    colorA = "#0000ff"
#    colorD = "#ff0000"
    line_color = "#ff0000"
    line_opacity = 0.7
    line_width = 1
    fill_opacity = 0.5

    url_list_base = 'https://gsrt.digiarc.aist.go.jp/insarbrowser/doc'
    url_alltxt = os.path.join(url_list_base, 'all_products_list.txt')
    url_gunw_base = 'https://s3.abci.ai/palsar-insar-pds/P1INSAR/GUNW'

    errlist = 'err_frames.txt'
    if os.path.exists(errlist):
        os.remove(errlist)


    # %% Read arg
    start = time.time()
    prog = os.path.basename(sys.argv[0])
    description = 'Create GeoJSON tile of AIST ALOS frame map for GSIMaps.'
    print(f"\n{prog} ver1.0.0 20220630 Y. Morishita")
    print(f"{prog} {' '.join(sys.argv[1:])}\n")

    parser = argparse.ArgumentParser(description=description)
    addarg = parser.add_argument
    addarg('-z', '--zoomlevel', type=int, default=6,
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

    if os.path.exists('network'):
        subprocess.run(['rm', '-rf', 'network'])
    os.mkdir('network')


    # %% For each frames
    print('Get all_products_list.txt')
    all_list = requests.get(url_alltxt).text.splitlines()
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
        if int(path) > 320: # not sure exact boundary
            AD = 'A'
#           color = colorA
        else:
            AD = 'D'
#           color = colorD

        products_list = requests.get(plisttxt).text.splitlines()

        # Unwrap rate
        url_unwratetxt = os.path.join(url_list_base, frameid,
                                      'unwrap_rates_list.txt')
        unwrates = requests.get(url_unwratetxt).text.splitlines()
        unwrates_dict = {}
        for l in unwrates:
            unwrates_dict[l.split(',')[0]] = float(l.split(',')[1])

        # bperp and number
        url_baselines = os.path.join(url_gunw_base, frameid,
                                     f'{frameid}_GUNW.baselines')
        baselines = requests.get(url_baselines).text.splitlines()
        bperp_dict = {} # e.g. '20070312': 19.008
        for l in baselines:
            bperp_dict[l.split()[1]] = float(l.split()[-2])
            bperp_dict[l.split()[2]] = float(l.split()[-1])

        n_im = len(bperp_dict)
        n_ifg = int(n_im*(n_im-1)/2)

        if n_im >= 32:
            color = "#ff0000"
        color = "#ff"+hex(255-n_im*8)[2:].zfill(2)*2

        # latlon
        url_gunwtxt = None
        for file in products_list:
            if 'GUNW.txt' in file:
                url_gunwtxt = file
                break
        gunwtxt = requests.get(url_gunwtxt).text.splitlines()

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



        # %% Create network plot
        pngfile = os.path.join('network', f'network_{frameid}.png')
        try:
            plot_network(bperp_dict, unwrates_dict, pngfile)
        except:
            with open(errlist, 'a') as f:
                print(frameid, file=f)
        url_networkpng = os.path.join(url_list_base, frameid,
                                      f'network_{frameid}.png')


        # %% Append geojson
        coords = [[[lon_sn, lat_sn], [lon_sf, lat_sf], [lon_ef, lat_ef],
                   [lon_en, lat_en], [lon_sn, lat_sn]]]
        geometry = {"type": "Polygon", "coordinates": coords}
        descr = f'# epochs: {n_im}<br># ifgs: {n_ifg}<br>' \
                f'<a href="{plisttxt}" target="_blank">Product list</a><br>' \
                f'<a href="{url_networkpng}" target="_blank">' \
                f'<img src="{url_networkpng}"></a>'

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
