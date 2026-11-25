#define VECTOR_SEARCH_LIBRARY
#include "benchmark.cpp"
#include <sys/resource.h>
int main(int argc,char** argv) {
    if(argc!=3) return 2;
    auto x=read_vectors(argv[1],10000,128),q=read_vectors(argv[2],100,128);
    std::cout<<"repeat,variant,allocation_ms,distance_ms,selection_ms,process_peak_rss_kib\n";
    std::vector<int> order={0,1,5,7}; std::mt19937 rng(20261109);
    for(int rep=-1;rep<21;++rep) {
        std::shuffle(order.begin(),order.end(),rng);
        for(int mask:order) {
            double phases[3];
            auto out=search(x,q,10000,100,128,10,mask&1,mask&2,mask&4,256,phases);
            if(out.size()!=1000) return 1;
            rusage usage{}; getrusage(RUSAGE_SELF,&usage);
            if(rep>=0) std::cout<<rep<<','<<mask<<','<<phases[0]<<','<<phases[1]<<','<<phases[2]<<','<<usage.ru_maxrss<<'\n';
        }
    }
}
