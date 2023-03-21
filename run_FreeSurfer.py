#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# %% import ===================================================================
import argparse
from pathlib import Path
import os
import shlex
import subprocess
import multiprocessing 

from mproc import run_multi_shell


# %% run_reconall =============================================================
def run_reconall(input_folder, FS_SUBJ_DIR):
    """
    Run FreeSurfer recon-all to create aparc+aseg and wmparc
    """
    
    if not FS_SUBJ_DIR.is_dir():
        os.makedirs(FS_SUBJ_DIR)

    # Get subject folders
    SUBJIDS = [dd.name for dd in input_folder.glob('*')
               if dd.is_dir() and (dd / 't1.nii.gz').is_file()]

    # Prepare command lines
    Cmds = []
    JobNames = []
    for subjid in SUBJIDS:
        dst_root = FS_SUBJ_DIR / subjid

        aseg_f = dst_root / 'mri' / 'aparc+aseg.mgz'
        wmparc_f = dst_root / 'mri' / 'wmparc.mgz'
        if aseg_f.is_file() and wmparc_f.is_file():
            continue

        IsRun = dst_root / 'scripts' / 'IsRunning.lh+rh'
        if IsRun.is_file():
            print(f"\n{IsRun.relative_to(FS_SUBJ_DIR)} exists."
                  f" Recon-all for {subjid} seems to be running.\n"
                  f"Otherwise, remove {IsRun} file.")
            continue

        # recon-all
        t1_src_f = input_folder / subjid / 't1.nii.gz'
        t2_src_f = input_folder / subjid / 't2.nii.gz'

        cmd = f"export SUBJECTS_DIR={FS_SUBJ_DIR}; recon-all -subjid {subjid}"
        orig_f = dst_root / 'mri' / 'orig' / '001.mgz'
        if not orig_f.is_file():
            cmd += f" -i {t1_src_f}"

        if t2_src_f.is_file():
            t2_f = dst_root / 'mri' / 'orig' / 'T2raw.mgz'
            if not t2_f.is_file():
                cmd += f" -T2 {t2_src_f}"
            cmd += " -T2pial"

        cmd += f" -all -openmp 4"

        Cmds.append(cmd)
        JobNames.append(f"Recon-all_{subjid}")

    # Run command list in parallel
    if len(Cmds) > 0:
        nr_proc = min(len(Cmds), max(int(multiprocessing.cpu_count() // 2), 1))
        run_multi_shell(Cmds, JobNames, Nr_proc=nr_proc)


# %% Copy aparc+aseg and wmparc ===============================================
def copy_aparc_wmparc(input_folder, FS_SUBJ_DIR, overwrite=False):
    SUBJIDS = [dd.name for dd in input_folder.glob('*')
               if dd.is_dir() and (dd / 't1.nii.gz').is_file()]
    for subjid in SUBJIDS:
        dst_dir = input_folder / subjid
        subjdir = FS_SUBJ_DIR / subjid
        t1_f = dst_dir / 't1.nii.gz'
        if not t1_f.is_file():
            continue
        
        aseg_f = dst_dir / 'aparc+aseg.nii.gz'
        if not aseg_f.is_file() or overwrite:
            aseg_src_f = subjdir / 'mri' / 'aparc+aseg.mgz'
            if aseg_src_f.is_file():
                cmd = f'mri_convert {aseg_src_f} {aseg_f}'
                subprocess.check_call(shlex.split(cmd))
                
                cmd = f"3dresample -overwrite -master {t1_f} -input {aseg_f}"
                cmd += f" -prefix {aseg_f} -rmode NN"
                subprocess.check_call(shlex.split(cmd))

        wmparc_f = dst_dir / 'wmparc.nii.gz'
        if not wmparc_f.is_file() or overwrite:
            wmparc_src_f = subjdir / 'mri' / 'wmparc.mgz'
            if wmparc_src_f.is_file():
                cmd = f'mri_convert {wmparc_src_f} {wmparc_f}'
                subprocess.check_call(shlex.split(cmd))
                
                cmd = f"3dresample -overwrite -master {t1_f} -input {wmparc_f}"
                cmd += f" -prefix {wmparc_f} -rmode NN"
                subprocess.check_call(shlex.split(cmd))


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog = 'Run FreeSurfer',
        description = 'Create aparc+aseg and wmparc for TractFlow pipeline')
    
    parser.add_argument('input_folder', help='input folder')
    parser.add_argument('-o', '--outdir', help='output directory')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    input_folder = Path(args.input_folder).resolve()
    assert input_folder.is_dir(), f"No directory at {input_folder}"
    FS_SUBJ_DIR = args.outdir
    if FS_SUBJ_DIR is None:
        FS_SUBJ_DIR = input_folder.parent / 'freesurfer'
    overwrite = args.overwrite

    # Run recon-all
    run_reconall(input_folder, FS_SUBJ_DIR)
    
    # Copy aparc+aseg and wmparc to TractFlow input_folder
    copy_aparc_wmparc(input_folder, FS_SUBJ_DIR, overwrite=overwrite)

