import sys, numpy as np
from PIL import Image
p=sys.argv[1]; dpi=float(sys.argv[2])
a=np.asarray(Image.open(p)).astype(float)
if a.ndim==3: a=a[...,:3].mean(2)
s=a[a.shape[0]//4:a.shape[0]//4+300].mean(0); n=s.size
k=(int(2.0*dpi/25.4)|1)
tr=np.convolve(s,np.ones(k)/k,mode='same')
d=((s-tr)/tr)[int(30*dpi/25.4):n-int(10*dpi/25.4)]
print(f"{p.split('/')[-1]}: {n} px, рябь rms {100*d.std():.2f}%, размах {100*(d.max()-d.min()):.2f}%")
f=np.abs(np.fft.rfft(d*np.hanning(d.size))); fr=np.fft.rfftfreq(d.size)
for i in (np.argsort(f[3:])[::-1][:4]+3):
    per=1/fr[i]
    print(f"   период {per:8.2f} px = {per*25.4/dpi:6.3f} мм   амплитуда {f[i]/f[3:].max():.2f}")
