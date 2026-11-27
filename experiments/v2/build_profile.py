"""Build separate control/diagnostic libraries without editing release sources."""
from pathlib import Path
import hashlib,json,subprocess,shutil
ROOT=Path(__file__).resolve().parents[2]
FIELDS=['prepare_ns','distance_ns','selection_ns','finalize_ns','sampled_tiles','total_tiles','sampled_candidates','heap_inserts','heap_replacements']
HEADER=r"""
#include <chrono>
#include <cstdint>
struct V2Profile { uint64_t v[9] = {}; };
static thread_local V2Profile vp;
static thread_local uint64_t vmask=127, vserial=0, vseed=1;
static inline uint64_t vnow(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
static inline bool vsample(){uint64_t x=(++vserial)+vseed; x^=x>>30; x*=0xbf58476d1ce4e5b9ULL; x^=x>>27; x*=0x94d049bb133111ebULL; x^=x>>31; return (x&vmask)==0;}
extern "C" void v2_reset(uint64_t period,uint64_t seed){vp=V2Profile{};vserial=0;vmask=period-1;vseed=seed;}
extern "C" void v2_read(uint64_t* out){for(int i=0;i<9;++i)out[i]=vp.v[i];}
"""
def instrument(source):
    for name in ['byte_search','byte128_search']:
        start=source.index('template<int R,int S> int '+name+'(')
        end=source.index('\n}\n',start)+3
        f=source[start:end]
        f=f.replace('float* ds,int* ids){','float* ds,int* ids){\n    const uint64_t prep_start=vnow();',1)
        needle='    for(int ba=0;ba<p.n;ba+=blocksize)'
        assert f.count(needle)==1
        f=f.replace(needle,'    vp.v[0]+=vnow()-prep_start;\n'+needle,1)
        needle='        __m256i acc[R][S];'
        f=f.replace(needle,'        ++vp.v[5]; const bool sample=vsample(); uint64_t t0=sample?vnow():0;\n'+needle,1)
        needle='        for(int r=0;r<std::min(R,nq-qa);++r){'
        assert f.count(needle)==1
        f=f.replace(needle,'        uint64_t t1=sample?vnow():0;\n'+needle,1)
        # Counters run only on sampled tiles, not for every heap update.
        f=f.replace('Hit v{lanes[l],b+l};','Hit v{lanes[l],b+l}; if(sample)++vp.v[6];')
        f=f.replace('h.push_back(v);','if(sample)++vp.v[7];h.push_back(v);')
        f=f.replace('else if(less_hit(v,h.front()))replace_heap_root(h,v);','else if(less_hit(v,h.front())){if(sample)++vp.v[8];replace_heap_root(h,v);}')
        needle='      }\n    for(int qi=0;qi<nq;++qi)'
        assert f.count(needle)==1
        f=f.replace(needle,'        if(sample){uint64_t t2=vnow();vp.v[1]+=t1-t0;vp.v[2]+=t2-t1;++vp.v[4];}\n      }\n    const uint64_t final_start=vnow();\n    for(int qi=0;qi<nq;++qi)',1)
        f=f.replace('    return 0;','    vp.v[3]+=vnow()-final_start;\n    return 0;',1)
        source=source[:start]+f+source[end:]
    return HEADER+source

def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    native=ROOT/'autotune/src'; source=(native/'autotune_kernels.cpp').read_text()
    shutil.copy2(native/'benchmark.cpp',out/'benchmark.cpp')
    flags=['-std=c++17','-O3','-mavx2','-mfma','-ffp-contract=off','-shared','-fPIC']
    records={}
    for name,s in [('control',source),('diagnostic',instrument(source))]:
        p=out/(name+'.cpp');p.write_text(s)
        subprocess.run(['g++',*flags,str(p),'-o',str(out/(name+'.so'))],check=True)
        records[name]={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256((out/(name+'.so')).read_bytes()).hexdigest()}
    records.update(original_source_sha256=hashlib.sha256((native/'autotune_kernels.cpp').read_bytes()).hexdigest(),flags=flags,compiler=subprocess.check_output(['g++','--version'],text=True))
    (out/'build.json').write_text(json.dumps(records,indent=2));return records
if __name__=='__main__':
    import sys
    build(sys.argv[1])
