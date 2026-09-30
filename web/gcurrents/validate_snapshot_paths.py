"""Trim invalid terminal samples from legacy traces, then strictly encode JSON.

The current integrator checks accepted endpoints directly. This migration
validates products generated before that check without retracing valid curves.
Interior invalid samples are an error, never silently joined across a gap.
"""
import argparse
import json
from pathlib import Path
import h5py
import numpy as np

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    args=parser.parse_args();removed=0
    manifest=json.loads((args.directory/'snapshots.json').read_text())
    with h5py.File(args.directory/'current_paths.h5','r+') as h:
        for entry in manifest:
            filename=args.directory/entry['file'];record=json.loads(filename.read_text())
            group=h[filename.stem.removeprefix('paths-')]
            for path in record['paths']:
                name=str(path['id']);ds=group[name];a=ds[...]
                valid=np.isfinite(a).all(axis=1)&(np.linalg.norm(a[:,:3],axis=1)>2.2)
                indices=np.flatnonzero(valid)
                if len(indices)<30 or not np.all(np.diff(indices)==1):
                    raise ValueError(f'Invalid interior or short path: {filename}:{name}')
                start,end=indices[0],indices[-1]+1
                if start or end<len(a):
                    attrs=dict(ds.attrs);removed+=len(a)-(end-start)
                    if start:attrs['start']='sampled boundary'
                    if end<len(a):attrs['end']='sampled boundary'
                    a=a[start:end];del group[name]
                    ds=group.create_dataset(name,data=a,compression='gzip')
                    for key,value in attrs.items():ds.attrs[key]=value
                path['points']=np.round(a[:,:3],4).tolist()
                path['magnitude']=np.round(np.linalg.norm(a[:,3:],axis=1),3).tolist()
                path['length']=round(float(np.linalg.norm(np.diff(a[:,:3],axis=0),axis=1).sum()),2)
                path['start']=ds.attrs['start'];path['end']=ds.attrs['end']
            filename.write_text(json.dumps(record,separators=(',',':'),allow_nan=False))
        h.attrs['endpoint_validation']='validate_snapshot_paths.py: finite J and r > 2.2 RE; terminal samples only'
    print(f'Removed {removed} invalid terminal samples; all JSON strictly finite.')

if __name__=='__main__':main()
