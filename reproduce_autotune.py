"""Default reproduction: calibrate on this host, freeze, compare all 78 cases."""
import argparse,datetime,json,os,shutil,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def decision(manifest=None):
    if manifest is None:return dict(status='not_evaluated',target_met=None,cases=0,passed=None)
    assert manifest['status']=='completed' and manifest['cases']==78 and manifest['correct_cases']==78
    return dict(status='evaluated',target_met=manifest['passed']==78,cases=78,passed=manifest['passed'],geomean=manifest['gain_geomean'])

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cpu',type=int,help='One allowed logical CPU; defaults to the lowest allowed CPU')
    ap.add_argument('--quick',action='store_true',help='Build and correctness/formal tests only; no full calibration or performance claim')
    ap.add_argument('--require-performance-target',action='store_true',help='After all outputs, exit 3 unless all 78 cases meet performance target')
    a=ap.parse_args()
    if a.quick and a.require_performance_target:ap.error('Quick mode has no full performance target')
    allowed=os.sched_getaffinity(0);cpu=a.cpu if a.cpu is not None else min(allowed)
    if cpu not in allowed:ap.error('CPU outside allowed affinity')
    os.sched_setaffinity(0,{cpu});os.nice(10)
    base=ROOT/'baseline';auto=ROOT/'autotune_v2'
    out=ROOT/'results'/('autotune_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir(parents=True)
    env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_CORETYPE='Haswell',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    steps=[];start=time.perf_counter()
    def step(label,script,args=(),deps=False,cwd=None):
        e=env.copy();e.pop('PYTHONPATH',None)
        if deps:e['PYTHONPATH']=str(base/'.deps')
        cmd=[sys.executable,str(script),*map(str,args)];print('RUN',label,flush=True)
        t=time.perf_counter()
        with (out/(label+'.log')).open('w') as f:p=subprocess.run(cmd,cwd=cwd or script.parent,env=e,stdout=f,stderr=subprocess.STDOUT)
        steps.append(dict(step=label,command=cmd,exit=p.returncode,seconds=time.perf_counter()-t))
        (out/'steps.json').write_text(json.dumps(steps,indent=2))
        if p.returncode:raise RuntimeError(f'{label} failed; see {out/(label+".log")}')
    try:
        step('environment',base/'check_environment.py',['--json',out/'environment.json'])
        step('adaptive_regression',auto/'test_adaptive.py',deps=True)
        # Replay formal checks in a separate directory, preserving historical baseline results.
        formal=out/'formal';formal.mkdir()
        for name in ['formal_verify.py','formal_verify_byte.py']:
            shutil.copy2(base/name,formal/name);step(name,formal/name)
        step('formal_dot',ROOT/'experiments/v2/formal_dot.py',['--out',out/'formal_dot'])
        step('prepare_siftsmall',base/'prepare_data.py',deps=True)
        step('siftsmall_regression',auto/'check_siftsmall.py',['--data',base/'data','--out',out/'siftsmall_correctness.json','--cpu',cpu],True)
        if a.quick:
            perf=decision()
        else:
            for name in ['prepare_data.py','prepare_sift1m.py','prepare_glove.py']:step(name,base/name,deps=True)
            old=set((auto/'results').glob('calibration_*'))
            profile=auto/'profiles/local.json'
            step('calibrate',auto/'calibrate.py',['--data',base/'data','--cpu',cpu,'--profile',profile],True)
            created=set((auto/'results').glob('calibration_*'))-old;assert len(created)==1
            cal=created.pop();record=json.loads((cal/'SUCCESS.json').read_text());assert record['configs']==26 and record['full_scope']
            shutil.copytree(cal,out/'calibration');shutil.copy2(profile,out/'selected_profile.json')
            step('faiss78',auto/'compare_faiss78_portable.py',['--base',base,'--out',out/'confirmation','--cpu',cpu,'--profile',profile],True)
            manifest=json.loads((out/'confirmation/manifest.json').read_text());perf=decision(manifest)
        report=out/'report';report.mkdir()
        scope='短验收：完成v2编译、候选与缓存回归、48项SIFTsmall功能检查、原有及新增整数内积形式化验证；完整26配置校准与78项性能比较由完整模式执行。' if a.quick else f'本机完成 26 配置校准或复用，并冻结选择完成 78 项同轮比较；正确性 78/78，性能胜出 {perf["passed"]}/78，几何平均加速比 {perf["geomean"]:.4f} 倍。'
        text=f'# 本机v2自动校准版复现报告\n\n{scope}\n\n逻辑 CPU：{cpu}；搜索及 Faiss/BLAS 均为单线程。本报告记录当前机器的实际运行结果。\n\n'
        if not a.quick:
            import csv
            rows=list(csv.DictReader((out/'confirmation/summary.csv').open()))
            text+='校准与数据准备耗时见 steps.json。下表记录常驻索引上的完整查询耗时。\n\n| 配置/批次 | 新版 ms | 最快 Faiss ms | 加速比 | 通过 |\n|---|---|---|---|---|\n'
            for r in rows:text+=f'| {r["label"]} | {float(r["custom_ms"]):.3f} | {float(r["best_faiss_ms"]):.3f} | {float(r["gain"]):.3f} | {r["passed"]} |\n'
        text+='\n所有执行步骤见上级 steps.json 和日志。\n\n补充：性能表使用确认测试前选定的内核，所有配置均保留。数据准备和校准属于一次性成本，程序整体收益取决于实际查询次数；快速模式仅提供功能验收结果。\n'
        (report/'reproduction_report.md').write_text(text,encoding='utf-8')
        render_env=env.copy();render_env.update(VECTOR_REPORT_DIR=str(report),VECTOR_REPORT_STEM='reproduction_report',VECTOR_REPORT_TITLE='本机v2自动校准版复现报告')
        subprocess.run([sys.executable,str(ROOT/'packaging/render_report.py')],env=render_env,check=True)
        result=dict(status='passed',execution_status='completed',correctness_status='passed',mode='quick' if a.quick else 'full',cpu=cpu,performance=perf,total_seconds=time.perf_counter()-start)
        (out/'performance.json').write_text(json.dumps(perf,indent=2));(out/'SUCCESS.json').write_text(json.dumps(result,indent=2))
        archive=out/'reproduction_evidence.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for p in out.rglob('*'):
                if p.is_file() and p!=archive and '.oracle_cache' not in p.parts:z.write(p,p.relative_to(out))
        print(out,flush=True)
        return 3 if a.require_performance_target and not perf['target_met'] else 0
    except Exception as exc:
        (out/'SUCCESS.json').unlink(missing_ok=True)
        (out/'FAILED.json').write_text(json.dumps(dict(status='failed',error=str(exc),steps=steps),indent=2))
        print(str(exc),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
