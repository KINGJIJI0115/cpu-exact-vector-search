"""Bounded SMT proof of the abstract streaming Top-K transition, not C++/FP verification."""
import datetime,json,hashlib
from pathlib import Path
import z3
root=Path(__file__).resolve().parent
out=root/'results'/('formal_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir(parents=True)
def insert(values,x):
    result=[]
    for value in values:
        result.append(z3.If(x<value,x,value));x=z3.If(x<value,value,x)
    return result+[x]
records=[]
for n in range(1,9):
    for k in range(1,n+1):
        keys=z3.Reals(' '.join(f'x{i}' for i in range(n)))
        retained=[]
        for x in keys:retained=insert(retained,x)[:k]
        # Independent specification: kth order statistic as exact count below each result.
        constraints=[z3.Distinct(keys)]
        correct=[]
        for rank,value in enumerate(retained):
            correct += [z3.Or([value==x for x in keys]),
                        z3.Sum([z3.If(x<value,1,0) for x in keys])==rank]
        solver=z3.Solver();solver.set(timeout=30000)
        solver.add(*constraints,z3.Not(z3.And(correct)))
        name=f'n{n}_k{k}';(out/(name+'.smt2')).write_text(solver.to_smt2())
        result=solver.check();records.append({'n':n,'k':k,'negated_property':str(result)})
        if result!=z3.unsat:raise RuntimeError(f'{name}: {result}')
# Non-vacuity and mutation: keeping largest instead of smallest must yield a counterexample.
a,b=z3.Reals('a b');mutant=z3.If(a>b,a,b)
solver=z3.Solver();solver.add(a!=b,z3.Or(mutant>a,mutant>b))
assert solver.check()==z3.sat
mutation=str(solver.model())
report={'z3':z3.get_version_string(),'scope':'All distinct real order keys for 1<=N<=8 and every 1<=K<=N; rank abstraction of lexicographic (finite distance, unique ID). No bound on numeric magnitude.',
        'exclusions':'Does not verify C++ heap library, SIMD floating arithmetic, memory safety or arbitrary N. Sorting retained set abstracts heap implementation.',
        'checks':records,'mutation_expected_sat':mutation,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(out/'verification.json').write_text(json.dumps(report,indent=2));print(f'{len(records)} UNSAT proofs; mutation SAT');print(out)
