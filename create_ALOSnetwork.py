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
import numpy as np
import requests
from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import matplotlib as mpl
from matplotlib.patheffects import withStroke
from adjustText import adjust_text

os.environ['LANG'] = 'en_US.UTF-8'
mpl.use('Agg')


# %% plot_network
def plot_network(bperp_dict, unwrates_dict, frameid, pngfile):
    """
    Plot network of interferometric pairs with colors of unw_rate.
    """

    imdates = list(bperp_dict.keys())
    bperp = list(bperp_dict.values())
    n_im = len(imdates)
    imdates_dt = np.array(([datetime.datetime.strptime(imd, '%Y%m%d')
                            for imd in imdates]))

    # Plot fig
    fig = plt.figure(figsize=(12, 5))
    ax = fig.add_axes([0.08, 0.10, 0.87,0.88])

    cmap = plt.get_cmap('cividis_r', 100)
    texts = []
    effects = [withStroke(linewidth=2, foreground="w")]

    for i, imd in enumerate(imdates):
        # Epochs
        ax.scatter(imdates_dt[i], bperp[i], c='k', alpha=0.6, zorder=101)
        if imdates_dt[i].date() > datetime.date(2008, 8, 3):
            va, ha = 'top', 'left'
        else:
            va, ha = 'bottom', 'right'
        text = ax.annotate(imd[4:6]+'/'+imd[6:], (imdates_dt[i], bperp[i]),
                           ha=ha, va=va, zorder=102, fontweight='normal',
                           path_effects=effects, alpha=0.8)
        texts.append(text)

        # Interferograms
        for j in range(i+1, n_im):
            unwrate1 = int(unwrates_dict[f'{imd}_{imdates[j]}'])
            ax.plot([imdates_dt[i], imdates_dt[j]], [bperp[i], bperp[j]],
                     color=cmap(unwrate1), alpha=0.8, zorder=unwrate1,
                     linewidth=2)

    adjust_text(texts)

    # Locater
    loc = ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))
    ax.grid(visible=True, which='major')

    # Add bold line every 1yr
    ax.xaxis.set_minor_locator(mdates.YearLocator())
    ax.grid(visible=True, which='minor', linewidth=2)

    ax.set_xlim((datetime.datetime.strptime('20060208', '%Y%m%d'),
                 datetime.datetime.strptime('20110801', '%Y%m%d')))

    # Labels and legend
    plt.xlabel('Time [year]')
    plt.ylabel('Bperp [m]')
    plt.text(0.01, 0.95, frameid, fontweight='bold', transform=ax.transAxes)

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
    url_list_base = 'https://gsrt.digiarc.aist.go.jp/insarbrowser/doc'
    url_gunw_base = 'https://s3.abci.ai/palsar-insar-pds/P1INSAR/GUNW'


    # %% Read arg
    start = time.time()
    prog = os.path.basename(sys.argv[0])
    description = 'Create network plot of AIST ALOS frame.'
    print(f"\n{prog} ver1.0.0 20220714 Y. Morishita")
    print(f"{prog} {' '.join(sys.argv[1:])}\n")

    parser = argparse.ArgumentParser(description=description)
    addarg = parser.add_argument
    addarg('-f', '--frameid', type=str, help='Frame id (e.g., 045_2700_343)')
    args = parser.parse_args()
    frameid = args.frameid


    # %% Output network dir
    os.makedirs('network', exist_ok=True)


    # %% Read info
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


    # %% Create network plot
    pngfile = os.path.join('network', f'network_{frameid}.png')
    plot_network(bperp_dict, unwrates_dict, frameid, pngfile)


    # %% Finish
    elapsed_time = datetime.timedelta(seconds=(time.time()-start))
    print(f"\nElapsed time: {elapsed_time}")
    print(f'\n{prog} Successfully finished!!\n')

    print(f"Output: {pngfile}\n")


# %% main
if __name__ == "__main__":
    sys.exit(main())
