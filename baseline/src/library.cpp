// Reuse the exact implementation measured by benchmark.cpp.
#define VECTOR_SEARCH_LIBRARY
#include "benchmark.cpp"
struct Database { std::vector<float> x; int n,d; };
extern "C" {
// Merge a BLAS-produced dot-product tile into sorted per-query top-K outputs.
// Norms and dot products must be finite. Distances use the standard L2 identity.
int vs_merge_tile(const float* dots,const float* xn,const float* qn,int nq,int nb,int offset,int k,int mode,float* ds,int* ids) {
    try {
        if(nq<1||nb<1||k<1||offset<0||(mode<0||mode>2)) return 2;
        std::vector<Hit> work;work.reserve(static_cast<size_t>(k)+(mode==1?nb:0));
        for(int qi=0;qi<nq;++qi) {
            work.clear();
            for(int j=0;j<k;++j) work.push_back({ds[qi*k+j],ids[qi*k+j]});
            if(mode!=1) std::make_heap(work.begin(),work.end(),less_hit);
            int xi=0;
            if(!mode) for(;xi+8<=nb;xi+=8) {
                __m256 dot=_mm256_loadu_ps(dots+static_cast<size_t>(qi)*nb+xi);
                __m256 dist=_mm256_max_ps(_mm256_setzero_ps(),_mm256_sub_ps(
                    _mm256_add_ps(_mm256_set1_ps(qn[qi]),_mm256_loadu_ps(xn+xi)),
                    _mm256_mul_ps(_mm256_set1_ps(2.0f),dot)));
                unsigned mask=_mm256_movemask_ps(_mm256_cmp_ps(dist,_mm256_set1_ps(work.front().distance),_CMP_LE_OQ));
                if(!mask) continue;
                float lanes[8];_mm256_storeu_ps(lanes,dist);
                for(int lane=0;lane<8;++lane) if(mask&(1u<<lane)) {
                    Hit h{lanes[lane],offset+xi+lane};
                    if(less_hit(h,work.front())) {
                        std::pop_heap(work.begin(),work.end(),less_hit);work.back()=h;
                        std::push_heap(work.begin(),work.end(),less_hit);
                    }
                }
            }
            for(;xi<nb;++xi) {
                Hit h{std::max(0.0f,qn[qi]+xn[xi]-2.0f*dots[static_cast<size_t>(qi)*nb+xi]),offset+xi};
                if(mode==1) work.push_back(h);
                else if(less_hit(h,work.front())) {
                    std::pop_heap(work.begin(),work.end(),less_hit);work.back()=h;
                    std::push_heap(work.begin(),work.end(),less_hit);
                }
            }
            if(mode==1) {std::nth_element(work.begin(),work.begin()+k,work.end(),less_hit);work.resize(k);}
            std::sort(work.begin(),work.end(),less_hit);
            for(int j=0;j<k;++j) {ds[qi*k+j]=work[j].distance;ids[qi*k+j]=work[j].id;}
        }
        return 0;
    } catch(...) {return 1;}
}
void* vs_create(const float* x,int n,int d) {
    try { return new Database{std::vector<float>(x,x+static_cast<size_t>(n)*d),n,d}; }
    catch(...) { return nullptr; }
}
void vs_destroy(void* ptr) { delete static_cast<Database*>(ptr); }
int vs_search(void* ptr,const float* queries,int nq,int k,int mask,int block,float* distances,int* ids) {
    try {
        auto& db=*static_cast<Database*>(ptr);
        if(nq<1||k<1||k>db.n||block<1) return 2;
        std::vector<float> q(queries,queries+static_cast<size_t>(nq)*db.d);
        auto result=(mask&8)?search_stream(db.x,q,db.n,nq,db.d,k,mask&2,mask&4,block):search(db.x,q,db.n,nq,db.d,k,mask&1,mask&2,mask&4,block);
        for(size_t i=0;i<result.size();++i) { distances[i]=result[i].distance; ids[i]=result[i].id; }
        return 0;
    } catch(...) { return 1; }
}
}

