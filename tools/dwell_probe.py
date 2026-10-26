import subprocess, time, zmq, numpy as np, threading
ctx=zmq.Context(); s=ctx.socket(zmq.SUB); s.connect('tcp://127.0.0.1:9101')
s.setsockopt(zmq.SUBSCRIBE,b''); s.setsockopt(zmq.RCVTIMEO,300)
audio={}
def pump():
    while time.time()-t0 < 52:
        try: raw=s.recv()
        except zmq.Again: continue
        a=np.frombuffer(raw,dtype=np.float32)
        if len(a)==0: continue
        r=float(np.sqrt(np.mean(a**2)))
        b=int((time.time()-t0)*2)
        d=20*np.log10(r) if r>1e-9 else -120
        cur=audio.get(b,-200)
        audio[b]=max(cur,d)
t0=time.time()
threading.Thread(target=pump,daemon=True).start()
rows=[]
while time.time()-t0 < 52:
    out=subprocess.run(['ss','-tn'],capture_output=True,text=True).stdout
    sq=0
    for ln in out.splitlines():
        if '127.0.0.1:7001' in ln and 'LISTEN' not in ln:
            p=ln.split()
            try:
                if p[3].endswith(':7001'): sq=max(sq,int(p[2]))
            except: pass
    rows.append((round(time.time()-t0,1), sq))
    time.sleep(0.5)
print(f'{"t(s)":>6} {"SendQ":>8} {"audio dBFS":>11}')
for t,sq in rows:
    b=int(t*2); a=audio.get(b,None)
    print(f'{t:6.1f} {sq:8d} {("%.1f"%a) if a is not None and a>-190 else "   --":>11}')
