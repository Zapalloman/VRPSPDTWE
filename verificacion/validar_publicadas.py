import glob, os, sys, json
from evrp import *
H = sys.argv[1]
rows = []
for f in sorted(glob.glob(H + '/solution/akb/*.txt')) + sorted(glob.glob(H + '/solution/jd/*/*.txt')):
    base = os.path.basename(f).split('_timelimit')[0]
    inst = H + ('/data/akb_instances/' if '/akb/' in f else '/data/jd_instances/jd') + base + '.txt'
    I = read_instance(inst); R, T = read_solution(f)
    a = check_solution(I, R, T, use_reported=True)
    b = check_solution(I, R, T, use_reported=False)
    rows.append(dict(file=os.path.relpath(f, H), inst=I.name, K=a['K'], cost=round(a['cost'], 2), reported=T,
                     ok_reported=a['ok'], ok_recomputed=b['ok'], errors=a['errors'][:3] + b['errors'][:3]))
    print(rows[-1]['file'], a['ok'], b['ok'], a['errors'][:2], b['errors'][:2], flush=True)
json.dump(rows, open('validacion_publicadas.json', 'w'), indent=1, ensure_ascii=False)
print('total', len(rows), 'ok_reported', sum(r['ok_reported'] for r in rows), 'ok_recomputed', sum(r['ok_recomputed'] for r in rows))
