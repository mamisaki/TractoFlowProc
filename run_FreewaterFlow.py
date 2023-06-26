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
import shlex
import subprocess
import sys
import shutil
import time
from socket import gethostname

import psutil
import numpy as np


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog='run_FreewaterFlow',
        description='Run FreewaterFlow pipeline')

    parser.add_argument('tf_results_folder', help='TractFlow results folder')
    parser.add_argument('--workplace', help='Local working place')
    parser.add_argument('--num_proc', default=0, type=int,
                        help='Maximum number of subjects'
                        'processed simultaneously')
    parser.add_argument('--main_nf',
                        default=(Path.home() / 'freewater_flow' / 'main.nf'),
                        help='freewater_flow main.nf file')
    parser.add_argument('--b_thr', type=float,
                        help='Limit value to consider that a b-value is on' +
                        ' an existing shell. The default is 40.')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    tf_results_folder = Path(args.tf_results_folder).resolve()
    assert tf_results_folder.is_dir(), f"No directory at {tf_results_folder}"

    num_proc = args.num_proc
    num_proc_possible = max(int(np.round(psutil.virtual_memory().available /
                                         (20 * 10e8))), 1)
    if num_proc == 0:
        num_proc = num_proc_possible
    else:
        num_proc = min(num_proc, num_proc_possible)

    main_nf = args.main_nf
    b_thr = args.b_thr
    workplace = args.workplace
    if workplace is not None:
        workplace = Path(workplace).resolve()
    overwrite = args.overwrite

    '''DEBUG
    tf_results_folder = Path.home() / \
        'MRI/TractFlow_workspace/DTI_AdolescentData/results'
    main_nf = Path.home() / 'freewater_flow' / 'main.nf'
    copy_local = False
    workplace = None
    overwrite = False
    '''

    wd0 = tf_results_folder.parent

    if workplace is None:
        tmp_workplace = True
        workplace = Path.home() / 'fwflow_work'
    else:
        tmp_workplace = False

    file_patterns = {'dwi.nii.gz': ('Resample_DWI',  '__dwi_resampled.nii.gz'),
                     'bval': ('Eddy_Topup', '__bval_eddy'),
                     'bvec': ('Eddy_Topup', '__dwi_eddy_corrected.bvec'),
                     'brain_mask.nii.gz': ('Extract_B0',
                                           '__b0_mask_resampled.nii.gz')
                     }

    # --- Proc loop -----------------------------------------------------------
    while True:
        # Get input data
        sub_dirs = [sub_dir for sub_dir in tf_results_folder.glob('*')
                    if sub_dir.is_dir() and
                    sub_dir.name not in ('Readme', 'Compute_Kernel')]

        # Check if the job is done
        done_subj = []
        for sub_dir in sub_dirs:
            sub = sub_dir.name
            results_dir = tf_results_folder / sub
            last_f = results_dir / 'FW_Corrected_Metrics' / \
                f"{sub}__fw_corr_tensor.nii.gz"
            if last_f.is_file() and not overwrite:
                done_subj.append(sub_dir)

        # Check running process
        for isrun in wd0.glob('IsRun_FWF_*'):
            with open(isrun, 'r') as fd:
                run_subjs = [tf_results_folder / subj
                             for subj in fd.read().rstrip().split(',')]
            done_subj.extend(run_subjs)

        done_subj = np.unique(done_subj)
        sub_dirs = np.setdiff1d(sub_dirs, done_subj)
        if len(sub_dirs) == 0:
            break

        # Process num_proc subjects at once
        sub_dirs = sub_dirs[:num_proc]

        # Put IsRun
        IsRun = wd0 / f'IsRun_FWF_{gethostname()}'
        run_subjs = [d.name for d in sub_dirs]
        with open(IsRun, 'w') as fd:
            print(','.join(run_subjs), file=fd)

        # --- Prepare input files ---------------------------------------------
        if tmp_workplace and workplace.is_dir():
            shutil.rmtree(workplace)

        if not workplace.is_dir():
            workplace.mkdir()

        fwflow_input_dir = workplace / 'fwflow_input'
        if fwflow_input_dir.is_dir():
            shutil.rmtree(fwflow_input_dir)
        fwflow_input_dir.mkdir()

        print('Copy tractflow results for freewater_flow')
        excld_subj = []
        for sub_dir in sub_dirs:
            if not sub_dir.is_dir():
                continue

            sub = sub_dir.name
            dst_dir = fwflow_input_dir / sub
            if not dst_dir.is_dir():
                dst_dir.mkdir()

            for dst_pat, src_pat in file_patterns.items():
                dst_f = dst_dir / dst_pat
                src_f = sub_dir / src_pat[0] / f"{sub}{src_pat[1]}"
                if not src_f.is_file():
                    src_f = sub_dir / src_pat[0].replace('_Topup', '') / \
                        f"{sub}{src_pat[1]}"
                    if not src_f.is_file():
                        print(f"Not found {src_f} for {dst_f.name}")
                        shutil.rmtree(dst_dir)
                        excld_subj.append(sub_dir)
                        break
                dst_f.symlink_to(src_f)

        sub_dirs = np.setdiff1d(sub_dirs, excld_subj)

        # --- Run freewater_flow ----------------------------------------------
        cmd = f"nextflow run -bg {main_nf} --input {fwflow_input_dir} -w q"
        if b_thr is not None:
            cmd += f" --bthr {b_thr}"
        try:
            print('-' * 80)
            print(f"Run {cmd} at {workplace} in background.")
            sys.stdout.flush()
            subprocess.check_call(shlex.split(cmd), cwd=workplace)
        except Exception:
            print(f"Failed to run {cmd}")
            sys.exit()

        # Wait for complete
        while True:
            # Check if all the result filese are made
            done_subj = []
            for sub_dir in sub_dirs:
                sub = sub_dir.name
                results_dir = fwflow_input_dir.parent / 'results' / sub
                last_f = results_dir / 'FW_Corrected_Metrics' / \
                    f"{sub}__fw_corr_tensor.nii.gz"
                if last_f.is_file():
                    done_subj.append(sub_dir)

            last_subs = np.setdiff1d(sub_dirs, done_subj)
            if len(last_subs) == 0:
                break

            # Check if the process is running
            cmd = f"pgrep -f 'run -bg {main_nf}'"
            try:
                out = subprocess.check_output(shlex.split(cmd))
            except Exception:
                break

            time.sleep(10)

        # --- Copy back -------------------------------------------------------
        shutil.rmtree(fwflow_input_dir)
        cmd = "rsync -rtuvz --copy-links --exclude='.nextflow*' --exclude='q'"
        cmd += f" --exclude='fwflow_input' {workplace}/ {wd0}/"
        subprocess.run(shlex.split(cmd))

        if IsRun.is_file():
            IsRun.unlink()

    if tmp_workplace and workplace.is_dir():
        shutil.rmtree(workplace)
