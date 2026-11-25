// Direct squared differences, no BLAS calls and no dot-product identity.
#define VECTOR_SEARCH_LIBRARY
#include "benchmark.cpp"
struct Packed {int n,d;std::vector<float> a;};
extern "C" void* packed_create(const float* x,int n,int d) {
    try {
        auto* p=new Packed{n,d,std::vector<float>(static_cast<size_t>((n+7)/8)*d*8)};
        for(int b=0;b<n;b+=8) for(int j=0;j<d;++j) for(int l=0;l<8;++l)
            p->a[static_cast<size_t>(b/8)*d*8+j*8+l]=b+l<n?x[static_cast<size_t>(b+l)*d+j]:0;
        return p;
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
        const float* base=p.a.data()+static_cast<size_t>(b/8)*p.d*8;
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
        const float* base=p.a.data()+static_cast<size_t>(b/8)*p.d*8;

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



// Bounded candidate buffer: stale thresholds only admit extra candidates.
struct BufferedTopK {
    int k;float limit=INFINITY;std::vector<Hit> items;
    explicit BufferedTopK(int count):k(count){items.reserve(size_t(k)*2);}
    void reduce(){
        std::nth_element(items.begin(),items.begin()+k,items.end(),less_hit);
        items.resize(k);limit=std::max_element(items.begin(),items.end(),less_hit)->distance;
    }
    void offer(Hit v){items.push_back(v);if(items.size()==size_t(k)*2)reduce();}
    void finish(){if(items.size()>size_t(k))reduce();std::sort(items.begin(),items.end(),less_hit);}
};
template<int R,int S> int buffer_search(Packed& p,const float* q,int nq,int k,int blocksize,float* ds,int* ids) {
    std::vector<BufferedTopK> heaps;heaps.reserve(nq);for(int i=0;i<nq;++i)heaps.emplace_back(k);
    for(int ba=0;ba<p.n;ba+=blocksize) for(int qa=0;qa<nq;qa+=R)
      for(int b=ba;b<std::min(ba+blocksize,p.n);b+=8) {
        __m256 acc[R][S];
        const float* queries[R];
        for(int r=0;r<R;++r){queries[r]=q+std::min(qa+r,nq-1)*p.d;for(int s=0;s<S;++s)acc[r][s]=_mm256_setzero_ps();}
        const float* base=p.a.data()+static_cast<size_t>(b/8)*p.d*8;
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
            auto& h=heaps[qa+r];float limit=h.limit;
            unsigned mask=_mm256_movemask_ps(_mm256_cmp_ps(sum,_mm256_set1_ps(limit),_CMP_LE_OQ));
            if(!mask)continue;float lanes[8];_mm256_storeu_ps(lanes,sum);
            for(int l=0;l<8&&b+l<p.n;++l)if(mask&(1u<<l)) {
                Hit v{lanes[l],b+l};
                h.offer(v);
            }
        }
      }
    for(int qi=0;qi<nq;++qi){auto& h=heaps[qi];h.finish();for(int j=0;j<k;++j){ds[qi*k+j]=h.items[j].distance;ids[qi*k+j]=h.items[j].id;}}
    return 0;
}
template<int C,int Start> int buffer_chunk_search(Packed& p,const float* q,int nq,int k,int blocksize,float* ds,int* ids) {
    constexpr int R=8,S=1;
    std::vector<BufferedTopK> heaps;heaps.reserve(nq);for(int i=0;i<nq;++i)heaps.emplace_back(k);
    for(int ba=0;ba<p.n;ba+=blocksize) for(int qa=0;qa<nq;qa+=R)
      for(int b=ba;b<std::min(ba+blocksize,p.n);b+=8) {
        __m256 acc[R][S];
        const float* queries[R];
        for(int r=0;r<R;++r){queries[r]=q+std::min(qa+r,nq-1)*p.d;for(int s=0;s<S;++s)acc[r][s]=_mm256_setzero_ps();}
        const float* base=p.a.data()+static_cast<size_t>(b/8)*p.d*8;

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
                    auto& h=heaps[qa+r];float limit=h.limit;
                    alive|=_mm256_movemask_ps(_mm256_cmp_ps(acc[r][0],_mm256_set1_ps(limit),_CMP_LE_OQ));
                }
                if(!alive){abandoned=true;break;}
            }
        }
        if(abandoned)continue;
        for(int r=0;r<std::min(R,nq-qa);++r) {
            __m256 sum=acc[r][0];for(int s=1;s<S;++s)sum=_mm256_add_ps(sum,acc[r][s]);
            auto& h=heaps[qa+r];float limit=h.limit;
            unsigned mask=_mm256_movemask_ps(_mm256_cmp_ps(sum,_mm256_set1_ps(limit),_CMP_LE_OQ));
            if(!mask)continue;float lanes[8];_mm256_storeu_ps(lanes,sum);
            for(int l=0;l<8&&b+l<p.n;++l)if(mask&(1u<<l)) {
                Hit v{lanes[l],b+l};
                h.offer(v);
            }
        }
      }
    for(int qi=0;qi<nq;++qi){auto& h=heaps[qi];h.finish();for(int j=0;j<k;++j){ds[qi*k+j]=h.items[j].distance;ids[qi*k+j]=h.items[j].id;}}
    return 0;
}


// Shape-only policy; no dataset names, timing probes or Faiss calls.
extern "C" int packed_route(int d,int nq,int k){return d==128 && nq>=128 && k>=1 && k<=10;}
extern "C" int packed_tuned(void* ptr,const float* q,int nq,int k,int mode,int block,float* ds,int* ids) {
    try {auto& p=*static_cast<Packed*>(ptr);if(nq<1||k<1||k>p.n||block<8||block%8)return 2;
        if(mode==9)return buffer_search<8,1>(p,q,nq,k,block,ds,ids);
        if(mode==10)return buffer_chunk_search<32,64>(p,q,nq,k,block,ds,ids);
        if(mode==7){
            if(packed_route(p.d,nq,k))return chunk_search<32,64>(p,q,nq,k,block,ds,ids);
            mode=6;
        }
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
                    __m256 x=_mm256_loadu_ps(p.a.data()+static_cast<size_t>(b/8)*p.d*8+j*8);
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

