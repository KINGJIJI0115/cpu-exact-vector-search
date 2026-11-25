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
