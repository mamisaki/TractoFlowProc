#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" run XTRACT
https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/XTRACT
"""

# %% import ===================================================================
import argparse
from pathlib import Path
import shlex
import subprocess
import numpy as np

from mproc import run_multi_shell

if '__file__' not in locals():
    __file__ = 'run_XTRACT.py'


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog='run_XTRACT',
        description='Run FSL XTRACT to extract major tracts and there stats')

    parser.add_argument('FDT_folder', help='FDT results folder')
    parser.add_argument('--gpu', action='store_true', help='Use GPU')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    FDT_folder = Path(args.FDT_folder).resolve()
    assert FDT_folder.is_dir(), f"No directory at {FDT_folder}"
    gpu = args.gpu
    overwrite = args.overwrite

    '''DEBUG
    FDT_folder = Path.home() / \
        'MRI/TractFlow_workspace/DTI_AdolescentData/FDT'
    gpu = True
    overwrite = False
    '''

    # --- XTRACT ----------------------------------------------------------
    # Get input data
    SUB_DIRS = [sub_dir for sub_dir in FDT_folder.glob('*.bedpostX')
                if sub_dir.is_dir()]

    # Check if the job is done
    done_subj = []
    for sub_dir in SUB_DIRS:
        sub = sub_dir.name.replace('.bedpostX', '')
        res_dir = FDT_folder / f"{sub}.xtract"
        last_f = res_dir / 'tracts' / 'vof_r' / 'densityNorm.nii.gz'
        if last_f.is_file() and not overwrite:
            done_subj.append(sub_dir)
    SUB_DIRS = np.setdiff1d(SUB_DIRS, done_subj)

    # run xtract
    for sub_dir in SUB_DIRS:
        sub = sub_dir.name.replace('.bedpostX', '')
        res_dir = FDT_folder / f"{sub}.xtract"

        # XTRACT
        cmd = f"xtract -bpx {sub_dir} -out {res_dir} -species HUMAN"
        if gpu:
            cmd += ' -gpu'
        subprocess.check_call(shlex.split(cmd))

    # --- run xtract_stats ----------------------------------------------------
    # Get input data
    SUB_DIRS = [sub_dir for sub_dir in FDT_folder.glob('*.xtract')
                if sub_dir.is_dir()]

    # Check if the job is done
    done_subj = []
    for sub_dir in SUB_DIRS:
        last_f = sub_dir / 'stats.csv'
        if last_f.is_file() and not overwrite:
            done_subj.append(sub_dir)
    SUB_DIRS = np.setdiff1d(SUB_DIRS, done_subj)

    Cmds = []
    JobNames = []
    for sub_dir in SUB_DIRS:
        last_f = sub_dir / 'tracts' / 'vof_r' / 'densityNorm.nii.gz'
        if not last_f.is_file():
            continue

        # xtract_stats
        sub = sub_dir.name.replace('.xtract', '')
        w = sub_dir.parent / f"{sub}.bedpostX" / 'xfms' / 'standard2diff'
        dti_dir = sub_dir.parent / sub / 'DTI_'
        r = sub_dir.parent / sub / 'DTI_FA.nii.gz'
        if not r.is_file():
            continue

        cmd = f"xtract_stats -d {dti_dir} -xtract {sub_dir} -w {w} -r {r}"
        cmd += ' -meas AD,FA,GA,MD,RD'
        Cmds.append(cmd)
        JobNames.append(f"xtract_stats_{sub}")

    if len(Cmds):
        run_multi_shell(Cmds, JobNames)
