"""Verifica feasible_fixed (O(n)) contra el PL de evrp.eval_route en rutas publicadas y perturbadas."""
import glob, os, random, sys, time
from frvcp import *
H = '/home/user/oe3/common/hma'
random.seed(1)
files = sorted(glob.glob(H + '/solution/akb/*.txt'))
n = agree = dis = 0; tl = tf = 0.0
for f in files:
    I = read_instance(H + '/data/akb_instances/' + os.path.basename(f).split('_timelimit')[0] + '.txt')
    R, _ = read_solution(f)
    for r in R:
        nodes = [x[0] for x in r]
        variants = [nodes]
        for _ in range(4):  # perturbaciones: quitar/insertar/cambiar una estación
            v = nodes[:]
            op = random.random()
            st = [k for k in range(1, len(v)-1) if I.typ[v[k]] == 'f']
            if op < 0.33 and st:
                del v[random.choice(st)]
            elif op < 0.66:
                v.insert(random.randint(1, len(v)-1), random.choice(I.stations))
            elif st:
                v[random.choice(st)] = random.choice(I.stations)
            if all(v[k] != v[k+1] for k in range(len(v)-1)):
                variants.append(v)
        for v in variants:
            for beta in (0.0, 0.2, 0.3):
                t0 = time.perf_counter(); a = eval_route(I, v, beta)['feasible']; tl += time.perf_counter()-t0
                t0 = time.perf_counter(); b = feasible_fixed(I, v, beta); tf += time.perf_counter()-t0
                n += 1
                if a == b: agree += 1
                else:
                    dis += 1
                    if dis <= 10: print('DESACUERDO', I.name, beta, v, 'PL', a, 'O(n)', b)
print(f'casos {n}, coinciden {agree}, discrepan {dis}; tiempo PL {tl:.1f}s, O(n) {tf:.3f}s')
