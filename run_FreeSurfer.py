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

        IsRun = input_folder / f"IsRunning.{subjid}"
        IsRun_FS = dst_root / 'scripts' / 'IsRunning.lh+rh'
        if IsRun.is_file() or IsRun_FS.is_file():
            print("IsRun file exists."
                  f" Recon-all for {subjid} seems to be running.\n"
                  f"Otherwise, remove {IsRun} file.")
            continue

        # Make command
        cmd = ''

        # Check if the job is running (on anohter node).
        cmd += f"if test -f {IsRun}; then exit; fi; "
        # Place IsRun to block other process
        cmd += f"hostname > {IsRun} && date >> {IsRun} && "

        # recon-all
        t1_src_f = input_folder / subjid / 't1.nii.gz'
        t2_src_f = input_folder / subjid / 't2.nii.gz'

        cmd += f"export SUBJECTS_DIR={FS_SUBJ_DIR}; recon-all -subjid {subjid}"
        orig_f = dst_root / 'mri' / 'orig' / '001.mgz'
        if not orig_f.is_file():
            cmd += f" -i {t1_src_f}"

        if t2_src_f.is_file():
            t2_f = dst_root / 'mri' / 'orig' / 'T2raw.mgz'
            if not t2_f.is_file():
                cmd += f" -T2 {t2_src_f}"
            cmd += " -T2pial"

        cmd += " -all -openmp 4;"
        cmd += f"if test -f {IsRun}; then rm {IsRun}; fi"

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
        prog='run_FreeSurfer.py',
        description='Create aparc+aseg and wmparc for TractFlow pipeline')

    parser.add_argument('input_folder', help='input folder')
    parser.add_argument('--copy_local', action='store_true',
                        help='Copy local working place')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    input_folder = Path(args.input_folder).resolve()
    assert input_folder.is_dir(), f"No directory at {input_folder}"

    FS_SUBJ_DIR = input_folder.parent / 'freesurfer'
    copy_local = args.copy_local
    if copy_local and args.workplace is not None:
        subjdir = {Path.home()} / 'freesurfer'
    else:
        subjdir = FS_SUBJ_DIR
    overwrite = args.overwrite

    # Run recon-all
    run_reconall(input_folder, subjdir)

    # Copy aparc+aseg and wmparc to TractFlow input_folder
    copy_aparc_wmparc(input_folder, subjdir, overwrite=overwrite)

    # Sync to the original workpalce
    if copy_local and subjdir != FS_SUBJ_DIR:
        cmd = f"rsync -auvz {subjdir}/ {FS_SUBJ_DIR}/"
        subprocess.check_call(shlex.split(cmd))
