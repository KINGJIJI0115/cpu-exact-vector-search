import json,os,tempfile,unittest
from pathlib import Path
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import numpy as np
from adaptive import AdaptiveIndex,candidates,identity,save_profile,read_profile
from calibrate import verify
from build_kernels import build
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):build()
    def test_candidates_and_fallbacks(self):
        rng=np.random.default_rng(502)
        for d,kind in [(7,'byte'),(25,'float'),(128,'byte'),(258,'byte'),(259,'byte'),(128,'float')]:
            x=rng.integers(0,256,(137,d)).astype('float32') if kind=='byte' else rng.normal(size=(137,d)).astype('float32')
            x[1]=x[0]
            with AdaptiveIndex(x) as index:
                for nq in [1,2,8]:
                    q=x[:nq].copy();q[-1]=x[0]
                    dist=((q[:,None,:].astype('float64')-x.astype('float64'))**2).sum(axis=2)
                    for k in [1,10,137]:
                        ids=np.array([np.lexsort((np.arange(len(x)),v))[:k] for v in dist]);od=np.take_along_axis(dist,ids,axis=1)
                        for mode in candidates(index.prepare(q,k)[1],d,nq):verify(index,q,k,index.forced(q,k,mode),(od,ids))
                        verify(index,q,k,index.search(q,k),(od,ids));self.assertEqual(index.last_mode,7)
    def test_saved_profile_invalidated_and_unknown_key_falls_back(self):
        x=np.arange(128*20,dtype='float32').reshape(20,128)%256
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'profile.json'
            with AdaptiveIndex(x) as a:
                facts=a.facts;key=a.key(1,1,'byte')
            payload=dict(schema=1,identity=facts,entries={key:dict(mode=100,block=256,validated=True)})
            save_profile(p,payload)
            with AdaptiveIndex(x,p) as a:
                a.search(x[:1],1);self.assertEqual(a.last_mode,100)
                a.search(x[:1],2);self.assertEqual(a.last_mode,7)
                a.search(x[:1]+.25,1);self.assertEqual(a.last_mode,7)
            with AdaptiveIndex(x+1,p) as a:a.search(x[:1],1);self.assertEqual(a.last_mode,7)
            stale=json.loads(json.dumps(facts));stale['threads']=2
            self.assertIsNone(read_profile(p,stale)[0])
            raw=json.loads(p.read_text());raw['payload']['entries'][key]['mode']=103;p.write_text(json.dumps(raw))
            self.assertIsNone(read_profile(p,facts)[0])
    def test_dot_profile_roundtrip_and_block_validation(self):
        from adaptive import DOT_MODES,mode_block
        rng=np.random.default_rng(9001);x=rng.integers(0,256,(137,128)).astype('float32');q=x[:9].copy()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'profile.json'
            with AdaptiveIndex(x) as a:
                facts=a.facts;key=a.key(9,10,'byte');expected=a.forced(q,10,7)
            for mode in DOT_MODES:
                payload=dict(schema=1,identity=facts,entries={key:dict(mode=mode,block=mode_block(mode),validated=True)})
                save_profile(p,payload)
                with AdaptiveIndex(x,p) as a:
                    self.assertEqual(a.profile_status,'matched')
                    result=a.search(q,10);self.assertEqual(a.last_mode,mode)
                    np.testing.assert_array_equal(result[0],expected[0]);np.testing.assert_array_equal(result[1],expected[1])
                    a.search(q+.25,10);self.assertEqual(a.last_mode,7)
                payload['entries'][key]['block']=64;save_profile(p,payload)
                self.assertIsNone(read_profile(p,facts)[0])
    def test_bad_inputs(self):
        with AdaptiveIndex(np.zeros((10,128),'float32')) as a:
            for q,k in [(np.zeros((1,127)),1),(np.zeros((1,128)),11),(np.full((1,128),np.nan),1)]:
                with self.assertRaises(ValueError):a.search(q,k)
if __name__=='__main__':unittest.main()
