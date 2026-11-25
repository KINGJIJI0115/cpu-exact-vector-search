"""Arithmetic bounds for lossless byte SIMD; not a proof of compiled C++."""
import datetime,json
from pathlib import Path
import z3
r=Path(__file__).resolve().parent;out=r/'results'/('formal_byte_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir()
x,q,u,v,d,total,term=z3.Ints('x q u v d total term')
obligations=[
 ('signed16_difference',[x>=0,x<=255,q>=0,q<=255,z3.Or(x-q < -32768,x-q>32767)]),
 ('pair_square_bound',[u>=-255,u<=255,v>=-255,v<=255,z3.Or(u*u+v*v<0,u*u+v*v>130050)]),
 ('int32_and_exact_float_output',[d>=1,d<=258,total>=0,total<=(d-1)*65025,term>=0,term<=65025,z3.Or(total+term<0,total+term>=2**24)]),
 ('odd_dimension_padding',[total>=0,total<=2**24,total+(0-0)*(0-0)!=total]),
]
results=[]
for name,assertions in obligations:
 solver=z3.Solver();solver.set(timeout=30000);solver.add(*assertions);(out/(name+'.smt2')).write_text(solver.to_smt2());answer=str(solver.check());assert answer=='unsat',(name,answer)
 results.append(dict(name=name,result=answer))
result=dict(z3=z3.get_version_string(),obligations=results,scope='Integer range and padding lemmas under checked 0..255 integral coordinates and d<=258. IEEE float32 represents all integer sums below 2^24. Does not verify the C++ implementation, memory layout, intrinsics lowering, or machine code.')
(out/'manifest.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));print(out)
