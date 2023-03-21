#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" run_FreewaterFlow.py

INSTALL
---
# Download git repositories
cd
git clone https://github.com/scilus/scilpy.git
git clone https://github.com/scilus/freewater_flow

# Install scilpy
conda create -n tractflow python=3.10 pip hdf5=1.12 cython numpy -c anaconda
conda activate tractflow

cd ~/scilpy
pip install -e .
"""

# %% import ===================================================================
import argparse
from pathlib import Path
import os
import shlex
import subprocess
import sys
import shutil

import numpy as np


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog = 'run_FreewaterFlow',
        description = 'Run FreewaterFlow pipeline')
    
    parser.add_argument('tf_results_folder', help='TractFlow results folder')
    parser.add_argument('--main_nf',
                        default=(Path.home() / 'freewater_flow' / 'main.nf'),
                        help='freewater_flow main.nf file')
    parser.add_argument('--copy_local', action='store_true',
                        help='Copy local working place')
    parser.add_argument('--workplace', default=(Path.home() / 'FWFlow_work'),
                        help='Local working place')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    tf_results_folder = Path(args.tf_results_folder).resolve()
    assert tf_results_folder.is_dir(), f"No directory at {tf_results_folder}"
    main_nf = args.main_nf
    copy_local = args.copy_local
    workplace = args.workplace
    if workplace is not None:
        workplace = Path(workplace).resolve()
    overwrite = args.overwrite

    # --- Get input data dirs -------------------------------------------------
    sub_dirs = [sub_dir for sub_dir in tf_results_folder.glob('*')
                if sub_dir.is_dir() and
                sub_dir.name not in ('Readme', 'Compute_Kernel')]

    # Check if the job is done
    done_subj = []
    for sub_dir in sub_dirs:
        sub = sub_dir.name
        results_dir = tf_results_folder.parent / 'results' / sub
        last_f = results_dir / 'FW_Corrected_Metrics' / \
            f"{sub}__fw_corr_tensor.nii.gz"
        if last_f.is_file() and not overwrite:
            done_subj.append(sub)
    
    sub_dirs = np.setdiff1d(sub_dirs, done_subj)

    # --- Prepate input files -------------------------------------------------
    wd0 = tf_results_folder.parent
    fwflow_input_dir = wd0 / 'fwflow_input'
    if not fwflow_input_dir.is_dir():
        fwflow_input_dir.mkdir()

    file_patterns = {'dwi.nii.gz': ('Resample_DWI',  '__dwi_resampled.nii.gz'),
                     'bval': ('Eddy_Topup', '__bval_eddy'),
                     'bvec': ('Eddy_Topup', '__dwi_eddy_corrected.bvec'),
                     'brain_mask.nii.gz': ('Extract_B0',
                                           '__b0_mask_resampled.nii.gz')
    }

    print('Copy tractflow results for freewater_flow')
    for sub_dir in sub_dirs:
        if not sub_dir.is_dir():
            continue
        
        sub = sub_dir.name
        dst_dir = fwflow_input_dir / sub
        if not dst_dir.is_dir():
            dst_dir.mkdir()
        
        for dst_pat, src_pat in file_patterns.items():
            dst_f = dst_dir / dst_pat
            if not dst_f.is_file() or overwrite:
                src_f = sub_dir / src_pat[0] / f"{sub}{src_pat[1]}"
                if not src_f.is_file():
                    print(f"Not found {src_f} for {dst_f.name}")
                    continue
                
                print(f"Link {dst_f.relative_to(wd0)} to"
                      f" {src_f.relative_to(wd0)}")
                dst_f.symlink_to(src_f)
                #shutil.copyfile(src_f, dst_f, follow_symlinks=True)

    # --- Prepare local workplace ---------------------------------------------
    if copy_local:
        if not workplace.is_dir():
            try:
                os.makedirs(workplace)
            except Exception:
                print(f"Failed to create {workplace}")
                sys.exit()
    else:
        workplace = wd0

    # --- Run freewater_flow --------------------------------------------------
    cmd = f"nextflow run -bg {main_nf} --input {fwflow_input_dir}"
    try:
        print('-' * 80)
        print(f"Run {cmd} at {workplace} in background.")
        sys.stdout.flush()
        subprocess.check_call(shlex.split(cmd), cwd=workplace)
    except Exception:
        print(f"Failed to run {cmd}")
        sys.exit()

    # Wait for finish
    while True:
        done_subj = []
        for sub_dir in sub_dirs:
            sub = sub_dir.name
            results_dir = tf_results_folder.parent / 'results' / sub
            last_f = results_dir / 'FW_Corrected_Metrics' / \
                f"{sub}__fw_corr_tensor.nii.gz"
            if last_f.is_file() and not overwrite:
                done_subj.append(sub)

        last_dirs = np.setdiff1d(sub_dirs, done_subj)
        if len(last_dirs) == 0:
            break

    # --- Copy back ------------------------------------------------------------
    if copy_local:
        cmd = f"rsync -rtvz --copy-links"
        cmd += " --include='results' --include='results/**'"
        cmd += " --include='work' --include='work/**'"
        cmd += f" --exclude='*' {workplace}/ {wd0}/"
        try:
            subprocess.check_call(shlex.split(cmd))
        except Exception:
            print(f"Failed to run {cmd}")
            sys.exit()
