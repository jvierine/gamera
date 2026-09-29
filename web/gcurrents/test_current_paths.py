"""Direction and domain checks for frozen current paths."""
import h5py
import numpy as np
from trace_snapshots import integrate, ROOT

def test_integrator_direction():
    field=lambda p:np.tile([0.,1.,0.],(len(p),1))
    for sign in (-1,1):
        paths,_=integrate(field,np.array([[5.,0.,0.]]),sign,nsteps=20)
        np.testing.assert_allclose(paths[0][-1],[5,sign*2.4,0],atol=1e-12)

def test_circle():
    field=lambda p:np.column_stack([-p[:,1],p[:,0],np.zeros(len(p))])
    paths,_=integrate(field,np.array([[5.,0.,0.]]),1,nsteps=100)
    np.testing.assert_allclose(np.linalg.norm(paths[0],axis=1),5,atol=1e-6)

def test_exported_paths():
    with h5py.File(ROOT/'current_paths.h5') as h:
        for g in h.values():
            errors=[]
            for ds in g.values():
                a=ds[...];assert np.isfinite(a).all()
                p,j=a[:,:3],a[:,3:];assert np.min(np.linalg.norm(p,axis=1))>2.19
                tangent=np.diff(p,axis=0);local=(j[1:]+j[:-1])/2
                cosine=np.sum(tangent*local,axis=1)/(np.linalg.norm(tangent,axis=1)*np.linalg.norm(local,axis=1))
                errors.extend(np.rad2deg(np.arccos(np.clip(cosine,-1,1))))
            # Short steps follow +J, including the reversed backward branch.
            assert np.percentile(errors,95)<3,np.percentile(errors,[50,95,99])
