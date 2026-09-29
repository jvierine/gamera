"""Trace frozen J, not B, from the unstrided GAMERA snapshot cell centres.

Linear tetrahedral interpolation; RK4 in arc length. Curves terminate at the
sample boundary, r=2.2 RE, weak J, or an integration limit. No synthetic
ionospheric connector is appended. Scientific results are retained in HDF5.
"""
from pathlib import Path
import json
import h5py
import numpy as np
from scipy.spatial import Delaunay
from scipy.interpolate import LinearNDInterpolator

ROOT=Path(__file__).resolve().parent

def integrate(field,seeds,sign,step=.12,nsteps=750):
    p=seeds.copy();alive=np.ones(len(p),bool);out=[[q.copy()] for q in p]
    reasons=['length limit']*len(p)
    def unit(q):
        j=field(q);mag=np.linalg.norm(j,axis=1)
        good=np.isfinite(j).all(axis=1)&(mag>.03)&(np.linalg.norm(q,axis=1)>2.2)
        return sign*j/np.maximum(mag[:,None],1e-30),good
    for _ in range(nsteps):
        ids=np.flatnonzero(alive)
        if not len(ids):break
        q=p[ids];k1,g1=unit(q);k2,g2=unit(q+.5*step*k1)
        k3,g3=unit(q+.5*step*k2);k4,g4=unit(q+step*k3)
        nxt=q+step*(k1+2*k2+2*k3+k4)/6
        good=g1&g2&g3&g4&np.isfinite(nxt).all(axis=1)
        for k,i in enumerate(ids):
            if not good[k]:
                alive[i]=False;reasons[i]='inner boundary' if np.linalg.norm(q[k])<2.4 else 'weak current / sampled boundary'
                continue
            if len(out[i])>40 and np.linalg.norm(nxt[k]-seeds[i])<step*.8:
                out[i].append(nxt[k]);alive[i]=False;reasons[i]='returned near seed';continue
            out[i].append(nxt[k]);p[i]=nxt[k]
    return [np.asarray(q) for q in out],reasons

def choose_seeds(p,j):
    r=np.linalg.norm(p,axis=1);mag=np.linalg.norm(j,axis=1)
    latitude=np.rad2deg(np.arcsin(p[:,2]/r))
    radial=np.sum(p*j,axis=1)/r
    rho=np.hypot(p[:,0],p[:,1])
    azimuthal=(p[:,0]*j[:,1]-p[:,1]*j[:,0])/np.maximum(rho,1e-12)
    flank=abs(p[:,1])>.45*rho
    inner=(r>2.4)&(r<3.3)&flank&(abs(radial)>.35*mag)
    # Operational seed classes, not a decomposition of the numerical J.
    # R1: outward dusk / inward dawn. R2: the opposite sense. Latitude
    # windows are at the MHD shell, not ionospheric invariant latitude.
    masks={'dayside':(p[:,0]>6)&(p[:,0]<13)&(r<17),
           'tail':(p[:,0]<-7)&(p[:,0]>-29)&(abs(p[:,2])<2)&(abs(p[:,1])<15),
           'ring':(r>3)&(r<8)&(abs(p[:,2])<1.3)&(azimuthal<-.35*mag),
           'r1':inner&(abs(latitude)>45)&(abs(latitude)<78)&(radial*p[:,1]>0),
           'r2':inner&(abs(latitude)>20)&(abs(latitude)<65)&(radial*p[:,1]<0)}
    limits={'dayside':20,'tail':40,'ring':32,'r1':32,'r2':32}
    spacing={'dayside':2.3,'tail':1.8,'ring':.75,'r1':.38,'r2':.38}
    seeds=[];groups=[]
    for group,mask in masks.items():
        candidates=np.flatnonzero(mask);candidates=candidates[np.argsort(mag[candidates])[::-1]]
        # Interleave spatial sectors so the first few visible paths already
        # cover both hemispheres/flanks, instead of one strongest-current patch.
        if group=='tail':sector=np.floor((p[:,0]+29)/6).astype(int)*2+(p[:,1]>0)
        elif group=='ring':sector=np.floor((np.arctan2(p[:,1],p[:,0])+np.pi)*4/np.pi).astype(int)
        else:sector=(p[:,1]>0).astype(int)*2+(p[:,2]>0)
        queues=[list(candidates[sector[candidates]==s]) for s in np.unique(sector[candidates])]
        chosen=[]
        while any(queues) and len(chosen)<limits[group]:
            for queue in queues:
                while queue:
                    idx=queue.pop(0)
                    if all(np.linalg.norm(p[idx]-p[k])>spacing[group] for k in chosen):
                        chosen.append(idx);break
                if len(chosen)==limits[group]:break
        seeds.extend(p[chosen]);groups.extend([group]*len(chosen))
    return np.asarray(seeds),groups

def main():
    with h5py.File(ROOT/'snapshots.h5','r') as source,h5py.File(ROOT/'current_paths.h5','w') as output:
        positions=source['positions'][...].astype(float)
        print('Triangulating',len(positions),'unstrided cells',flush=True)
        tri=Delaunay(positions)
        output.attrs['method']='RK4 ds=0.12 RE; linear Delaunay interpolation of unstrided GAMERA J'
        output.attrs['generator']='trace_snapshots.py';output.attrs['coordinates']='SM Cartesian; RE; J nA/m2'
        snapshots=[]
        for hours in (6,12,18):
            g=source[str(hours)];j=g['J'][...];field=LinearNDInterpolator(tri,j)
            seeds,groups=choose_seeds(positions,j)
            f,fr=integrate(field,seeds,1);b,br=integrate(field,seeds,-1)
            record={'hours':hours,'utc':g.attrs['utc'],'frame':hours*4,'paths':[]}
            og=output.create_group(str(hours));og.attrs['utc']=g.attrs['utc']
            for i,(forward,backward,group) in enumerate(zip(f,b,groups)):
                p=np.concatenate([backward[:0:-1],forward]);values=field(p)
                if len(p)<30:continue
                length=np.linalg.norm(np.diff(p,axis=0),axis=1).sum()
                ds=og.create_dataset(str(i),data=np.column_stack([p,values]),compression='gzip')
                ds.attrs['seed_group']=group;ds.attrs['start']=br[i];ds.attrs['end']=fr[i]
                ds.attrs['seed_position']=seeds[i]
                record['paths'].append(dict(id=i,group=group,points=np.round(p,4).tolist(),
                    seed=np.round(seeds[i],5).tolist(),
                    magnitude=np.round(np.linalg.norm(values,axis=1),3).tolist(),
                    length=round(float(length),2),start=br[i],end=fr[i]))
            filename=f'paths-{hours:02d}.json'
            (ROOT/filename).write_text(json.dumps(record,separators=(',',':')))
            snapshots.append(dict(hours=hours,utc=record['utc'],frame=hours*4,file=filename,count=len(record['paths'])))
            print(hours,len(record['paths']),'paths',flush=True)
        (ROOT/'snapshots.json').write_text(json.dumps(snapshots))

if __name__=='__main__':main()
