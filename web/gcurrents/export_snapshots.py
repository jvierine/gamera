"""Extract unstrided J cell centres for frozen current-line visualizations."""
from pathlib import Path
import argparse
import h5py
import numpy as np
from export_gcurrents import rank_files, load_grid, available_times, stitch, mjd_iso

def select_snapshots(rows):
    """Ten evenly spaced targets, after the two-hour burn-in (nearest output)."""
    usable=[row for row in rows if row[1]>=7200]
    return [(target,min(usable,key=lambda row:abs(row[1]-target)))
            for target in np.linspace(7200,86400,10)]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    files=rank_files(args.source,'hello_earth_24h');p,local,ranks=load_grid(files)
    mask=(p[...,0]>-32)&(p[...,0]<16)&(abs(p[...,1])<24)&(abs(p[...,2])<24)&(np.linalg.norm(p,axis=-1)>2.05)
    rows=available_times(files[0][0])
    with h5py.File(args.output,'w') as h,h5py.File(args.source/'hello_earth_24h.mix.h5') as mix:
        h.attrs['source']=str(args.source);h.attrs['generator']='export_snapshots.py'
        h.attrs['burn_in_s']=7200;h.attrs['snapshot_count']=10
        h.create_dataset('positions',data=p[mask],compression='gzip').attrs['units']='RE; SM Cartesian'
        for index,(target,(step,t,mjd)) in enumerate(select_snapshots(rows)):
            v=stitch(files,local,ranks,step,('Jx','Jy','Jz'))
            g=h.create_group(f'snapshot-{index:02d}');g.attrs['step']=step;g.attrs['utc']=mjd_iso(mjd)
            g.attrs['model_time_s']=t;g.attrs['target_time_s']=target
            g.create_dataset('J',data=np.stack([v[k][mask] for k in ('Jx','Jy','Jz')],axis=-1),compression='gzip').attrs['units']='nA/m2'
            mg=mix[f'Step#{step}'];fac_slice=(slice(None,None,2),slice(None,None,4))
            fac=np.concatenate([-mg['Field-aligned current NORTH'][...][fac_slice].ravel(),mg['Field-aligned current SOUTH'][...][fac_slice].ravel()])
            g.create_dataset('fac',data=fac,compression='gzip').attrs['units']='uA/m2; positive outward'
            print(index,mjd_iso(mjd),len(p[mask]),flush=True)

if __name__=='__main__':main()
