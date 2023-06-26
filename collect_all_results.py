#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# %% import ===================================================================
import argparse
from pathlib import Path
import shutil


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog='collect_all_results',
        description='Collect all result files of TractFlowProc')

    parser.add_argument('workDir', help='worked directory')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    workDir = Path(args.workDir)
    overwrite = args.overwrite

    '''
    workDir = Path.home() / 'MRI/TractFlow_workspace/DTI_AdolescentData'
    overwrite = False
    '''

    # Get subjects
    res_dir = workDir / 'results'
    Subs = [sub_dir.name for sub_dir in res_dir.glob('*')
            if sub_dir.is_dir() and
            sub_dir.name not in ('Compute_Kernel', 'Readme')]

    # Copy result files
    OUT_ROOT = workDir / 'All_results'
    if not OUT_ROOT.is_dir():
        OUT_ROOT.mkdir()

    for sub in Subs:
        sub_dir = OUT_ROOT / sub
        if not sub_dir.is_dir():
            sub_dir.mkdir()

        # DTI metrics
        src_dir = workDir / 'results' / sub / 'Standardize_DTI_Metrics'
        for src_f in src_dir.glob('*.nii.gz'):
            dst_f = sub_dir / src_f.name
            if not dst_f.is_file() or overwrite:
                shutil.copy(src_f, dst_f)

        # FODF Metrics
        src_dir = workDir / 'results' / sub / 'Standardize_FODF_Metrics'
        for src_f in src_dir.glob('*.nii.gz'):
            dst_f = sub_dir / src_f.name
            if not dst_f.is_file() or overwrite:
                shutil.copy(src_f, dst_f)

        # FW-corrected DTI metrics
        src_dir = workDir / 'results' / sub / \
            'Standardize_FW_Corrected_Metrics'
        for src_f in src_dir.glob('*.nii.gz'):
            dst_f = sub_dir / src_f.name
            if not dst_f.is_file() or overwrite:
                shutil.copy(src_f, dst_f)

        # FDT XTRACT stats
        src_f = workDir / 'FDT' / f"{sub}.xtract" / 'stats.csv'
        dst_f = sub_dir / f"{sub}_FDT_xtract_stats.csv"
        if src_f.is_file() and not dst_f.is_file() or overwrite:
            shutil.copy(src_f, dst_f)

        # FDT probtackx
        src_dir = workDir / 'FDT' / f"{sub}.probtackx"
        for src_f in src_dir.glob('*_prob_standard.nii.gz'):
            dst_f = sub_dir / f"{sub}_{src_f.name}"
            if not dst_f.is_file() or overwrite:
                shutil.copy(src_f, dst_f)
