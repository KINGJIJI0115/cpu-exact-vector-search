"""Experimental integer-dot candidate; release sources remain byte-identical."""
from pathlib import Path
import hashlib,json,shutil,subprocess
from build_profile import ROOT

def build(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 native=ROOT/'autotune/src';s=(native/'autotune_kernels.cpp').read_text()
 needle='std::vector<unsigned char> bytes;float* aligned=nullptr;'
 assert s.count(needle)==1;s=s.replace(needle,'std::vector<unsigned char> bytes;std::vector<int32_t> norms;float* aligned=nullptr;')
 start=s.index('static void make_byte_layout(Packed& p,const float* x){');end=s.index('\n}',start)
 s=s[:end]+r"""
    p.norms.assign(size_t((p.n+7)/8)*8,0);
    for(int i=0;i<p.n;++i)for(int j=0;j<p.d;++j){int v=int(x[size_t(i)*p.d+j]);p.norms[i]+=v*v;}
"""+s[end:]
 start=s.index('template<int R,int S> int byte128_search(');end=s.index('\n}\n',start)+3
 f=s[start:end].replace('int byte128_search(', 'int dot128_search(',1)
 f=f.replace('int pairs=(D+1)/2;','std::vector<int32_t> qnorm(nq,0);for(int i=0;i<nq;++i)for(int j=0;j<D;++j){int v=int(q[size_t(i)*D+j]);qnorm[i]+=v*v;}\n    int pairs=(D+1)/2;',1)
 a='__m256i t=_mm256_sub_epi16(x,_mm256_set1_epi32(qs[r][j+s]));acc[r][s]=_mm256_add_epi32(acc[r][s],_mm256_madd_epi16(t,t));'
 b='acc[r][s]=_mm256_add_epi32(acc[r][s],_mm256_madd_epi16(x,_mm256_set1_epi32(qs[r][j+s])));'
 assert f.count(a)==1;f=f.replace(a,b)
 a='__m256i t=_mm256_sub_epi16(x,_mm256_set1_epi32(qs[r][j]));acc[r][0]=_mm256_add_epi32(acc[r][0],_mm256_madd_epi16(t,t));'
 b='acc[r][0]=_mm256_add_epi32(acc[r][0],_mm256_madd_epi16(x,_mm256_set1_epi32(qs[r][j])));'
 assert f.count(a)==1;f=f.replace(a,b)
 a='__m256 fsum=_mm256_cvtepi32_ps(sum);'
 b='__m256i norms=_mm256_loadu_si256(reinterpret_cast<const __m256i*>(p.norms.data()+b));\n            sum=_mm256_sub_epi32(_mm256_add_epi32(norms,_mm256_set1_epi32(qnorm[qa+r])),_mm256_slli_epi32(sum,1));\n            __m256 fsum=_mm256_cvtepi32_ps(sum);'
 assert f.count(a)==1;f=f.replace(a,b)
 s=s[:end]+f+s[end:]
 needle='        if(mode==7){';assert s.count(needle)==1
 s=s.replace(needle,'        if((mode==200 || mode==201) && (p.d!=128 || p.bytes.empty() || !byte_coordinates(q,size_t(nq)*p.d,p.d)))return packed_tuned(ptr,q,nq,k,7,block,ds,ids);\n        if(mode==200)return dot128_search<8,1>(p,q,nq,k,block,ds,ids);\n        if(mode==201)return dot128_search<4,2>(p,q,nq,k,block,ds,ids);\n'+needle)
 s+='\nextern "C" size_t v2_norm_storage(void* ptr){return static_cast<Packed*>(ptr)->norms.capacity()*sizeof(int32_t);}\n'
 source=out/'candidate.cpp';source.write_text(s);shutil.copy2(native/'benchmark.cpp',out/'benchmark.cpp')
 flags=['-std=c++17','-O3','-mavx2','-mfma','-ffp-contract=off','-shared','-fPIC']
 subprocess.run(['g++',*flags,str(source),'-o',str(out/'candidate.so')],check=True)
 symbols=subprocess.check_output(['nm','-D',str(out/'candidate.so')],text=True)
 assert not any(w in symbols.lower() for w in ['cblas','sgemm','faiss'])
 record=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),flags=flags,no_blas_faiss_symbols=True,scope='D=128 byte-integer norm/dot identity with original fallback; extra norm array included in index construction')
 (out/'build.json').write_text(json.dumps(record,indent=2));return record
if __name__=='__main__':
 import sys
 build(sys.argv[1])
