"""Direction and domain checks for frozen current paths."""
import h5py
import json
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

def test_legacy_endpoint_validation(tmp_path,monkeypatch):
    from validate_snapshot_paths import main
    key='snapshot-00';filename=f'paths-{key}.json'
    (tmp_path/'snapshots.json').write_text(json.dumps([{'file':filename}]))
    (tmp_path/filename).write_text(json.dumps({'paths':[{'id':0}]}))
    data=np.tile([5.,0.,0.,0.,1.,0.],(34,1));data[[0,-1],3:]=np.nan
    with h5py.File(tmp_path/'current_paths.h5','w') as h:
        ds=h.create_group(key).create_dataset('0',data=data)
        ds.attrs['start']=ds.attrs['end']='length limit'
    monkeypatch.setattr('sys.argv',['validate_snapshot_paths.py',str(tmp_path)])
    main()
    with h5py.File(tmp_path/'current_paths.h5') as h:
        assert h[key]['0'].shape==(32,6)
        assert np.isfinite(h[key]['0'][...]).all()
    record=json.loads((tmp_path/filename).read_text())
    assert len(record['paths'][0]['points'])==32
    assert record['paths'][0]['start']=='sampled boundary'

def test_legacy_interior_gap_rejected(tmp_path,monkeypatch):
    import pytest
    from validate_snapshot_paths import main
    filename='paths-snapshot-00.json'
    (tmp_path/'snapshots.json').write_text(json.dumps([{'file':filename}]))
    (tmp_path/filename).write_text(json.dumps({'paths':[{'id':0}]}))
    data=np.tile([5.,0.,0.,0.,1.,0.],(34,1));data[17,3:]=np.nan
    with h5py.File(tmp_path/'current_paths.h5','w') as h:
        h.create_group('snapshot-00').create_dataset('0',data=data)
    monkeypatch.setattr('sys.argv',['validate_snapshot_paths.py',str(tmp_path)])
    with pytest.raises(ValueError,match='Invalid interior'):
        main()

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

def test_ten_snapshot_times_and_fac_alignment():
    manifest=json.loads((ROOT/'snapshots.json').read_text())
    assert len(manifest)==10
    targets=np.asarray([p['target_time_s'] for p in manifest])
    np.testing.assert_allclose(targets,np.linspace(7200,86400,10))
    actual=np.asarray([p['model_time_s'] for p in manifest])
    assert np.min(actual)>=7200 and np.all(np.diff(actual)>0)
    assert np.max(abs(actual-targets))<31
    assert np.fromfile(ROOT/'fac-positions.bin',dtype=np.float32).size==3960*3
    with h5py.File(ROOT/'snapshots.h5') as source,h5py.File(ROOT/'current_paths.h5') as paths:
        for index,item in enumerate(manifest):
            def reject_nonfinite(value):
                raise ValueError('Non-finite JSON number: '+value)
            key=f'snapshot-{index:02d}';g=source[key];record=json.loads((ROOT/item['file']).read_text(),parse_constant=reject_nonfinite)
            assert record['step']==g.attrs['step']==paths[key].attrs['step']
            assert record['utc']==g.attrs['utc']==paths[key].attrs['utc']
            assert len(record['fac'])==3960
            np.testing.assert_allclose(record['fac'],g['fac'][...],atol=5.1e-7)
            assert {p['group'] for p in record['paths']}=={'dayside','tail','ring','r1','r2'}
