"""Compara corridas.csv de dos o más métodos (juez oficial) por instancia y en agregado."""
import csv, sys, collections, statistics as st
paths = sys.argv[1:]
data = {}
for p in paths:
    for r in csv.DictReader(open(p)):
        data.setdefault(r['metodo'], {}).setdefault(r['instancia'], {})[int(r['semilla'])] = r
mets = list(data)
insts = sorted(set.intersection(*[set(data[m]) for m in mets]), key=lambda k: ('_21' in k, k))
print('| instancia | ' + ' | '.join(f'{m}: fact / K medio / TC medio (mín)' for m in mets) + ' |')
print('|---|' + '---|' * len(mets))
agg = {m: collections.defaultdict(list) for m in mets}
for i in insts:
    seeds = sorted(set.intersection(*[set(data[m][i]) for m in mets]))
    row = [i]
    for m in mets:
        rs = [data[m][i][s] for s in seeds]
        f = [r for r in rs if r['factible'] == '1']
        tc = [float(r['costo_TC']) for r in f]
        K = [int(r['K']) for r in f]
        row.append(f"{len(f)}/{len(rs)} / {st.mean(K):.2f} / {st.mean(tc):.2f} ({min(tc):.2f})" if f else f"0/{len(rs)}")
        g = 'grandes' if '_21' in i else 'pequeñas'
        agg[m][g + '_fact'].append(len(f)); agg[m][g + '_n'].append(len(rs))
        agg[m][g + '_K'] += K; agg[m][g + '_tc'] += tc
        agg[m][g + '_t'] += [float(r['tiempo_pared']) for r in rs]
    print('| ' + ' | '.join(row) + ' |')
print()
for g in ('pequeñas', 'grandes'):
    for m in mets:
        a = agg[m]
        if not a[g + '_n']: continue
        print(f"{g} {m}: factibles {sum(a[g+'_fact'])}/{sum(a[g+'_n'])}, K medio {st.mean(a[g+'_K']):.3f}, "
              f"TC medio {st.mean(a[g+'_tc']):.2f}, tiempo medio {st.mean(a[g+'_t']):.1f}s")
# comparación pareada (misma instancia y semilla, ambas factibles)
if len(mets) >= 2:
    A, B = mets[0], mets[1]
    for g in ('pequeñas', 'grandes'):
        d, w, l, kA, kB = [], 0, 0, 0, 0
        for i in insts:
            if (g == 'grandes') != ('_21' in i): continue
            for s in set(data[A][i]) & set(data[B][i]):
                ra, rb = data[A][i][s], data[B][i][s]
                if ra['factible'] == rb['factible'] == '1':
                    x, y = float(ra['costo_TC']), float(rb['costo_TC'])
                    d.append((y - x) / x * 100); w += y < x - 1e-6; l += y > x + 1e-6
                    kA += int(ra['K']); kB += int(rb['K'])
        if d:
            print(f"{g}: {B} vs {A} en {len(d)} pares factibles: Δ TC medio {st.mean(d):+.3f} %, {B} mejor en {w}, peor en {l}; K total {kA} -> {kB}")
