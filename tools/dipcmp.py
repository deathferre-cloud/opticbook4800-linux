import sys, numpy as np
from PIL import Image
def load(p):
    try:
        import tifffile as tf; a=tf.imread(p).astype(float)
    except Exception:
        a=np.asarray(Image.open(p)).astype(float)
    if a.ndim==3: a=a.mean(2)
    return a.mean(0) if a.ndim==2 else a
cal=load(sys.argv[1])
s=np.asarray(Image.open(sys.argv[2])).astype(float)
if s.ndim==3: s=s[...,:3].mean(2)
sc=(s[300:1500].mean(0)/255.0)**1.7
def hp(v,w=401,sm=9):
    v=np.convolve(v,np.ones(sm)/sm,mode='same')
    tr=np.convolve(v,np.ones(w)/w,mode='same'); return v/np.maximum(tr,1e-9)
hc=hp(cal); hs=hp(sc)
print(f"== {sys.argv[1].split('/')[-1]}: {cal.size} px, шум {100*hc[3000:4000].std():.2f}%")
for c in (1501,6910):
    tmpl=hs[c-60:c+60]-1; best=None
    for sh in range(-150,450):
        seg=hc[c+sh-60:c+sh+60]-1
        cc=np.dot(tmpl,seg)/(np.linalg.norm(tmpl)*np.linalg.norm(seg)+1e-12)
        if best is None or cc>best[1]: best=(sh,cc)
    sh=best[0]
    ds=100*(hs[c-30:c+30].min()-1); dc=100*(hc[c+sh-30:c+sh+30].min()-1)
    ws=int((hs[c-60:c+60]<0.98).sum()); wc=int((hc[c+sh-60:c+sh+60]<0.98).sum())
    As=(1-hs[c-60:c+60]).clip(0).sum(); Ac=(1-hc[c+sh-60:c+sh+60]).clip(0).sum()
    print(f"px {c}: скан {ds:+.1f}% шир {ws} пл {As:.1f} | калибр сдвиг {sh:+d} корр {best[1]:.2f}: {dc:+.1f}% шир {wc} пл {Ac:.1f}")
    print("   профиль калибр: "+" ".join(f"{100*(hc[k:k+10].mean()-1):+.1f}" for k in range(c+sh-60,c+sh+60,10)))
