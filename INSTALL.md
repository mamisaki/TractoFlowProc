
# INSTALL

## Install miniconda
See https://conda.io/projects/conda/en/latest/user-guide/install/index.html

## Install git
See https://git-scm.com/book/en/v2/Getting-Started-Installing-Git

## Install docker
See https://docs.docker.com/engine/install/

## Install FreeSurfer
https://surfer.nmr.mgh.harvard.edu/fswiki/DownloadAndInstall


## Download scilpy git repositories
```
cd
git clone https://github.com/scilus/scilpy.git
```

## Install scilpy in conda environment
```
conda create -n tractflow python=3.10 pip hdf5=1.12 cython numpy -c anaconda
conda activate tractflow
cd ~/scilpy
pip install -e .
```

## Download nextflow
```
cd ~/bin
wget https://github.com/nextflow-io/nextflow/releases/download/v21.10.6/nextflow && chmod +x nextflow
rm -rf ~/.nextflow
```

## Download TractoFlow and freewater_flow
```
nextflow pull scilus/tractoflow
cd
git clone https://github.com/scilus/freewater_flow
docker pull scilus/scilus:1.4.2
```

## Install TractFlowProc scripts
```
cd
git clone https://github.com/mmisaki/TractFlowProc
```
