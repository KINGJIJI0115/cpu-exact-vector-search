"""Arithmetic obligations for byte dot/norm identity (not a compiled-code proof)."""
from pathlib import Path
import argparse,json
import z3

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False);rows=[]
 x,q,y,r=z3.Ints('x q y r');bounds=[v>=0 for v in [x,q,y,r]]+[v<=255 for v in [x,q,y,r]]
 identity=(x-q)*(x-q)+(y-r)*(y-r)-(x*x+y*y+q*q+r*r-2*(x*q+y*r))
 cases=[('integer_identity',[],z3.simplify(identity,som=True)!=0),('product_bound',bounds,z3.Or(x*q<0,x*q>65025)),('pair_dot_int32',bounds,z3.Or(x*q+y*r<0,x*q+y*r>130050)),('squared_difference_bound',bounds,z3.Or((x-q)*(x-q)<0,(x-q)*(x-q)>65025))]
 norm,dot,dist=z3.Ints('norm dot dist')
 cases += [('d128_intermediate_and_float_range',[norm>=0,norm<=128*65025,dot>=0,dot<=128*65025,dist>=0,dist<=128*65025],z3.Or(norm+norm>=2**31,2*dot>=2**31,norm+norm-2*dot<=-2**31,dist>2**24))]
 for name,assumptions,bad in cases:
  s=z3.Solver();s.set(timeout=30000);s.add(*assumptions,bad);result=s.check();(a.out/(name+'.smt2')).write_text(s.to_smt2());assert result==z3.unsat,(name,result);rows.append({'name':name,'result':str(result)})
 s=z3.Solver();s.add(*bounds,(x-q)*(x-q)+(y-r)*(y-r)!=x*x+y*y+q*q+r*r-(x*q+y*r));assert s.check()==z3.sat
 (a.out/'mutation_missing_factor_two.smt2').write_text(s.to_smt2());record={'status':'passed','z3':z3.get_version_string(),'proofs':rows,'mutation':'sat','counterexample':str(s.model()),'scope':'Exact integer algebra and conservative D=128 0..255 arithmetic bounds. Reduction induction uses bounded nonnegative terms. Does not verify SIMD lane layout, C++ compiler, memory safety, or machine code; those require independent regression.'}
 (a.out/'summary.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
if __name__=='__main__':main()
