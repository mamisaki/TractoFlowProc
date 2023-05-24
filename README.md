# README
See the [INSTALL](INSTALL.md) file to set up the environment. These instructions assume that the TractFlowProc scripts are stored in ~/TractFlowProc and the workspace is ~/TractFlow_workspace.

## 1. Prepare data files
Create an input data folder (e.g. ~/TractFlow_workspace/input).  
Place the data file for each subject (e.g. S1, S2, ...) into the input folder.  
The data structure is as follows:  
input  
&nbsp;&nbsp;├── S1  
&nbsp;&nbsp;│ ├── dwi.nii.gz  
&nbsp;&nbsp;│ ├── bval  
&nbsp;&nbsp;│ ├── bvec  
&nbsp;&nbsp;│ ├── rev_b0.nii.gz (optional)  
&nbsp;&nbsp;│ ├── aparc+aseg.nii.gz (optional)  
&nbsp;&nbsp;│ ├── wmparc.nii.gz (optional)  
&nbsp;&nbsp;│ └── t1.nii.gz  
&nbsp;&nbsp;└── S2  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── dwi.nii.gz  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── bval  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── bvec  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── rev_b0.nii.gz (optional)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── aparc+aseg.nii.gz (optional)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── wmparc.nii.gz (optional)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── t1.nii.gz  

dwi.nii.gz: DWI image file.  
bval, bvec: b-value and b-vector files. b-vector must be of unit length.  
t1.nii.gz: T1 anatomical image file.  
rev_b0.nii.gz (optional): Reverse phase encoding of b0 DWI images.  
aparc+aseg.nii.gz (optional): FreeSurfer aparc+aseg image file.  
wmparc.nii.gz (optional): FreeSurfer wmparc image file.  

## 2. Run FreeSurfer (optional)
**You can skip this step.** Only if the T1 image contrast is not good enough to segment tissue and you need to use Atlas Based Segmentation (ABS) in Tractflow, you should perform this process.  

The fiber tracking process uses the white matter (WM), gray matter (GM), and cerebrospinal fluid (CSF) maps to compute the tracking maps and the seeding mask. These masks are extracted by default with 'fast' in FSL for t1.nii.gz, but you can also use a FreeSurfer segmentation, i.e. aparc+aseg and wmparc, with the --ABS option in tractflow.  

The script run_FreeSurfer.py processes t1.nii.gz in the input folder to create aparc+aseg.nii.gz and wmparc.nii.gz.
```
cd ~/TractFlowProc
nohup ./run_FreeSurfer.py ~/TractFlow_workspace/input > nohup_FS.out &
```
The process will take a very long time (almost a day for one subject, depending on the CPU). Multiple subjects are processed in parallel, and the number of simultaneous processes is '(number of CPU cores)//2'.  
The files processed by FreeSurfer are stored in the folder ~/TractFlow_workspace/freesurfer.  
Each subject's aparc+aseg.nii.gz and wmparc.nii.gz are created in the input folder.  

## 3. TractoFlow pipeline
https://tractoflow-documentation.readthedocs.io/en/latest/pipeline/steps.html
```
cd ~/TractFlowProc
nohup ./run_TractFlow.py ~/TractFlow_workspace/input --with_docker --fully_reproducible > nohup_tf.out &
```
The command returns immediately, and the process runs in the background.  
The process takes a very long time: > 10h for one subject. Multiple subjects are processed in parallel.  

* Add '--ABS' option to run TractoFlow-ABS (See [2](#2-run-freesurfer-optional)).  

## 4. freewater_flow pipeline
https://github.com/scilus/freewater_flow
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_FreewaterFlow.py ~/TractFlow_workspace/results > nohup_fwf.out &
```
The 'results' folder of run_TractFlow.py should be passed as an argument. The input files for freewater_flow are created in 'fwflow_input' in '\~/TractFlow_workspace' (parent directory of the results folder).  
A working directory, '\~/TractFlow_workspace/fwflow_work', is also created.

The command returns immediately, and the process runs in the background.  
The process takes a very long time: > 10h for one subject. Multiple subjects are processed in parallel.  

## 5. Result files
Result files are stored in the ~/TractFlow_workspace/results/*subject* folders.  

- DTI_Metrics/  
    The axial diffusivity (ad), fractional anisotropy (fa), geodesic anisotropy (ga) [[Batchelor et al., 2005](https://onlinelibrary.wiley.com/doi/10.1002/mrm.20334)], mean diffusivity (md), radial diffusivity (rd), tensor, tensor norm [[Kindlmann et al., 2007](https://ieeexplore.ieee.org/abstract/document/4359059)], tensor eigenvalues, tensor eigenvectors, tensor mode, and color-FA are created.

- FODF_Metrics/  
    The fiber orientation distribution function (fODF) metrics computed are the total and maximum Apparent Fiber Density (AFD) [[Raffelt et al., 2012](https://www.sciencedirect.com/science/article/pii/S1053811911012092)], the Number of Fiber Orientation (NuFO) [[Dell’Acqua et al., 2013](https://onlinelibrary.wiley.com/doi/epdf/10.1002/hbm.22080)] and principal fODFs orientations (up to 5 per voxel).

- FW_Corrected_Metrics/  
    DTI metrics files with freewater correction are created in this folder.    
    
- Local_Tracking/  
    *subject*__local_tracking_prob_wm_seeding_wm_mask_seed_0.trk  

## 6. Standardize DTI and fODF metrics
The run_warp2template.py script normalizes the DTI and fDOF metric files to MNI152 template space.  
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_warp2template.py ~/TractFlow_workspace/results > nohup_wrp.out &
```

The result files are saved in the 'Standardize_*' folders in the results folder.

## 7. FDT processing
Running a probabilistic fiber tracking analysis with [FSL FDT tools](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FDT/UserGuide), including [BEDPOSTX](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FDT/UserGuide#BEDPOSTX), [XTRACT](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/XTRACT), and [PROBTRACKX](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FDT/UserGuide#PROBTRACKX_-_probabilistic_tracking_with_crossing_fibres). 

### BEDPOSTX
Run commnd below, 
if GPU can be used,
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_bedpostX.py --gpu ~/TractFlow_workspace/results > nohup_bpx.out &
```

or if no GPU is available,
```
nohup ./run_bedpostX.py ~/TractFlow_workspace/results > nohup_bpx.out &
```
The results are stored in '~/TractFlow_workspace/FDT/\*.bedpostX' foldres.  

### XTRACT
[XTRACT](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/XTRACT)(cross-species tractography) can be used to automatically extract a set of carefully dissected tracts in human (neonates and adults) and macaques. It can also be used to define one's own tractography protocols where all the user needs to do is to define a set of masks in standard space (e.g. MNI152).  
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_XTRACT.py --gpu ~/TractFlow_workspace/FDT > nohup_xtract.out &
```

### PROBTRACKX
[PROBTRACKX](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FDT/UserGuide#PROBTRACKX_-_probabilistic_tracking_with_crossing_fibres) produces sample streamlines, by starting from some seed and then iterate between (1) drawing an orientation from the voxel-wise bedpostX distributions, (2) taking a step in this direction, and (3) checking for any termination criteria. These sample streamlines can then be used to build up a histogram of how many streamlines visited each voxel or the number of streamlines connecting specific brain regions. This streamline distribution can be thought of as the posterior distribution on the streamline location or the connectivity distribution.  

