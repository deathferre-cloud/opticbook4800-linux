import sys, numpy as np
from PIL import Image
p=sys.argv[1]; dpi=float(sys.argv[2]); px=25.4/dpi
a=np.asarray(Image.open(p)).astype(float)
if a.ndim==3: a=a[...,:3].mean(2)
h=a.shape[0]
mid=a[:,int(100/px):int(150/px)]
for y0,y1 in [(10,40),(90,120),(180,210),(255,285)]:
    r0,r1=int(y0/px),int(y1/px)
    if r1>h: continue
    b=a[r0:r1]; m=b[:,int(100/px):int(150/px)].mean()
    out=[]
    for mm in range(0,40,2):
        v=b[:,int(mm/px):int((mm+2)/px)].mean()
        out.append(f"{mm}:{v:.0f}({100*((v/m)**1.7-1):+.0f}%)")
    print(f"y {y0}-{y1} мм  середина {m:.1f}")
    print("  "+" ".join(out))
