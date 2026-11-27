#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
#include <immintrin.h>
#include <fstream>

std::vector<float> read_vectors(const std::string& path,int count,int dimension) {
    std::ifstream f(path,std::ios::binary);
    if(!f) throw std::runtime_error("cannot open "+path);
    std::vector<float> data(static_cast<size_t>(count)*dimension);
    for(int i=0;i<count;++i) {
        int dim=0; f.read(reinterpret_cast<char*>(&dim),4);
        if(dim!=dimension) throw std::runtime_error("fvecs dimension mismatch");
        f.read(reinterpret_cast<char*>(data.data()+static_cast<size_t>(i)*dimension),4*dimension);
        if(!f) throw std::runtime_error("truncated fvecs");
    }
    return data;
}

struct Hit { float distance; int id; };
bool less_hit(const Hit& a, const Hit& b) {
    return a.distance < b.distance || (a.distance == b.distance && a.id < b.id);
}
float scalar(const float* a, const float* b, int d) {
    float sum = 0;
    for (int j=0;j<d;++j) { float delta=a[j]-b[j]; sum+=delta*delta; }
    return sum;
}
float simd(const float* a, const float* b, int d) {
    __m256 sum=_mm256_setzero_ps(); int j=0;
    for (;j+8<=d;j+=8) {
        __m256 x=_mm256_sub_ps(_mm256_loadu_ps(a+j),_mm256_loadu_ps(b+j));
        sum=_mm256_add_ps(sum,_mm256_mul_ps(x,x));
    }
    float lanes[8]; _mm256_storeu_ps(lanes,sum);
    float result=0; for (float v:lanes) result+=v;
    for (;j<d;++j) { float x=a[j]-b[j]; result+=x*x; }
    return result;
}
// Retain only K candidates per query. The heap front is the worst retained hit.
std::vector<Hit> search_stream(const std::vector<float>& x,const std::vector<float>& q,
                             int n,int nq,int d,int k,bool blocked,bool vectorized,int block) {
    std::vector<Hit> out(static_cast<size_t>(nq)*k);
    std::vector<std::vector<Hit>> heaps(nq);
    for(auto& h:heaps) h.reserve(k);
    auto distance=vectorized?simd:scalar;
    int qb=blocked?8:1, xb=blocked?block:n;
    for(int qa=0;qa<nq;qa+=qb)
        for(int xa=0;xa<n;xa+=xb)
            for(int qi=qa;qi<std::min(qa+qb,nq);++qi) {
                auto& h=heaps[qi];
                for(int xi=xa;xi<std::min(xa+xb,n);++xi) {
                    Hit candidate{distance(q.data()+static_cast<size_t>(qi)*d,x.data()+static_cast<size_t>(xi)*d,d),xi};
                    if(h.size()<static_cast<size_t>(k)) {
                        h.push_back(candidate); std::push_heap(h.begin(),h.end(),less_hit);
                    } else if(less_hit(candidate,h.front())) {
                        std::pop_heap(h.begin(),h.end(),less_hit); h.back()=candidate;
                        std::push_heap(h.begin(),h.end(),less_hit);
                    }
                }
            }
    for(int qi=0;qi<nq;++qi) {
        auto& h=heaps[qi]; std::sort_heap(h.begin(),h.end(),less_hit);
        std::copy(h.begin(),h.end(),out.begin()+static_cast<size_t>(qi)*k);
    }
    return out;
}
std::vector<Hit> search(const std::vector<float>& x, const std::vector<float>& q,
                       int n,int nq,int d,int k,bool partial,bool blocked,bool vectorized,int block,double* phases=nullptr) {
    using Clock=std::chrono::steady_clock;
    auto t0=phases?Clock::now():Clock::time_point{};
    std::vector<Hit> out(nq*k), work(static_cast<size_t>(n)*nq);
    auto t1=phases?Clock::now():Clock::time_point{};
    auto distance=vectorized ? simd : scalar;
    const int qb=blocked ? 8 : 1;
    const int xb=blocked ? block : n;
    for (int qa=0;qa<nq;qa+=qb)
        for (int xa=0;xa<n;xa+=xb)
            for (int qi=qa;qi<std::min(qa+qb,nq);++qi)
                for (int xi=xa;xi<std::min(xa+xb,n);++xi)
                    work[static_cast<size_t>(qi)*n+xi]={distance(q.data()+qi*d,x.data()+xi*d,d),xi};
    auto t2=phases?Clock::now():Clock::time_point{};
    for (int qi=0;qi<nq;++qi) {
        auto begin=work.begin()+static_cast<size_t>(qi)*n, end=begin+n;
        if (partial && k<n) std::nth_element(begin,begin+k,end,less_hit);
        std::sort(begin,partial ? begin+k : end,less_hit);
        std::copy(begin,begin+k,out.begin()+qi*k);
    }
    if(phases) {
        auto t3=Clock::now();
        phases[0]=std::chrono::duration<double,std::milli>(t1-t0).count();
        phases[1]=std::chrono::duration<double,std::milli>(t2-t1).count();
        phases[2]=std::chrono::duration<double,std::milli>(t3-t2).count();
    }
    return out;
}
#ifndef VECTOR_SEARCH_LIBRARY
int main(int argc,char** argv) {
    try {
        int n=argc>1?std::stoi(argv[1]):10000,nq=argc>2?std::stoi(argv[2]):32;
        int d=argc>3?std::stoi(argv[3]):128,k=argc>4?std::stoi(argv[4]):10;
        int repeats=argc>5?std::stoi(argv[5]):5,block=argc>6?std::stoi(argv[6]):256;
        if(n<1||nq<1||d<1||k<1||k>n||repeats<1||block<1) throw std::runtime_error("invalid arguments");
        std::mt19937 rng(20261109);
        std::vector<float> x(static_cast<size_t>(n)*d),q(static_cast<size_t>(nq)*d);
        // Integer mapping avoids implementation-dependent normal distributions.
        for(auto& v:x) v=float(int(rng()%20001)-10000)/10000;
        for(auto& v:q) v=float(int(rng()%20001)-10000)/10000;
        if(argc==8 && std::string(argv[7])=="--duplicates") {
            std::fill(x.begin(),x.end(),1.0f); std::fill(q.begin(),q.end(),1.0f);
        }
        if(argc>8) { x=read_vectors(argv[7],n,d); q=read_vectors(argv[8],nq,d); }
        auto reference=search(x,q,n,nq,d,k,false,false,false,block);
        // Independent double-precision distance and full-sort oracle, outside timing.
        for(int qi=0;qi<nq;++qi) {
            std::vector<std::pair<double,int>> oracle;
            for(int xi=0;xi<n;++xi) {
                double value=0;
                for(int j=0;j<d;++j) {
                    double delta=double(q[qi*d+j])-double(x[xi*d+j]); value+=delta*delta;
                }
                oracle.emplace_back(value,xi);
            }
            std::sort(oracle.begin(),oracle.end());
            for(int rank=0;rank<k;++rank) {
                const auto& actual=reference[qi*k+rank];
                if(actual.id!=oracle[rank].second || std::abs(actual.distance-oracle[rank].first)>1e-4*(1+oracle[rank].first))
                    throw std::runtime_error("double oracle differs; investigate ties or precision");
            }
        }
        std::cout<<"n,nq,d,k,block,repeat,variant,ms,queries_per_second,max_distance_error,topk_match\n";
        std::vector<int> order={0,1,2,3,4,5,6,7,8,12,14};
        for(int rep=-1;rep<repeats;++rep) {
            std::shuffle(order.begin(),order.end(),rng);
            for(int mask:order) {
                auto start=std::chrono::steady_clock::now();
                auto result=(mask&8)?search_stream(x,q,n,nq,d,k,mask&2,mask&4,block):search(x,q,n,nq,d,k,mask&1,mask&2,mask&4,block);
                double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
                double error=0; bool match=true;
                for(size_t i=0;i<result.size();++i) {
                    error=std::max(error,double(std::abs(result[i].distance-reference[i].distance)));
                    match &= result[i].id==reference[i].id;
                    if(std::abs(result[i].distance-reference[i].distance)>1e-4*(1+reference[i].distance))
                        throw std::runtime_error("distance validation failed");
                }
                if(!match) throw std::runtime_error("Top-K IDs differ: investigate numerical ties");
                if(rep>=0) std::cout<<n<<','<<nq<<','<<d<<','<<k<<','<<block<<','<<rep<<','<<mask<<','<<ms<<','<<nq*1000/ms<<','<<error<<",1\n";
            }
        }
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
    return 0;
}
#endif
