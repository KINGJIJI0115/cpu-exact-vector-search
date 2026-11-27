"""Alternating fresh-process index-construction measurements."""
import argparse,ctypes as ct,json,os,random,resource,statistics,subprocess,sys,time
from pathlib import Path
from profile_bottlenecks import Native,vectors

def rss():
 for line in Path('/proc/self/status').read_text().splitlines():
  if line.startswith('VmRSS:'):return int(line.split()[1])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--control',type=Path,required=True);ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cpu',type=int,default=0);ap.add_argument('--child',choices=['control','candidate']);a=ap.parse_args();os.sched_setaffinity(0,{a.cpu});os.nice(10)
 if a.child:
  x=vectors(a.data/'sift1m/sift_base.fvecs');before=rss();t=time.perf_counter();obj=Native(a.control if a.child=='control' else a.candidate,x);elapsed=(time.perf_counter()-t)*1000
  obj.lib.packed_storage_bytes.argtypes=[ct.c_void_p];obj.lib.packed_storage_bytes.restype=ct.c_size_t;payload=obj.lib.packed_storage_bytes(obj.h);norm=0
  if a.child=='candidate':obj.lib.v2_norm_storage.argtypes=[ct.c_void_p];obj.lib.v2_norm_storage.restype=ct.c_size_t;norm=obj.lib.v2_norm_storage(obj.h)
  record=dict(method=a.child,setup_ms=elapsed,rss_before_kib=before,rss_after_kib=rss(),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,index_payload_bytes=int(payload+norm),norm_bytes=int(norm));obj.close();print(json.dumps(record));return
 a.out.mkdir(parents=True,exist_ok=False);rows=[];rng=random.Random(271129)
 for rep in range(3):
  methods=['control','candidate'];rng.shuffle(methods)
  for method in methods:
   cmd=[sys.executable,__file__,'--data',str(a.data),'--control',str(a.control),'--candidate',str(a.candidate),'--out',str(a.out),'--cpu',str(a.cpu),'--child',method]
   record=json.loads(subprocess.check_output(cmd,text=True));record['repeat']=rep;rows.append(record);print(record,flush=True)
 summary={m:{k:statistics.median(r[k] for r in rows if r['method']==m) for k in ['setup_ms','rss_after_kib','peak_rss_kib','index_payload_bytes','norm_bytes']} for m in ['control','candidate']}
 (a.out/'raw.json').write_text(json.dumps(rows,indent=2));(a.out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary)
if __name__=='__main__':main()
