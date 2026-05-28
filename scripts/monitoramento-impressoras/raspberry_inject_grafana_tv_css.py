import json, urllib.request, socket, struct, os, base64, time
pages=json.load(urllib.request.urlopen('http://127.0.0.1:9222/json',timeout=10)); page=next(p for p in pages if p.get('type')=='page')
url=page['webSocketDebuggerUrl']; rest=url[5:]; hp,path=rest.split('/',1); path='/'+path; host,port=hp.split(':'); port=int(port)
s=socket.create_connection((host,port)); key=base64.b64encode(os.urandom(16)).decode(); s.sendall((f'GET {path} HTTP/1.1\r\nHost: {hp}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode()); s.recv(4096)
def send(o):
 data=json.dumps(o).encode(); h=bytearray([0x81]); n=len(data)
 if n<126: h.append(0x80|n)
 else: h+=bytes([0x80|126])+struct.pack('!H',n)
 m=os.urandom(4); h+=m; s.sendall(h+bytes(b^m[i%4] for i,b in enumerate(data)))
def recv():
 h=s.recv(2); n=h[1]&127
 if n==126: n=struct.unpack('!H',s.recv(2))[0]
 elif n==127: n=struct.unpack('!Q',s.recv(8))[0]
 m=s.recv(4) if h[1]&128 else b''; d=b''
 while len(d)<n: d+=s.recv(n-len(d))
 if m: d=bytes(b^m[i%4] for i,b in enumerate(d))
 return json.loads(d.decode(errors='replace'))
def cdp(method,params=None,seq=[0]):
 seq[0]+=1; send({'id':seq[0],'method':method,'params':params or {}})
 while True:
  r=recv()
  if r.get('id')==seq[0]: return r
css='''
* { scrollbar-width:none!important; }
*::-webkit-scrollbar { width:0!important; height:0!important; display:none!important; }
html, body, #reactRoot, .grafana-app, .main-view, #pageContent, [class*="page-"], [class*="canvas-content"] { width:100vw!important; height:100vh!important; min-height:100vh!important; max-height:100vh!important; overflow:hidden!important; contain:none!important; }
.scrollbar-view { width:100vw!important; height:100vh!important; min-height:100vh!important; max-height:100vh!important; overflow:hidden!important; contain:none!important; }
.react-grid-layout, .react-grid-item, .react-grid-layout--enable-move-animations { height:100vh!important; min-height:100vh!important; max-height:100vh!important; overflow:visible!important; contain:none!important; }
.react-grid-item { transform:none!important; top:0!important; left:0!important; width:100%!important; }
[class*="panel-content"], [class*="panel-container"], [class*="css-1juzzre"], [class*="markdown-html"] { height:100vh!important; min-height:100vh!important; max-height:100vh!important; overflow:visible!important; contain:none!important; }
.noc-printers { height:calc(100vh - 30px)!important; max-height:calc(100vh - 30px)!important; }
'''
expr=f'''(()=>{{let s=document.getElementById('grafana-tv-fit-override'); if(!s){{s=document.createElement('style'); s.id='grafana-tv-fit-override'; document.head.appendChild(s);}} s.textContent={json.dumps(css)}; return 'grafana-tv-css-ok';}})()'''
print(cdp('Runtime.evaluate',{'expression':expr,'returnByValue':True}).get('result',{}).get('result',{}).get('value'))
