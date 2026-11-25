"""Junta resultados/METODO/parte*/corridas.csv en resultados/METODO/corridas.csv."""
import sys, glob, os, csv
d = sys.argv[1]
rows, head = [], None
for f in sorted(glob.glob(os.path.join(d, 'parte*', 'corridas.csv'))):
    with open(f) as fh:
        r = list(csv.reader(fh))
    if not r: continue
    head = r[0]; rows += r[1:]
if head:
    with open(os.path.join(d, 'corridas.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(head); w.writerows(sorted(rows, key=lambda x: (x[1], int(x[3]))))
    print(len(rows), 'corridas ->', os.path.join(d, 'corridas.csv'))
