import sys, numpy as np
from PIL import Image
p=sys.argv[1]; dpi=float(sys.argv[2])
a=np.asarray(Image.open(p)).astype(float)
if a.ndim==3: a=a[...,:3].mean(2)
s=a[a.shape[0]//4:a.shape[0]//4+300].mean(0)
print(f"{p.split('/')[-1]}:")
for lo,hi in [(5,15),(20,40),(60,100),(120,200)]:
    q=s[int(lo*dpi/25.4):int(hi*dpi/25.4)]
    o,e=q[1::2].mean(),q[::2].mean()
    print(f"  {lo:3d}-{hi:3d} мм  нечёт {o:6.1f}  чёт {e:6.1f}  разница {100*(o/e-1):+5.2f}%")
