#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" run_TractoFlow.py
https://tractoflow-documentation.readthedocs.io/en/latest/index.html
"""

# %% import ===================================================================
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys
import shutil
import time
from socket import gethostname
import numpy as np
import psutil


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog='run_TractoFlow.py',
        description='Run TractoFlow pipeline')

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
    parser.add_argument('--workplace', help='Local working place')
    parser.add_argument('--num_proc', default=0, type=int,
                        help='Maximum number of subjects'
                        'processed simultaneously')
    parser.add_argument('--with_docker', action='store_true',
                        help='with docker')
    parser.add_argument('--processes', help='The number of parallel processes'
                        ' to launch.')
    parser.add_argument('--tempdir', help='Singurality tmp dir')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    input_orig = Path(args.input).resolve()
    use_cuda = args.use_cuda
    fully_reproducible = args.fully_reproducible
    ABS = args.ABS
    fs = args.fs
    workplace = args.workplace
    num_proc = args.num_proc
    with_docker = args.with_docker
    processes = args.processes
    tmpdir = args.tempdir
    overwrite = args.overwrite

    ''' DEBUG
    input_orig = Path.home() / 'MRI' / 'TractoFlow_workspace' / \
        'DTI_AdolescentData' / 'input_CW'
    use_cuda = False
    fully_reproducible = True
    ABS = False
    workplace = None
    num_proc = 0
    with_docker = True
    processes = None
    overwrite = False
    '''

    assert input_orig.is_dir(), f"No directory at {input_orig}"
    if ABS and fs is None:
        fs = input_orig.parent / 'freesurfer'
    if workplace is not None:
        workplace = Path(workplace).resolve()
    num_proc_possible = max(int(np.round(psutil.virtual_memory().available /
                                         (10 * 10e8))), 1)
    if num_proc == 0:
        num_proc = num_proc_possible
    else:
        num_proc = min(num_proc, num_proc_possible)

    wd0 = input_orig.parent

    if workplace is None:
        tmp_workplace = True
        workplace = Path.home() / 'tractoflow_work'
    else:
        tmp_workplace = False

    if not with_docker:
        sif_files = sorted(
            list(Path(__file__).resolve().parent.glob('scilus*.sif')))
        assert len(sif_files), \
            f'Not found scilus*.sif file in {Path(__file__).resolve().parent}'
        sif_file = sif_files[-1]

    # --- Proc loop -----------------------------------------------------------
    while True:
        # -- Find unprocessed data ----
        sub_dirs = [sub_dir for sub_dir in input_orig.glob('*')
                    if sub_dir.is_dir()]
        required_files = ['bval', 'bvec', 'dwi.nii.gz', 't1.nii.gz']

        # Check if the job is done
        done_subj = []
        for sub_dir in sub_dirs:
            sub = sub_dir.name
            results_dir = input_orig.parent / 'results' / sub
            last_f = results_dir / 'PFT_Tracking' / \
                f"{sub}__pft_tracking_prob_wm_seed_0.trk"
            if last_f.is_file() and not overwrite:
                done_subj.append(sub_dir)

            if not np.all([(sub_dir / ff).is_file() for ff in required_files]):
                done_subj.append(sub_dir)

        # Check running process
        for isrun in wd0.glob('IsRun_TrF_*'):
            with open(isrun, 'r') as fd:
                run_subjs = [input_orig / subj
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

        print(f"{len(sub_dirs)} data will be processed.")

        # -- Prepare input files ----
        if tmp_workplace and workplace.is_dir():
            shutil.rmtree(workplace)

        if not workplace.is_dir():
            workplace.mkdir()

        tractoflow_input_dir = workplace / 'tractoflow_input'
        tractoflow_input_dir.mkdir()

        print('Link tractoflow input files')
        for sub_dir in sub_dirs:
            if not sub_dir.is_dir():
                continue

            sub = sub_dir.name
            dst_dir = tractoflow_input_dir / sub
            if not dst_dir.is_dir():
                dst_dir.mkdir()

            for src_f in sub_dir.glob('*'):
                if not src_f.is_file():
                    continue
                dst_f = dst_dir / src_f.name
                dst_f.symlink_to(src_f)

        # -- Run TractoFlow ----
        cmd = "nextflow run -bg tractoflow -r 2.4.2"
        cmd += f" --input {tractoflow_input_dir}"
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
            # cmd += ' -with-docker scilus/scilus:1.4.2'
            cmd += ' -with-docker scilus/scilus:1.5.0'
        else:
            cmd += f' -with-singularity {sif_file}'
        cmd += ' -resume'

        if tmpdir is not None:
            env = os.environ.copy()
            env["SINGULARITY_TMPDIR"] = tmpdir
        else:
            env = None

        try:
            subprocess.check_call(shlex.split(cmd), cwd=workplace, env=env)
        except Exception:
            print(f"Failed to run {cmd}")
            sys.exit()

        # Wait for complete
        tf_results_folder = workplace / 'results'

        while True:
            # Check if all the result filese are made
            done_subj = []
            for sub_dir in sub_dirs:
                sub = sub_dir.name
                results_dir = tf_results_folder.parent / 'results' / sub
                last_f = results_dir / 'PFT_Tracking' / \
                    f"{sub}__pft_tracking_prob_wm_seed_0.trk"
                if last_f.is_file() and not overwrite:
                    done_subj.append(sub_dir)

            last_dirs = np.setdiff1d(sub_dirs, done_subj)
            if len(last_dirs) == 0:
                break

            # Check if the process is running
            cmd = "pgrep -f 'run -bg tractoflow'"
            try:
                out = subprocess.check_output(shlex.split(cmd))
            except Exception:
                break

            time.sleep(10)

        # --- Copy back -------------------------------------------------------
        shutil.rmtree(tractoflow_input_dir)
        cmd = "rsync -rtuvz --copy-links --exclude='.nextflow*'"
        cmd += f" -exclude='tractoflow_input' {workplace}/ {wd0}/"
        subprocess.run(shlex.split(cmd))

        if IsRun.is_file():
            IsRun.unlink()

    if tmp_workplace and workplace.is_dir():
        shutil.rmtree(workplace)
