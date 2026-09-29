"""Extract unstrided J cell centres for frozen current-line visualizations."""
from pathlib import Path
import argparse
import h5py
import numpy as np
from export_gcurrents import rank_files, load_grid, available_times, stitch, mjd_iso

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    files=rank_files(args.source,'hello_earth_24h');p,local,ranks=load_grid(files)
    mask=(p[...,0]>-32)&(p[...,0]<16)&(abs(p[...,1])<24)&(abs(p[...,2])<24)&(np.linalg.norm(p,axis=-1)>2.05)
    rows=available_times(files[0][0])
    with h5py.File(args.output,'w') as h:
        h.attrs['source']=str(args.source);h.attrs['generator']='export_snapshots.py'
        h.create_dataset('positions',data=p[mask],compression='gzip').attrs['units']='RE; SM Cartesian'
        for hours in (6,12,18):
            step,t,mjd=min(rows,key=lambda r:abs(r[1]-hours*3600))
            v=stitch(files,local,ranks,step,('Jx','Jy','Jz'))
            g=h.create_group(str(hours));g.attrs['step']=step;g.attrs['utc']=mjd_iso(mjd)
            g.create_dataset('J',data=np.stack([v[k][mask] for k in ('Jx','Jy','Jz')],axis=-1),compression='gzip').attrs['units']='nA/m2'
            print(hours,len(p[mask]),flush=True)

if __name__=='__main__':main()
