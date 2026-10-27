import csv, math
K_B = 8.617333262e-5

def estimate_ea(path):
    with open(path) as handle:
        rows = list(csv.DictReader(handle))
    x=[1/float(r['T']) for r in rows]
    y=[math.log(float(r['sigma'])) for r in rows]
    xm,ym=sum(x)/len(x),sum(y)/len(y)
    slope=sum((a-xm)*(b-ym) for a,b in zip(x,y))/sum((a-xm)**2 for a in x)
    return -K_B*slope
