#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# %% import ===================================================================
import argparse
from pathlib import Path
import shlex
import subprocess

from tqdm import tqdm
from ants_run import ants_registration, ants_warp_resample

if '__file__' not in locals():
    __file__ = 'run_Warp2MNI.py'

script_dir = Path(__file__).resolve().parent
MNI_f = script_dir / 'MNI152_T1_1mm_brain.nii.gz'

metric_files = {'DTI_Metrics': ('ad', 'fa', 'ga', 'md', 'rd'),
                'FODF_Metrics': ('afd_max', 'afd_sum', 'afd_total', 'nufo'),
                'FW_Corrected_Metrics':
                    ('fw_corr_ad', 'fw_corr_fa', 'fw_corr_ga', 'fw_corr_md',
                     'fw_corr_rd')
                }


# %% warp_MNI_T1 ==============================================================
def warp_MNI_T1(regt1_fs, template=MNI_f, overwrite=False):

    for t1_f in tqdm(regt1_fs, desc='ANTs registration'):
        work_dir = t1_f.parent.parent / 'Standardize_T1'
        if not work_dir.is_dir():
            work_dir.mkdir()

        aff_f = work_dir / 'template2orig_0GenericAffine.mat'
        invwrp_f = work_dir / 'template2orig_1InverseWarp.nii.gz'
        if aff_f.is_file() and invwrp_f.is_file() and not overwrite:
            continue

        # Run ANTs registration: template_f -> t1
        _ = ants_registration(t1_f, template, f"{work_dir}/template2orig_",
                              verbose=False)


# %% apply_warp ===============================================================
def apply_warp(regt1_fs, template=MNI_f, metric_files=metric_files,
               overwrite=False):

    for t1_f in tqdm(regt1_fs, desc='Apply warping'):
        work_root = t1_f.parent.parent

        # Check if warping paramter files exist
        Standardize_T1_dir = work_root / 'Standardize_T1'
        aff_f = Standardize_T1_dir / 'template2orig_0GenericAffine.mat'
        invwrp_f = Standardize_T1_dir / 'template2orig_1InverseWarp.nii.gz'
        if not aff_f.is_file() or not invwrp_f.is_file():
            continue

        # Apply warp
        for metric_dir, metric in metric_files.items():
            src_dir = work_root / metric_dir
            if not src_dir.is_dir():
                continue

            dst_dir = work_root / f"Standardize_{metric_dir}"
            if not dst_dir.is_dir():
                dst_dir.mkdir()

            for metric in metric:
                src_f = src_dir / f"{work_root.name}__{metric}.nii.gz"
                if not src_f.is_file():
                    print(f"Not found {src_f}.")
                    continue

                warped_f = dst_dir / \
                    src_f.name.replace('.nii.gz', '_standard.nii.gz')
                if warped_f.is_file() and not overwrite:
                    continue

                # Apply warp with resample in fix_f space
                warp_params = [str(aff_f), str(invwrp_f)]
                whichtoinvert = [True, False]
                out_f = warped_f
                ants_warp_resample(
                    template, src_f, warped_f, warp_params,
                    interpolator='linear', imagetype=0,
                    whichtoinvert=whichtoinvert, verbose=False)

                try:
                    cmd = f"3drefit -view tlrc -space MNI {out_f}"
                    subprocess.check_call(shlex.split(cmd),
                                          stderr=subprocess.PIPE)
                except Exception:
                    pass


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog='run_Warp2MNI',
        description='warp DTI and FODF metrics into MNI space')

    parser.add_argument('results_folder', help='TractFlow results folder')
    parser.add_argument('--template', default=MNI_f,
                        help='Template brain file')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    results_folder = Path(args.results_folder).resolve()
    assert results_folder.is_dir(), f"No directory at {results_folder}"
    template = args.template
    overwrite = args.overwrite

    '''DEBUG
    results_folder = Path.home() / \
        'MRI/TractFlow_workspace/DTI_AdolescentData/results'
    template = MNI_f
    overwrite = False
    '''

    # --- Get input data dirs -------------------------------------------------
    sub_dirs = [sub_dir for sub_dir in results_folder.glob('*')
                if sub_dir.is_dir() and
                sub_dir.name not in ('Readme', 'Compute_Kernel')]

    # Collect T1 registered to DWI
    regt1_fs = []
    for sub_dir in sub_dirs:
        sub = sub_dir.name
        regT1_f = results_folder / sub / 'Register_T1' / \
            f"{sub}__t1_warped.nii.gz"
        if regT1_f.is_file():
            regt1_fs.append(regT1_f)

    # Calculate warping parameters
    warp_MNI_T1(regt1_fs, template=template, overwrite=overwrite)

    # Apply warp to DTI and FODF metrics files to standardize
    apply_warp(regt1_fs, template=template, metric_files=metric_files,
               overwrite=overwrite)
