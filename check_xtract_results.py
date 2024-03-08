#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# %% import ===================================================================
import argparse
from pathlib import Path
import numpy as np

import pandas as pd

if '__file__' not in locals():
    __file__ = 'this.py'


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog='run_XTRACT.py',
        description='Run FSL XTRACT to extract major tracts and there stats')

    parser.add_argument('FDT_folder', help='FDT results folder')

    args = parser.parse_args()
    FDT_folder = Path(args.FDT_folder).resolve()

    # --- XTRACT ----------------------------------------------------------
    # Get input data
    sub_dirs = [sub_dir for sub_dir in FDT_folder.glob('*.xtract')
                if sub_dir.is_dir()]

    for sub_dir in sub_dirs:
        stat_tab = pd.read_csv(sub_dir / 'stats.csv', index_col=0)
        missing_tract = stat_tab.index[np.any(stat_tab == 0, axis=1)]
        if len(missing_tract):
            print(f"{sub_dir.name}: xtract missing {missing_tract}")
            print(stat_tab.loc[missing_tract])


# %%
