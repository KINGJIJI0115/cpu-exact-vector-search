#define VECTOR_SEARCH_LIBRARY
#include "benchmark.cpp"
#include <sys/resource.h>
int main(int argc,char** argv) {
    if(argc!=2) return 2;
    int mask=std::stoi(argv[1]);
    const int n=100000,nq=100,d=128,k=10;
    std::mt19937 rng(20261109);
    std::vector<float> x(static_cast<size_t>(n)*d),q(nq*d);
    for(auto& v:x) v=rng()%256;
    for(auto& v:q) v=rng()%256;
    rusage before{},after{}; getrusage(RUSAGE_SELF,&before);
    auto hits=mask==14?search_stream(x,q,n,nq,d,k,true,true,256):search(x,q,n,nq,d,k,true,true,true,256);
    getrusage(RUSAGE_SELF,&after);
    unsigned long long checksum=0;for(auto h:hits) checksum+=h.id;
    std::cout<<mask<<','<<before.ru_maxrss<<','<<after.ru_maxrss<<','<<checksum<<'\n';
}
