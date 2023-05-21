#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" run_TractFlow.py
https://tractoflow-documentation.readthedocs.io/en/latest/index.html
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
        prog='run_TractFlow',
        description='Run TractFlow pipeline')

    parser.add_argument('input', help='input folder')
    parser.add_argument('--use_cuda', action='store_true',
                        help='Use eddy_cuda for Eddy process')
    parser.add_argument('--fully_reproducible', action='store_true',
                        help='All the parameters will be set to have'
                        ' 100% reproducible')
    parser.add_argument('--ABS', action='store_true',
                        help='TractoFlow-ABS (Atlas Based Segmentation)'
                        ' is used.')
    parser.add_argument('--fs', help='FreeSurfer output folder')
    parser.add_argument('--copy_local', action='store_true',
                        help='Copy local working place')
    parser.add_argument('--workplace', help='Local working place')
    parser.add_argument('--with_docker', action='store_true',
                        help='with docker')
    parser.add_argument('--processes', help='The number of parallel processes'
                        ' to launch.')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    input_orig = Path(args.input).resolve()
    assert input_orig.is_dir(), f"No directory at {input_orig}"

    use_cuda = args.use_cuda
    fully_reproducible = args.fully_reproducible
    ABS = args.ABS
    fs = args.fs
    if ABS and fs is None:
        fs = input_orig.parent / 'freesurfer'
    copy_local = args.copy_local
    workplace = args.workplace
    if copy_local and workplace is not None:
        workplace = Path(workplace).resolve()
    with_docker = args.with_docker
    processes = args.processes
    overwrite = args.overwrite

    ''' DEBUG
    input_orig = Path.home() / 'MRI' / 'TractFlow_workspace' / 'RNT_decoding' \
        / 'input'
    use_cuda = False
    fully_reproducible = True
    ABS = False
    copy_local = False
    workplace = None
    with_docker = True
    processes = None
    overwrite = False
    '''

    # --- Find unprocessed data -----------------------------------------------
    sub_dirs = [sub_dir for sub_dir in input_orig.glob('*')
                if sub_dir.is_dir()]

    # Check if the job is done
    done_subj = []
    for sub_dir in sub_dirs:
        sub = sub_dir.name
        results_dir = input_orig.parent / 'results' / sub
        last_f = results_dir / 'PFT_Tracking' / \
            f"{sub}__pft_tracking_prob_wm_seed_0.trk"
        if last_f.is_file() and not overwrite:
            done_subj.append(sub_dir)

    sub_dirs = np.setdiff1d(sub_dirs, done_subj)

    # --- Prepare input files -------------------------------------------------
    wd0 = input_orig.parent

    tractflow_input_dir = input_orig.parent / 'tractflow_input'
    if tractflow_input_dir.is_dir():
        shutil.rmtree(tractflow_input_dir)
    tractflow_input_dir.mkdir()

    print('Copy tractflow input files')
    for sub_dir in sub_dirs:
        if not sub_dir.is_dir():
            continue

        sub = sub_dir.name
        dst_dir = tractflow_input_dir / sub
        if not dst_dir.is_dir():
            dst_dir.mkdir()

        for src_f in sub_dir.glob('*'):
            if not src_f.is_file():
                continue
            dst_f = dst_dir / src_f.name
            dst_f.symlink_to(src_f)

    # --- Copy to local working place -----------------------------------------
    if copy_local:
        if workplace is None:
            workplace = Path.home() / 'TractFlowWork_local'

        if not workplace.is_dir():
            try:
                os.makedirs(workplace)
            except Exception:
                print(f"Failed to create {workplace}")
                sys.exit()

        cmd = f"rsync -auvz --include='{tractflow_input_dir.name}'"
        cmd += f" --include='{tractflow_input_dir.name}/**'"
        if not overwrite:
            if (wd0 / 'work').is_dir():
                cmd += " --include='work' --include='work/**'"
            if (wd0 / 'results').is_dir():
                cmd += " include='results' --include='results/**'"
        cmd += " --exclude='*'"
        cmd += f" {wd0}/ {workplace}/"
        try:
            subprocess.check_call(shlex.split(cmd))
        except Exception:
            print(f"Failed to rsync {wd0} to {workplace}")
            sys.exit()

        tractflow_input_dir = workplace / tractflow_input_dir.name
        wd = workplace

    # --- Run TractFlow -------------------------------------------------------
    cmd = f"nextflow run -bg tractoflow -r 2.4.1 --input {tractflow_input_dir}"
    if ABS:
        cmd += " --fs {fs}"
    if processes is not None:
        cmd += " --processes {processes}"

    profile = ['cbrain']  # Copy all the output files, not use symlinks.
    if use_cuda:
        profile.append('use_cuda')

    if fully_reproducible:
        profile.append('fully_reproducible')

    if ABS:
        profile.append('ABS')

    if len(profile):
        cmd += f" -profile {','.join(profile)}"

    if with_docker:
        cmd += ' -with-docker scilus/scilus:1.4.2'
    cmd += ' -resume'

    try:
        subprocess.check_call(shlex.split(cmd), cwd=wd)
    except Exception:
        print(f"Failed to run {cmd}")
        sys.exit()

    # --- Copy back -----------------------------------------------------------
    if copy_local:
        cmd = f"rsync -auvx {workplace}/ {wd0}/"
        try:
            subprocess.check_call(shlex.split(cmd))
        except Exception:
            print(f"Failed to run {cmd}")
            sys.exit()
