#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" run_TractFlow.py
"""

# %% import ===================================================================
import argparse
from pathlib import Path
import os
import shlex
import subprocess
import sys


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog = 'run_TractFlow',
        description = 'Run TractFlow pipeline')
    
    parser.add_argument('input_folder', help='input folder')
    parser.add_argument('--use_cuda', action='store_true',
                        help='Use eddy_cuda for Eddy process')
    parser.add_argument('--fully_reproducible', action='store_true',
                        help='All the parameters will be set to have 100% reproducible')
    parser.add_argument('--ABS', action='store_true',
                        help='TractoFlow-ABS (Atlas Based Segmentation) is used.')
    parser.add_argument('--fs', help='FreeSurfer output folder')
    parser.add_argument('--copy_local', action='store_true',
                        help='Copy local working place')
    parser.add_argument('--workplace', help='Local working place')
    parser.add_argument('--with_docker', action='store_true',
                        help='with docker')
    parser.add_argument('--processes', help='The number of parallel processes to launch.')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    input_folder = Path(args.input_folder).resolve()
    assert input_folder.is_dir(), f"No directory at {input_folder}"
    
    use_cuda = args.use_cuda
    fully_reproducible = args.fully_reproducible
    ABS = args.ABS
    fs = args.fs
    if ABS and fs is None:
        fs = input_folder.parent / 'freesurfer'
    copy_local = args.copy_local
    workplace = args.workplace
    if copy_local and workplace is not None:
        workplace = Path(workplace).resolve()
    with_docker = args.with_docker
    processes = args.processes
    overwrite = args.overwrite
    
    # --- Copy to local working place -----------------------------------------
    wd = input_folder.parent
    if copy_local:
        if workplace is None:
            workplace = Path.home() / 'TractFlowWork_local'

        if not workplace.is_dir():
            try:
                os.makedirs(workplace)
            except Exception:
                print(f"Failed to create {workplace}")
                sys.exit()

        cmd = f"rsync -auvz --include='{input_folder.name}'"
        cmd += f" --include='{input_folder.name}/**'"
        if not overwrite:
            if (input_folder.parent / 'work').is_dir():
                cmd += " --include='work' --include='work/**'"
            if (input_folder.parent / 'results').is_dir():
                cmd += " include='results' --include='results/**'"
        cmd += " --exclude='*'"
        cmd += f" {input_folder.parent}/ {workplace}/"
        try:
            subprocess.check_call(shlex.split(cmd))
        except Exception:
            print(f"Failed to rsync {input_folder.parent} to {workplace}")
            sys.exit()
        
        input_folder0 = input_folder
        input_folder = workplace / input_folder.name
        wd = workplace

    # --- Run TractFlow -------------------------------------------------------
    cmd = f"nextflow run -bg tractoflow -r 2.4.1 --input {input_folder}"
    if ABS:
        cmd += " --fs {fs}"
    if processes is not None:
        cmd += " --processes {processes}"

    profile = ['cbrain']
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

    # --- Copy back ------------------------------------------------------------
    if copy_local:
        cmd = f"rsync -rtvz --copy-links {workplace}/"
        cmd += f" {input_folder0.parent}/"
        try:
            subprocess.check_call(shlex.split(cmd))
        except Exception:
            print(f"Failed to run {cmd}")
            sys.exit()

