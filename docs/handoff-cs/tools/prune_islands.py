# lanes and courts cut off from the network at any audited year (e.g. by the forum or a cistern) are given up
import json, sys, os
X = os.getcwd() + '/'
src = open(os.path.dirname(os.path.abspath(__file__)) + '/audit_streets.py').read()
head, rest = src.split('def audit(', 1)
exec(head.replace('sys.exit()', 'pass'))
exec('def audit(' + rest.split('\nR = ')[0].replace('    R = dict(year=Y', '    return [segs[i] for i in iso]\n    R = dict(year=Y'))
drop = set()
for Y in range(30, 75, 5):
    for q in audit(Y):
        if q[5] in ('l', 'c'): drop.add(tuple(q[:4]))
S2 = [q for q in S if tuple(q[:4]) not in drop]
print('islands pruned', len(S) - len(S2))
json.dump(S2, open(X + 'streets.json', 'w'), separators=(',', ':'))
