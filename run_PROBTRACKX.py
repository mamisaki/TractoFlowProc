#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" run PROBTRACKX
https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FDT/UserGuide#PROBTRACKX_-_probabilistic_tracking_with_crossing_fibres
"""

# %% import ===================================================================
import argparse
from pathlib import Path
import shlex
import subprocess
import sys
from socket import gethostname
import time

from tqdm import tqdm
import numpy as np
import nibabel as nib
import pandas as pd

if '__file__' not in locals():
    __file__ = 'run_PROBTRACKX.py'

script_dir = Path(__file__).resolve().parent
MNI_f = script_dir / 'MNI152_T1_1mm_brain.nii.gz'


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog='run_PROBTRACKX',
        description='Run FSL PROBTRACKX to make a map of probabilistic' +
        ' tractgrpahy')

    parser.add_argument('FDT_folder', help='FDT results folder')
    parser.add_argument('--gpu', action='store_true', help='Use GPU')
    parser.add_argument('--seed_template',
                        help='Seed mask in the template (MNI152) space.' +
                        'Multiple seeds can be implemented in one file with' +
                        'different values')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    FDT_folder = Path(args.FDT_folder).resolve()
    assert FDT_folder.is_dir(), f"No directory at {FDT_folder}"
    gpu = args.gpu
    seed_template = args.seed_template
    overwrite = args.overwrite

    '''DEBUG
    FDT_folder = Path.home() / \
        'MRI/TractFlow_workspace/DTI_AdolescentData/FDT'
    gpu = True
    seed_template = Path.home() / \
        'MRI/TractFlow_workspace/DTI_AdolescentData/SeedROI.nii.gz'
    overwrite = False
    '''

    # --- Set ROI names -------------------------------------------------------
    roi_name_f = seed_template.parent / \
        seed_template.name.replace('.nii.gz', '.csv')
    if roi_name_f.is_file():
        ROI_names = pd.read_csv(roi_name_f, index_col=0).squeeze()
    else:
        seed_V = nib.load(seed_template).get_fdata().astype(int)
        ROI_names = pd.Series(
            {ri: f"ROI_{ri}" for ri in np.unique(seed_V) if ri != 0}
        )

    # --- Get input data ------------------------------------------------------
    Subj_dirs = [sub_dir for sub_dir in FDT_folder.glob('*.bedpostX')
                 if sub_dir.is_dir()]

    # Check if the job is done
    done_subj = []
    for sub_dir in Subj_dirs:
        sub = sub_dir.name.replace('.bedpostX', '')
        res_dir = FDT_folder / f"{sub}.probtackx"
        DONE = True
        for roi in ROI_names.values:
            last_f = res_dir / f'{roi}_fdt_paths_prob_standard.nii.gz'
            if not last_f.is_file():
                DONE = False
                break
        if DONE:
            done_subj.append(sub_dir)
    Subj_dirs = np.setdiff1d(Subj_dirs, done_subj)

    # --- Loop for subjects ---------------------------------------------------
    for sub_d in tqdm(Subj_dirs, desc="Running probtackx"):
        sub = sub_d.name.replace('.bedpostX', '')
        IsRun = FDT_folder / f"IsRun_probtackx_{sub}"
        if IsRun.is_file():
            continue

        with open(IsRun, 'w', encoding='utf-8') as fd:
            print(gethostname(), file=fd)
            print(time.ctime(), file=fd)

        res_dir = FDT_folder / f"{sub}.probtackx"
        if not res_dir.is_dir():
            res_dir.mkdir()

        # Seed map in individual diffusion space
        seed_map_f = res_dir / \
            seed_template.name.replace('.nii.gz', '_diff.nii.gz')
        if not seed_map_f.is_file() or overwrite:
            t1_ref = sub_d.parent / sub / 'T1_brain.nii.gz'
            wrp_f = sub_d / 'xfms' / 'standard2diff.nii.gz'
            cmd = f"applywarp --ref={t1_ref} --in={seed_template}"
            cmd += f" --warp={wrp_f} --interp=nn --out={seed_map_f}"
            subprocess.check_call(shlex.split(cmd))

        seed_img = nib.load(seed_map_f)
        seed_V = seed_img.get_fdata().astype(int)

        # Run PROBTRACKX
        if gpu:
            cmd0 = 'probtrackx2_gpu'
        else:
            cmd0 = 'probtrackx2'

        # Loop for ROIs
        wrp2std_f = sub_d / 'xfms' / 'diff2standard.nii.gz'

        for seed_idx, roi in ROI_names.items():
            out_f = res_dir / f'{roi}_fdt_paths_prob_standard.nii.gz'
            if out_f.is_file() and not overwrite:
                continue

            # Create seed mask for the roi
            seed_f = res_dir / f"{roi}_ROI.nii.gz"
            roi_V = np.zeros_like(seed_V, dtype=np.int8)
            roi_V[seed_V == seed_idx] = 1
            simg = nib.Nifti1Image(roi_V, seed_img.affine)
            nib.save(simg, seed_f)

            # probtrackx
            mask_f = sub_d.parent / sub / 'nodif_brain_mask'
            cmd = cmd0 + f" -s {sub_d}/merged"
            cmd += f" -m {mask_f}"
            cmd += f" -x {seed_f} --opd -P 5000 -S 2000"
            cmd += f" -o {roi}_fdt_paths --dir={res_dir} --forcedir"
            try:
                subprocess.check_output(shlex.split(cmd))
                fdt_path_f = res_dir / f'{roi}_fdt_paths.nii.gz'
                assert fdt_path_f.is_file()
            except Exception as e:
                sys.stderr.write(f"Faild: {cmd}\n")
                sys.stderr.write(f"{e}\n")
                continue

            # Make fdt_paths to probability
            waytotal = float(np.loadtxt(res_dir / 'waytotal'))
            prob_fdt_path_f = res_dir / f'{roi}_fdt_paths_prob.nii.gz'
            cmd = f"fslmaths {fdt_path_f} -div {waytotal} {prob_fdt_path_f}"
            subprocess.check_call(shlex.split(cmd))

            # Warp fdt_paths_prob.nii.gz to standard space
            out_f = res_dir / f'{roi}_fdt_paths_prob_standard.nii.gz'
            cmd = f"applywarp --ref={MNI_f} --in={prob_fdt_path_f}"
            cmd += f" --warp={wrp2std_f} --out={out_f}"
            subprocess.check_call(shlex.split(cmd))

        if IsRun.is_file():
            IsRun.unlink()
