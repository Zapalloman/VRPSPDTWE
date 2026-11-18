import glob, os, sys, json, re, statistics as st
from evrp import *
H, RUNS = sys.argv[1], sys.argv[2]
def runs_of(f):
    vals = []
    for line in open(f):
        m = re.match(r"^\s*([\d.]+),\s*([\d.]+)\s*$", line)
        if m: vals.append((float(m.group(1)), float(m.group(2))))
    return vals
rows = []
for f in sorted(glob.glob(RUNS + '/*_timelimit=105_subproblem=1.txt')):
    base = os.path.basename(f).split('_timelimit')[0]
    pub = H + '/solution/akb/' + os.path.basename(f)
    I = read_instance(H + '/data/akb_instances/' + base + '.txt')
    R, T = read_solution(f); Rp, Tp = read_solution(pub)
    chk = check_solution(I, R, T, use_reported=False)
    loc, pv = runs_of(f), runs_of(pub)
    rows.append(dict(inst=base, n=len(I.customers), K_loc=len(R), K_pub=len(Rp),
                     best_loc=min(c for c, _ in loc), avg_loc=st.mean(c for c, _ in loc),
                     best_pub=min(c for c, _ in pv), avg_pub=st.mean(c for c, _ in pv),
                     t_loc=st.mean(t for _, t in loc), t_pub=st.mean(t for _, t in pv),
                     runs=len(loc), valid=chk['ok'], cost_chk=chk['cost']))
json.dump(rows, open('replica_akb_pequenas.json', 'w'), indent=1)
eq_best = sum(abs(r['best_loc'] - r['best_pub']) < 0.005 for r in rows)
eq_avg = sum(abs(r['avg_loc'] - r['avg_pub']) < 0.005 for r in rows)
better = [r['inst'] for r in rows if r['best_loc'] < r['best_pub'] - 0.005]
worse = [(r['inst'], r['best_loc'], r['best_pub']) for r in rows if r['best_loc'] > r['best_pub'] + 0.005]
print(len(rows), 'valid', sum(r['valid'] for r in rows), 'best=', eq_best, 'avg=', eq_avg, 'better', better, 'worse', worse)
for r in rows:
    if abs(r['avg_loc'] - r['avg_pub']) >= 0.005: print(r)
print('t_loc mean', st.mean(r['t_loc'] for r in rows), 't_pub', st.mean(r['t_pub'] for r in rows))
