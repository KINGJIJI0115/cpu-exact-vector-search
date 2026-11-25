// First compute a shared prefix; refine only live queries in pairs with four accumulators.
template<int Prefix> int selective_search(Packed& p,const float* q,int nq,int k,int blocksize,float* ds,int* ids){
    std::vector<std::vector<Hit>> heaps(nq);for(auto& h:heaps)h.reserve(k);
    for(int ba=0;ba<p.n;ba+=blocksize)for(int qa=0;qa<nq;qa+=8)
      for(int b=ba;b<std::min(ba+blocksize,p.n);b+=8){
        __m256 partial[8];const float* qs[8];
        for(int r=0;r<8;++r){partial[r]=_mm256_setzero_ps();qs[r]=q+std::min(qa+r,nq-1)*p.d;}
        const float* base=p.a.data()+size_t(b/8)*p.d*8;int split=std::min(Prefix,p.d);
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
