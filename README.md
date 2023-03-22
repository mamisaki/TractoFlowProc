# README
See the INSTALL file to set up the tools. It is assumed that the TractFlowProc scripts are stored in ~/TractFlowProc and the workspace is ~/TractFlow_workspace.

## 1. Prepare data files
Create an input data folder (e.g. ~/TractFlow_workspace/input_data).
Place the data file for each subject (e.g. S1, S2, ...) into the
input_data folder.
The data structure is as follows
input_data  
&nbsp;&nbsp;├── S1  
&nbsp;&nbsp;│ ├── dwi.nii.gz  
&nbsp;&nbsp;│ ├── bval  
&nbsp;&nbsp;│ ├── bvec  
&nbsp;&nbsp;│ ├── rev_b0.nii.gz (optional)  
&nbsp;&nbsp;│ ├── aparc+aseg.nii.gz (optional)  
&nbsp;&nbsp;│ ├── wmparc.nii.gz (optional)  
&nbsp;&nbsp;│ └── t1.nii.gz  
        └── S2  
          ├── dwi.nii.gz  
          ├── bval  
          ├── bvec  
          ├── rev_b0.nii.gz (optional)  
          ├── aparc+aseg.nii.gz (optional)  
          ├── wmparc.nii.gz (optional)  
          └── t1.nii.gz  

dwi.nii.gz : DWI image file  
bval, bvec : b-value and b-vector files. b-vector must be of unit length.  
t1.nii.gz : T1 anatomical image file.  
rev_b0.nii.gz (optional) : Reverse phase encoding of b0 DWI images.
aparc+aseg.nii.gz (optional) : FreeSurfer aparc+aseg image file.
wmparc.nii.gz (optional) : FreeSurfer wmparc image file.

## 2. Run FreeSurfer (optional)
If you are using TractoFlow-ABS (Atlas Based Segmentation), you will need aparc+aseg.nii.gz and wmparc.nii.gz, which are created by FreeSurfer and resampled to the same space as t1.nii.gz. The script run_FreeSurfer.py processes t1.nii.gz in the input_data folder to create aparc+aseg.nii.gz and wmparc.nii.gz.
```
cd ~/TractFlowProc
nohup ./run_FreeSurfer.py ~/TractFlow_workspace/input_data > nohup_FS.out &
```
The process will take a very long time (half a day for one subject). Multiple subjects are processed in parallel and the number of simultaneous processes is (number of CPU cores)//2.  
The files processed by Freesurfer are stored in the folder ~/TractFlow_workspace/freesurfer (parent folder of input_data).  
Each subject's aparc+aseg.nii.gz and wmparc.nii.gz are created in the input_data folder.  

TractoFlow-ABS must be used for pathological data.  
You can skip this process if you are not using TractoFlow-ABS.  

## 3. Run the TractoFlow pipeline
https://tractoflow-documentation.readthedocs.io/en/latest/pipeline/steps.html
```
cd ~/TractFlowProc
nohup ./run_TractFlow.py ~/TractFlow_workspace/input_data --with_docker --fully_reproducible > nohup_tf.out &
```
The command will return immediately, but the process will run in the background.
The process will take a very long time (a day or more) to complete.  

* Add '--ABS' option to run TractoFlow-ABS (See 2.).  

* If the workspace is on a network share, the trac_flow pipeline will fail. Then add the `-copy_local' option to the run_FreeSurfer command, for example,
```
cd ~/TractFlowProc
nohup ./run_TractFlow.py ~/TractFlow_workspace/input_data --with_docker --fully_reproducible \
    --copy_local --workspace ~/TractFlowWork_local > nohup_tf.out &
```
In this example, the --copy_local option causes the input_data folder to be copied to ~/TractFlowWork/, which is specified by the --workspace option, and when the process is finished, the results and work folders are copied back to the workspace (parent directory of input_data).

~/TractFlowWork_local can be removed after the process.

## 4. Run the freewater_flow pipeline
https://github.com/scilus/freewater_flow
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_FreewaterFlow.py ~/TractFlow_workspace/results > nohup_fwf.out &
```
The 'results' folder of the run_TractFlow.py should be given as an argument. The input files for freewater_flow are copied to 'fwflow_input' in ~/TractFlow_workspace (parent directory of the results folder).

* The '--copy_local' option allows you to work in the local workspace specified by the '--workplace' option. The results files will be copied to the ~/TractFlow_workspace/results folder.
```
# optional
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_FreewaterFlow.py ~/TractFlow_workspace/results \
    --copy_local --workspace ~/FWFlowWork_local
```
~/FWFlowWork_local can be removed after the process.

