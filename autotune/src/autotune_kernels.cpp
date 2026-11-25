#include <cstdint>
#include <memory>
// Direct squared differences, no BLAS calls and no dot-product identity.
#define VECTOR_SEARCH_LIBRARY
#include "benchmark.cpp"
struct Packed {int n,d;std::vector<float> a;std::vector<unsigned char> bytes;float* aligned=nullptr;};
static void make_byte_layout(Packed&,const float*);
extern "C" void* packed_create(const float* x,int n,int d) {
    try {
        std::unique_ptr<Packed> p(new Packed{n,d,std::vector<float>(static_cast<size_t>((n+7)/8)*d*8+16)});
        p->aligned=reinterpret_cast<float*>((reinterpret_cast<std::uintptr_t>(p->a.data())+63)&~std::uintptr_t(63));
        for(int b=0;b<n;b+=8) for(int j=0;j<d;++j) for(int l=0;l<8;++l)
            p->aligned[static_cast<size_t>(b/8)*d*8+j*8+l]=b+l<n?x[static_cast<size_t>(b+l)*d+j]:0;
        make_byte_layout(*p,x);
        return p.release();
    } catch(...) {return nullptr;}
}
extern "C" void packed_destroy(void* p) {delete static_cast<Packed*>(p);}
template<int R,int S> int tuned_search(Packed& p,const float* q,int nq,int k,int blocksize,float* ds,int* ids) {
    std::vector<std::vector<Hit>> heaps(nq);for(auto& h:heaps)h.reserve(k);
    for(int ba=0;ba<p.n;ba+=blocksize) for(int qa=0;qa<nq;qa+=R)
      for(int b=ba;b<std::min(ba+blocksize,p.n);b+=8) {
        __m256 acc[R][S];
        const float* queries[R];
        for(int r=0;r<R;++r){queries[r]=q+std::min(qa+r,nq-1)*p.d;for(int s=0;s<S;++s)acc[r][s]=_mm256_setzero_ps();}
        const float* base=p.aligned+static_cast<size_t>(b/8)*p.d*8;
        int j=0;
        for(;j+S<=p.d;j+=S) {
            #pragma GCC unroll 8
            for(int s=0;s<S;++s) {
                __m256 x=_mm256_loadu_ps(base+(j+s)*8);
                #pragma GCC unroll 8
                for(int r=0;r<R;++r) {
                    __m256 t=_mm256_sub_ps(x,_mm256_set1_ps(queries[r][j+s]));
                    acc[r][s]=_mm256_fmadd_ps(t,t,acc[r][s]);
                }
            }
        }
        for(;j<p.d;++j){__m256 x=_mm256_loadu_ps(base+j*8);for(int r=0;r<R;++r){__m256 t=_mm256_sub_ps(x,_mm256_set1_ps(queries[r][j]));acc[r][0]=_mm256_fmadd_ps(t,t,acc[r][0]);}}
        for(int r=0;r<std::min(R,nq-qa);++r) {
            __m256 sum=acc[r][0];for(int s=1;s<S;++s)sum=_mm256_add_ps(sum,acc[r][s]);
            auto& h=heaps[qa+r];float limit=h.size()==static_cast<size_t>(k)?h.front().distance:INFINITY;
            unsigned mask=_mm256_movemask_ps(_mm256_cmp_ps(sum,_mm256_set1_ps(limit),_CMP_LE_OQ));
            if(!mask)continue;float lanes[8];_mm256_storeu_ps(lanes,sum);
            for(int l=0;l<8&&b+l<p.n;++l)if(mask&(1u<<l)) {
                Hit v{lanes[l],b+l};
                if(h.size()<static_cast<size_t>(k)){h.push_back(v);std::push_heap(h.begin(),h.end(),less_hit);}
                else if(less_hit(v,h.front())){std::pop_heap(h.begin(),h.end(),less_hit);h.back()=v;std::push_heap(h.begin(),h.end(),less_hit);}
            }
        }
      }
    for(int qi=0;qi<nq;++qi){auto& h=heaps[qi];std::sort_heap(h.begin(),h.end(),less_hit);for(int j=0;j<k;++j){ds[qi*k+j]=h[j].distance;ids[qi*k+j]=h[j].id;}}
    return 0;
}
template<int C,int Start> int chunk_search(Packed& p,const float* q,int nq,int k,int blocksize,float* ds,int* ids) {
    constexpr int R=8,S=1;
    std::vector<std::vector<Hit>> heaps(nq);for(auto& h:heaps)h.reserve(k);
    for(int ba=0;ba<p.n;ba+=blocksize) for(int qa=0;qa<nq;qa+=R)
      for(int b=ba;b<std::min(ba+blocksize,p.n);b+=8) {
        __m256 acc[R][S];
        const float* queries[R];
        for(int r=0;r<R;++r){queries[r]=q+std::min(qa+r,nq-1)*p.d;for(int s=0;s<S;++s)acc[r][s]=_mm256_setzero_ps();}
        const float* base=p.aligned+static_cast<size_t>(b/8)*p.d*8;

        bool abandoned=false;
        for(int ja=0;ja<p.d;ja+=C){
            int end=std::min(ja+C,p.d);
            for(int j=ja;j<end;++j){
                __m256 x=_mm256_loadu_ps(base+j*8);
                #pragma GCC unroll 8
                for(int r=0;r<R;++r){__m256 t=_mm256_sub_ps(x,_mm256_set1_ps(queries[r][j]));acc[r][0]=_mm256_fmadd_ps(t,t,acc[r][0]);}
            }
            if(end>=Start && end<p.d){
                unsigned alive=0;
                for(int r=0;r<std::min(R,nq-qa);++r){
                    auto& h=heaps[qa+r];float limit=h.size()==static_cast<size_t>(k)?h.front().distance:INFINITY;
                    alive|=_mm256_movemask_ps(_mm256_cmp_ps(acc[r][0],_mm256_set1_ps(limit),_CMP_LE_OQ));
                }
                if(!alive){abandoned=true;break;}
            }
        }
        if(abandoned)continue;
        for(int r=0;r<std::min(R,nq-qa);++r) {
            __m256 sum=acc[r][0];for(int s=1;s<S;++s)sum=_mm256_add_ps(sum,acc[r][s]);
            auto& h=heaps[qa+r];float limit=h.size()==static_cast<size_t>(k)?h.front().distance:INFINITY;
            unsigned mask=_mm256_movemask_ps(_mm256_cmp_ps(sum,_mm256_set1_ps(limit),_CMP_LE_OQ));
            if(!mask)continue;float lanes[8];_mm256_storeu_ps(lanes,sum);
            for(int l=0;l<8&&b+l<p.n;++l)if(mask&(1u<<l)) {
                Hit v{lanes[l],b+l};
                if(h.size()<static_cast<size_t>(k)){h.push_back(v);std::push_heap(h.begin(),h.end(),less_hit);}
                else if(less_hit(v,h.front())){std::pop_heap(h.begin(),h.end(),less_hit);h.back()=v;std::push_heap(h.begin(),h.end(),less_hit);}
            }
        }
      }
    for(int qi=0;qi<nq;++qi){auto& h=heaps[qi];std::sort_heap(h.begin(),h.end(),less_hit);for(int j=0;j<k;++j){ds[qi*k+j]=h[j].distance;ids[qi*k+j]=h[j].id;}}
    return 0;
}


// First compute a shared prefix; refine only live queries in pairs with four accumulators.
template<int Prefix> int selective_search(Packed& p,const float* q,int nq,int k,int blocksize,float* ds,int* ids){
    std::vector<std::vector<Hit>> heaps(nq);for(auto& h:heaps)h.reserve(k);
    for(int ba=0;ba<p.n;ba+=blocksize)for(int qa=0;qa<nq;qa+=8)
      for(int b=ba;b<std::min(ba+blocksize,p.n);b+=8){
        __m256 partial[8];const float* qs[8];
        for(int r=0;r<8;++r){partial[r]=_mm256_setzero_ps();qs[r]=q+std::min(qa+r,nq-1)*p.d;}
        const float* base=p.aligned+size_t(b/8)*p.d*8;int split=std::min(Prefix,p.d);
        for(int j=0;j<split;++j){
            __m256 x=_mm256_loadu_ps(base+j*8);
            #pragma GCC unroll 8
            for(int r=0;r<8;++r){__m256 t=_mm256_sub_ps(x,_mm256_set1_ps(qs[r][j]));partial[r]=_mm256_fmadd_ps(t,t,partial[r]);}
        }
        int live[8],count=0;
        for(int r=0;r<std::min(8,nq-qa);++r){
            auto& h=heaps[qa+r];float limit=h.size()==size_t(k)?h.front().distance:INFINITY;
            if(_mm256_movemask_ps(_mm256_cmp_ps(partial[r],_mm256_set1_ps(limit),_CMP_LE_OQ)))live[count++]=r;
        }
        for(int a=0;a<count;a+=2){
            int rr[2]={live[a],live[std::min(a+1,count-1)]};__m256 acc[2][4];
            for(int t=0;t<2;++t){acc[t][0]=partial[rr[t]];for(int s=1;s<4;++s)acc[t][s]=_mm256_setzero_ps();}
            for(int j=split;j<p.d;j+=4){
                #pragma GCC unroll 4
                for(int s=0;s<4;++s)if(j+s<p.d){
                    __m256 x=_mm256_loadu_ps(base+(j+s)*8);
                    #pragma GCC unroll 2
                    for(int t=0;t<2;++t){__m256 delta=_mm256_sub_ps(x,_mm256_set1_ps(qs[rr[t]][j+s]));acc[t][s]=_mm256_fmadd_ps(delta,delta,acc[t][s]);}
                }
            }
            for(int t=0;t<std::min(2,count-a);++t){
                __m256 sum=acc[t][0];for(int s=1;s<4;++s)sum=_mm256_add_ps(sum,acc[t][s]);
                auto& h=heaps[qa+rr[t]];float limit=h.size()==size_t(k)?h.front().distance:INFINITY;
                unsigned mask=_mm256_movemask_ps(_mm256_cmp_ps(sum,_mm256_set1_ps(limit),_CMP_LE_OQ));
                if(!mask)continue;float lanes[8];_mm256_storeu_ps(lanes,sum);
                for(int l=0;l<8&&b+l<p.n;++l)if(mask&(1u<<l)){
                    Hit v{lanes[l],b+l};
                    if(h.size()<size_t(k)){h.push_back(v);std::push_heap(h.begin(),h.end(),less_hit);}
                    else if(less_hit(v,h.front())){std::pop_heap(h.begin(),h.end(),less_hit);h.back()=v;std::push_heap(h.begin(),h.end(),less_hit);}
                }
            }
        }
      }
    for(int qi=0;qi<nq;++qi){auto& h=heaps[qi];std::sort_heap(h.begin(),h.end(),less_hit);for(int j=0;j<k;++j){ds[qi*k+j]=h[j].distance;ids[qi*k+j]=h[j].id;}}
    return 0;
}

// Floating-point fallback policy; checked integral routing is handled separately.
extern "C" int packed_route(int d,int nq,int k){return d==25 && nq==1 ? 13 : (d==25 && nq>=5 ? 14 : (d==128 && nq>=128 ? (k>=1 && k<=10 ? 1 : (k==100 ? 2 : 0)) : 0));}
static inline void replace_heap_root(std::vector<Hit>& h,Hit v){
    size_t pos=0;
    while(pos*2+1<h.size()){
        size_t child=pos*2+1;
        if(child+1<h.size() && less_hit(h[child],h[child+1]))++child;
        if(!less_hit(v,h[child]))break;
        h[pos]=h[child];pos=child;
    }
    h[pos]=v;
}
// Lossless unsigned-byte coordinates; two dimensions per 32-bit SIMD lane.
// Eligibility is checked on all database/query coordinates, never on a dataset name.
static bool byte_coordinates(const float* a,size_t n,int d){
    if(d<1 || d>258)return false; // d*255^2 <= 2^24: exact float output too.
    for(size_t i=0;i<n;++i)if(!(a[i]>=0 && a[i]<=255) || a[i]!=std::floor(a[i]))return false;
    return true;
}
static void make_byte_layout(Packed& p,const float* x){
    if(!byte_coordinates(x,size_t(p.n)*p.d,p.d))return;
    int pairs=(p.d+1)/2;p.bytes.resize(size_t((p.n+7)/8)*pairs*16);
    for(int b=0;b<p.n;b+=8)for(int j=0;j<pairs;++j)for(int l=0;l<8;++l)for(int s=0;s<2;++s)
        p.bytes[size_t(b/8)*pairs*16+j*16+l*2+s]=(b+l<p.n && j*2+s<p.d)?static_cast<unsigned char>(x[size_t(b+l)*p.d+j*2+s]):0;
}
template<int R,int S> int byte_search(Packed& p,const float* q,int nq,int k,int blocksize,float* ds,int* ids){
    if(p.bytes.empty() || !byte_coordinates(q,size_t(nq)*p.d,p.d))return tuned_search<R,S>(p,q,nq,k,blocksize,ds,ids);
    int pairs=(p.d+1)/2;std::vector<int> qp(size_t(nq)*pairs);
    for(int qi=0;qi<nq;++qi)for(int j=0;j<pairs;++j)
        qp[size_t(qi)*pairs+j]=int(q[size_t(qi)*p.d+j*2])|((j*2+1<p.d?int(q[size_t(qi)*p.d+j*2+1]):0)<<16);
    std::vector<std::vector<Hit>> heaps(nq);for(auto& h:heaps)h.reserve(k);
    for(int ba=0;ba<p.n;ba+=blocksize)for(int qa=0;qa<nq;qa+=R)
      for(int b=ba;b<std::min(ba+blocksize,p.n);b+=8){
        __m256i acc[R][S];const int* qs[R];
        for(int r=0;r<R;++r){qs[r]=qp.data()+size_t(std::min(qa+r,nq-1))*pairs;for(int s=0;s<S;++s)acc[r][s]=_mm256_setzero_si256();}
        const unsigned char* base=p.bytes.data()+size_t(b/8)*pairs*16;
        int j=0;
        for(;j+S<=pairs;j+=S){
            #pragma GCC unroll 8
            for(int s=0;s<S;++s){
                __m256i x=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(base+(j+s)*16)));
                #pragma GCC unroll 8
                for(int r=0;r<R;++r){__m256i t=_mm256_sub_epi16(x,_mm256_set1_epi32(qs[r][j+s]));acc[r][s]=_mm256_add_epi32(acc[r][s],_mm256_madd_epi16(t,t));}
            }
        }
        for(;j<pairs;++j){
            __m256i x=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(base+j*16)));
            for(int r=0;r<R;++r){__m256i t=_mm256_sub_epi16(x,_mm256_set1_epi32(qs[r][j]));acc[r][0]=_mm256_add_epi32(acc[r][0],_mm256_madd_epi16(t,t));}
        }
        for(int r=0;r<std::min(R,nq-qa);++r){
            __m256i sum=acc[r][0];for(int s=1;s<S;++s)sum=_mm256_add_epi32(sum,acc[r][s]);
            __m256 fsum=_mm256_cvtepi32_ps(sum);auto& h=heaps[qa+r];float limit=h.size()==size_t(k)?h.front().distance:INFINITY;
            unsigned mask=_mm256_movemask_ps(_mm256_cmp_ps(fsum,_mm256_set1_ps(limit),_CMP_LE_OQ));
            if(!mask)continue;float lanes[8];_mm256_storeu_ps(lanes,fsum);
            for(int l=0;l<8 && b+l<p.n;++l)if(mask&(1u<<l)){
                Hit v{lanes[l],b+l};
                if(h.size()<size_t(k)){h.push_back(v);std::push_heap(h.begin(),h.end(),less_hit);}
                else if(less_hit(v,h.front()))replace_heap_root(h,v);
            }
        }
      }
    for(int qi=0;qi<nq;++qi){auto& h=heaps[qi];std::sort_heap(h.begin(),h.end(),less_hit);for(int j=0;j<k;++j){ds[qi*k+j]=h[j].distance;ids[qi*k+j]=h[j].id;}}
    return 0;
}
template<int R,int S> int byte128_search(Packed& p,const float* q,int nq,int k,int blocksize,float* ds,int* ids){
    constexpr int D=128;if(p.d!=D)return byte_search<R,S>(p,q,nq,k,blocksize,ds,ids);
    if(p.bytes.empty() || !byte_coordinates(q,size_t(nq)*D,D))return tuned_search<R,S>(p,q,nq,k,blocksize,ds,ids);
    int pairs=(D+1)/2;std::vector<int> qp(size_t(nq)*pairs);
    for(int qi=0;qi<nq;++qi)for(int j=0;j<pairs;++j)
        qp[size_t(qi)*pairs+j]=int(q[size_t(qi)*D+j*2])|((j*2+1<D?int(q[size_t(qi)*D+j*2+1]):0)<<16);
    std::vector<std::vector<Hit>> heaps(nq);for(auto& h:heaps)h.reserve(k);
    for(int ba=0;ba<p.n;ba+=blocksize)for(int qa=0;qa<nq;qa+=R)
      for(int b=ba;b<std::min(ba+blocksize,p.n);b+=8){
        __m256i acc[R][S];const int* qs[R];
        for(int r=0;r<R;++r){qs[r]=qp.data()+size_t(std::min(qa+r,nq-1))*pairs;for(int s=0;s<S;++s)acc[r][s]=_mm256_setzero_si256();}
        const unsigned char* base=p.bytes.data()+size_t(b/8)*pairs*16;
        int j=0;
        #pragma GCC unroll 64
        for(;j+S<=pairs;j+=S){
            #pragma GCC unroll 8
            for(int s=0;s<S;++s){
                __m256i x=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(base+(j+s)*16)));
                #pragma GCC unroll 8
                for(int r=0;r<R;++r){__m256i t=_mm256_sub_epi16(x,_mm256_set1_epi32(qs[r][j+s]));acc[r][s]=_mm256_add_epi32(acc[r][s],_mm256_madd_epi16(t,t));}
            }
        }
        for(;j<pairs;++j){
            __m256i x=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(base+j*16)));
            for(int r=0;r<R;++r){__m256i t=_mm256_sub_epi16(x,_mm256_set1_epi32(qs[r][j]));acc[r][0]=_mm256_add_epi32(acc[r][0],_mm256_madd_epi16(t,t));}
        }
        for(int r=0;r<std::min(R,nq-qa);++r){
            __m256i sum=acc[r][0];for(int s=1;s<S;++s)sum=_mm256_add_epi32(sum,acc[r][s]);
            __m256 fsum=_mm256_cvtepi32_ps(sum);auto& h=heaps[qa+r];float limit=h.size()==size_t(k)?h.front().distance:INFINITY;
            unsigned mask=_mm256_movemask_ps(_mm256_cmp_ps(fsum,_mm256_set1_ps(limit),_CMP_LE_OQ));
            if(!mask)continue;float lanes[8];_mm256_storeu_ps(lanes,fsum);
            for(int l=0;l<8 && b+l<p.n;++l)if(mask&(1u<<l)){
                Hit v{lanes[l],b+l};
                if(h.size()<size_t(k)){h.push_back(v);std::push_heap(h.begin(),h.end(),less_hit);}
                else if(less_hit(v,h.front()))replace_heap_root(h,v);
            }
        }
      }
    for(int qi=0;qi<nq;++qi){auto& h=heaps[qi];std::sort_heap(h.begin(),h.end(),less_hit);for(int j=0;j<k;++j){ds[qi*k+j]=h[j].distance;ids[qi*k+j]=h[j].id;}}
    return 0;
}

template<int R,int S> int fixed25_search(Packed& p,const float* q,int nq,int k,int blocksize,float* ds,int* ids) {
    constexpr int D=25;if(p.d!=D)return tuned_search<R,S>(p,q,nq,k,blocksize,ds,ids);
    std::vector<std::vector<Hit>> heaps(nq);for(auto& h:heaps)h.reserve(k);
    for(int ba=0;ba<p.n;ba+=blocksize) for(int qa=0;qa<nq;qa+=R)
      for(int b=ba;b<std::min(ba+blocksize,p.n);b+=8) {
        __m256 acc[R][S];
        const float* queries[R];
        for(int r=0;r<R;++r){queries[r]=q+std::min(qa+r,nq-1)*D;for(int s=0;s<S;++s)acc[r][s]=_mm256_setzero_ps();}
        const float* base=p.aligned+static_cast<size_t>(b/8)*D*8;
        int j=0;
        #pragma GCC unroll 32
        for(;j+S<=D;j+=S) {
            #pragma GCC unroll 8
            for(int s=0;s<S;++s) {
                __m256 x=_mm256_loadu_ps(base+(j+s)*8);
                #pragma GCC unroll 8
                for(int r=0;r<R;++r) {
                    __m256 t=_mm256_sub_ps(x,_mm256_set1_ps(queries[r][j+s]));
                    acc[r][s]=_mm256_fmadd_ps(t,t,acc[r][s]);
                }
            }
        }
        for(;j<D;++j){__m256 x=_mm256_loadu_ps(base+j*8);for(int r=0;r<R;++r){__m256 t=_mm256_sub_ps(x,_mm256_set1_ps(queries[r][j]));acc[r][0]=_mm256_fmadd_ps(t,t,acc[r][0]);}}
        for(int r=0;r<std::min(R,nq-qa);++r) {
            __m256 sum=acc[r][0];for(int s=1;s<S;++s)sum=_mm256_add_ps(sum,acc[r][s]);
            auto& h=heaps[qa+r];float limit=h.size()==static_cast<size_t>(k)?h.front().distance:INFINITY;
            unsigned mask=_mm256_movemask_ps(_mm256_cmp_ps(sum,_mm256_set1_ps(limit),_CMP_LE_OQ));
            if(!mask)continue;float lanes[8];_mm256_storeu_ps(lanes,sum);
            for(int l=0;l<8&&b+l<p.n;++l)if(mask&(1u<<l)) {
                Hit v{lanes[l],b+l};
                if(h.size()<static_cast<size_t>(k)){h.push_back(v);std::push_heap(h.begin(),h.end(),less_hit);}
                else if(less_hit(v,h.front())){replace_heap_root(h,v);}
            }
        }
      }
    for(int qi=0;qi<nq;++qi){auto& h=heaps[qi];std::sort_heap(h.begin(),h.end(),less_hit);for(int j=0;j<k;++j){ds[qi*k+j]=h[j].distance;ids[qi*k+j]=h[j].id;}}
    return 0;
}


// Checked data-dependent routing; queries are never assumed to be integral.
extern "C" int packed_query_route(void* ptr,const float* q,int nq,int k){
    auto& p=*static_cast<Packed*>(ptr);if(nq<1 || k<1 || k>p.n)return -1;
    if(!p.bytes.empty() && byte_coordinates(q,size_t(nq)*p.d,p.d))return nq==1?10:(nq==2?15:(nq<=4?11:12));
    return packed_route(p.d,nq,k);
}
extern "C" size_t packed_storage_bytes(void* ptr){auto& p=*static_cast<Packed*>(ptr);return p.a.capacity()*sizeof(float)+p.bytes.capacity();}
extern "C" size_t packed_byte_storage_bytes(void* ptr){return static_cast<Packed*>(ptr)->bytes.capacity();}

extern "C" int packed_tuned(void* ptr,const float* q,int nq,int k,int mode,int block,float* ds,int* ids) {
    try {auto& p=*static_cast<Packed*>(ptr);if(nq<1||k<1||k>p.n||block<8||block%8)return 2;
        if(mode==100)return byte_search<1,4>(p,q,nq,k,block,ds,ids);
        if(mode==101)return byte_search<2,4>(p,q,nq,k,block,ds,ids);
        if(mode==102)return byte_search<4,2>(p,q,nq,k,block,ds,ids);
        if(mode==103)return byte_search<8,1>(p,q,nq,k,block,ds,ids);
        if(mode==110)return byte128_search<1,4>(p,q,nq,k,block,ds,ids);
        if(mode==111)return byte128_search<2,4>(p,q,nq,k,block,ds,ids);
        if(mode==112)return byte128_search<4,2>(p,q,nq,k,block,ds,ids);
        if(mode==113)return byte128_search<8,1>(p,q,nq,k,block,ds,ids);
        if(mode==120)return fixed25_search<1,4>(p,q,nq,k,block,ds,ids);
        if(mode==121)return fixed25_search<8,1>(p,q,nq,k,block,ds,ids);
        if(mode==7){
            int route=packed_query_route(ptr,q,nq,k);
            if(route==10)return byte128_search<1,4>(p,q,nq,k,block,ds,ids);
            if(route==11)return byte128_search<4,2>(p,q,nq,k,block,ds,ids);
            if(route==12)return byte128_search<8,1>(p,q,nq,k,block,ds,ids);
            if(route==15)return byte128_search<2,4>(p,q,nq,k,block,ds,ids);
            if(route==13)return fixed25_search<1,4>(p,q,nq,k,block,ds,ids);
            if(route==14)return fixed25_search<8,1>(p,q,nq,k,block,ds,ids);
            if(route==1)return chunk_search<32,64>(p,q,nq,k,block,ds,ids);
            if(route==2)return selective_search<96>(p,q,nq,k,block,ds,ids);
            mode=6;
        }
        if(mode==10)return byte128_search<1,4>(p,q,nq,k,block,ds,ids);
        if(mode==11)return byte128_search<4,2>(p,q,nq,k,block,ds,ids);
        if(mode==12)return byte128_search<8,1>(p,q,nq,k,block,ds,ids);
        if(mode==13)return fixed25_search<1,4>(p,q,nq,k,block,ds,ids);
        if(mode==14)return fixed25_search<8,1>(p,q,nq,k,block,ds,ids);
        if(mode==15)return byte128_search<2,4>(p,q,nq,k,block,ds,ids);
        if(mode==9)return selective_search<96>(p,q,nq,k,block,ds,ids);
        if(mode==8)return chunk_search<32,64>(p,q,nq,k,block,ds,ids);
        if(mode==0)return tuned_search<4,2>(p,q,nq,k,block,ds,ids);
        if(mode==1)return tuned_search<8,1>(p,q,nq,k,block,ds,ids);
        if(mode==2)return tuned_search<2,4>(p,q,nq,k,block,ds,ids);
        if(mode==3)return tuned_search<1,4>(p,q,nq,k,block,ds,ids);
        if(mode==4)return tuned_search<2,2>(p,q,nq,k,block,ds,ids);
        if(mode==5)return tuned_search<4,1>(p,q,nq,k,block,ds,ids);
        if(mode==6){
            if(nq==1)return tuned_search<1,4>(p,q,nq,k,block,ds,ids);
            if(nq<=2)return tuned_search<2,2>(p,q,nq,k,block,ds,ids);
            if(nq<=4)return tuned_search<4,1>(p,q,nq,k,block,ds,ids);
            return tuned_search<8,1>(p,q,nq,k,block,ds,ids);
        }
        return 2;
    }catch(...){return 1;}
}
extern "C" int packed_search(void* ptr,const float* q,int nq,int k,float* ds,int* ids) {
    try {
        auto& p=*static_cast<Packed*>(ptr);
        if(nq<1||k<1||k>p.n)return 2;
        std::vector<std::vector<Hit>> h(nq);
        for(auto& v:h)v.reserve(k);
        for(int block=0;block<p.n;block+=256)
          for(int qa=0;qa<nq;qa+=4)
            for(int b=block;b<std::min(block+256,p.n);b+=8) {
                __m256 s0=_mm256_setzero_ps(),s1=s0,s2=s0,s3=s0;
                const int q1=std::min(qa+1,nq-1),q2=std::min(qa+2,nq-1),q3=std::min(qa+3,nq-1);
                for(int j=0;j<p.d;++j) {
                    __m256 x=_mm256_loadu_ps(p.aligned+static_cast<size_t>(b/8)*p.d*8+j*8);
                    __m256 t0=_mm256_sub_ps(x,_mm256_set1_ps(q[qa*p.d+j]));
                    __m256 t1=_mm256_sub_ps(x,_mm256_set1_ps(q[q1*p.d+j]));
                    __m256 t2=_mm256_sub_ps(x,_mm256_set1_ps(q[q2*p.d+j]));
                    __m256 t3=_mm256_sub_ps(x,_mm256_set1_ps(q[q3*p.d+j]));
                    s0=_mm256_fmadd_ps(t0,t0,s0);s1=_mm256_fmadd_ps(t1,t1,s1);
                    s2=_mm256_fmadd_ps(t2,t2,s2);s3=_mm256_fmadd_ps(t3,t3,s3);
                }
                __m256 sums[4]={s0,s1,s2,s3};
                for(int r=0;r<std::min(4,nq-qa);++r) {
                    auto& heap=h[qa+r];
                    float threshold=heap.size()==static_cast<size_t>(k)?heap.front().distance:INFINITY;
                    unsigned mask=_mm256_movemask_ps(_mm256_cmp_ps(sums[r],_mm256_set1_ps(threshold),_CMP_LE_OQ));
                    if(!mask)continue;
                    float lanes[8];_mm256_storeu_ps(lanes,sums[r]);
                    for(int l=0;l<8&&b+l<p.n;++l) if(mask&(1u<<l)) {
                        Hit v{lanes[l],b+l};
                        if(heap.size()<static_cast<size_t>(k)){heap.push_back(v);std::push_heap(heap.begin(),heap.end(),less_hit);}
                        else if(less_hit(v,heap.front())){std::pop_heap(heap.begin(),heap.end(),less_hit);heap.back()=v;std::push_heap(heap.begin(),heap.end(),less_hit);}
                    }
                }
            }
        for(int qi=0;qi<nq;++qi){std::sort_heap(h[qi].begin(),h[qi].end(),less_hit);for(int j=0;j<k;++j){ds[qi*k+j]=h[qi][j].distance;ids[qi*k+j]=h[qi][j].id;}}
        return 0;
    } catch(...) {return 1;}
}

