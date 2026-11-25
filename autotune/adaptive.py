"""Host-specific cached selection among custom kernels. Search never calibrates implicitly."""
import ctypes as ct,hashlib,json,os,platform,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
ALL_MODES={7,0,1,2,3,4,5,100,101,102,103,110,111,112,113,120,121}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def host_facts():
    if platform.system()!='Linux' or platform.machine()!='x86_64':raise RuntimeError('Requires Linux x86-64 with AVX2/FMA; ARM is unsupported.')
    affinity=sorted(os.sched_getaffinity(0))
    if len(affinity)!=1:raise RuntimeError('Pin to exactly one logical CPU before calibration/search.')
    cpu=affinity[0];fields={}
    for block in Path('/proc/cpuinfo').read_text().split('\n\n'):
        d=dict((a.strip(),b.strip()) for a,b in (line.split(':',1) for line in block.splitlines() if ':' in line))
        if d.get('processor')==str(cpu):fields=d;break
    if not {'avx2','fma','avx'}<=set(fields.get('flags','').split()):raise RuntimeError('AVX2/FMA not exposed by this CPU/OS.')
    caches=[]
    for folder in sorted(Path(f'/sys/devices/system/cpu/cpu{cpu}/cache').glob('index*')):
        caches.append({name:(folder/name).read_text().strip() for name in ['level','type','size','coherency_line_size'] if (folder/name).exists()})
    return dict(machine=platform.machine(),kernel=platform.release(),cpu={k:fields.get(k) for k in ['vendor_id','cpu family','model','model name','stepping','microcode','flags']},affinity=affinity,caches=caches,threads=1,numpy=np.__version__,python=list(sys.version_info[:2]))
def identity():
    facts=host_facts()
    for name in ['src/autotune_kernels.cpp','src/benchmark.cpp','build/libautotune.so','adaptive.py']:
        facts[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    facts['build']=json.loads((ROOT/'build/build.json').read_text())
    return facts
def save_profile(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    wrapper={'payload':payload,'sha256':digest(payload)}
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(wrapper,indent=2));temp.replace(path)
def read_profile(path,current):
    if not path or not Path(path).exists():return None,'missing profile; original dispatcher used'
    try:
        wrapper=json.loads(Path(path).read_text());p=wrapper['payload']
        if wrapper['sha256']!=digest(p):return None,'corrupt profile; original dispatcher used'
        if p['identity']!=current:return None,'host/build/thread identity changed; recalibration required'
        if p.get('schema')!=1:return None,'unsupported profile schema'
        for row in p['entries'].values():
            if row['mode'] not in ALL_MODES or row['block']!=256:raise ValueError('Invalid kernel')
        return p,'matched'
    except (OSError,ValueError,KeyError,TypeError):return None,'invalid profile; original dispatcher used'
def query_kind(x,d):
    return 'byte' if d<=258 and bool(np.all((x>=0)&(x<=255)&(x==np.floor(x)))) else 'float'
def candidates(kind,d,nq):
    if kind=='byte':
        pairs=[(1,100,110),(2,101,111),(4,102,112),(8,103,113)]
        default=110 if nq==1 else 111 if nq==2 else 112 if nq<=4 else 113
        modes=[v for count,a,b in pairs if count<=nq for v in [a,b] if v!=default]
        return [7]+modes
    if d==25:return [7,120] if nq>=8 else [7,121]
    return [7,0,1,2,3,4,5]
class AdaptiveIndex:
    def __init__(self,x,profile=None):
        self.facts=identity();self.x=np.array(x,dtype=np.float32,order='C',copy=True)
        if self.x.ndim!=2 or min(self.x.shape)<1 or not np.isfinite(self.x).all():raise ValueError('Expected nonempty finite N x D float32 data')
        self.x.flags.writeable=False;self.n,self.d=self.x.shape
        self.database_hash=hashlib.sha256(memoryview(self.x).cast('B')).hexdigest()
        self.database_kind=query_kind(self.x,self.d)
        self.profile,self.profile_status=read_profile(profile,self.facts)
        self.lib=ct.CDLL(str(ROOT/'build/libautotune.so'))
        fp=np.ctypeslib.ndpointer(dtype=np.float32,flags='C_CONTIGUOUS');ip=np.ctypeslib.ndpointer(dtype=np.int32,flags='C_CONTIGUOUS')
        self.lib.packed_create.argtypes=[fp,ct.c_int,ct.c_int];self.lib.packed_create.restype=ct.c_void_p
        self.lib.packed_tuned.argtypes=[ct.c_void_p,fp,ct.c_int,ct.c_int,ct.c_int,ct.c_int,fp,ip]
        self.lib.packed_destroy.argtypes=[ct.c_void_p]
        self.handle=self.lib.packed_create(self.x,self.n,self.d)
        if not self.handle:raise MemoryError('Index allocation failed')
        self.last_mode=7
    def key(self,nq,k,kind):return f'{self.database_hash}:{self.n}:{self.d}:{nq}:{k}:{kind}'
    def prepare(self,q,k):
        if sorted(os.sched_getaffinity(0))!=self.facts['affinity']:raise RuntimeError('CPU affinity changed after index creation')
        q=np.ascontiguousarray(q,dtype=np.float32)
        if q.ndim!=2 or q.shape[1]!=self.d or not len(q) or not np.isfinite(q).all() or not 1<=k<=self.n:raise ValueError('Invalid query or K')
        kind=query_kind(q,self.d) if self.database_kind=='byte' else 'float'
        return q,kind
    def invoke(self,q,k,mode):
        ds=np.empty((len(q),k),'float32');ids=np.empty((len(q),k),'int32')
        if self.lib.packed_tuned(self.handle,q,len(q),k,mode,256,ds,ids)!=0:raise RuntimeError('Native search failed')
        return ds,ids
    def search(self,q,k):
        q,kind=self.prepare(q,k);entry=(self.profile or {}).get('entries',{}).get(self.key(len(q),k,kind))
        self.last_mode=entry['mode'] if entry and entry['mode'] in candidates(kind,self.d,len(q)) else 7
        return self.invoke(q,k,self.last_mode)
    def forced(self,q,k,mode):
        q,kind=self.prepare(q,k)
        if mode not in candidates(kind,self.d,len(q)):raise ValueError('Inapplicable candidate')
        return self.invoke(q,k,mode)
    def close(self):
        if getattr(self,'handle',None):self.lib.packed_destroy(self.handle);self.handle=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
