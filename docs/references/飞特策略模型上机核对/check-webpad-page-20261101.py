"""Open/read web-gamepad session state; never acquire driving or send movement."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import websockets

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('webpad-page-status-20261101.json')
record = {'date':'2026-11-01','captured_at_utc':datetime.now(timezone.utc).isoformat(),
          'scope':'Heartbeat, read-only watch and drive open only; no lease acquisition, stand or movement',
          'sent':[],'messages':[]}

async def main():
    async with asyncio.timeout(20):
        async with websockets.connect('ws://192.168.1.35:8000/ws',origin='http://192.168.1.35:8000',
                                      max_size=4*1024*1024,open_timeout=5) as ws:
            for msg in [{'t':'hb','seq':1,'visible':True,'route':'/pad','pad_visible':True},
                        {'t':'cmd','id':'webpad-open-check','name':'pad.op','args':{'op':'drive','open':True,'seq':1}},
                        {'t':'cmd','id':'webpad-watch-check','name':'pad.op','args':{'op':'watch'}}]:
                await ws.send(json.dumps(msg)); record['sent'].append(msg)
            seen = set()
            while True:
                msg = json.loads(await ws.recv())
                if msg.get('t') == 'state':
                    record['state'] = msg
                elif msg.get('t') == 'pad':
                    record['pad'] = msg
                elif msg.get('t') == 'result':
                    record['messages'].append(msg)
                    if msg.get('id') in ['webpad-open-check','webpad-watch-check']:
                        seen.add(msg['id'])
                        assert msg.get('ok') is True, msg
                if len(seen)==2 and record.get('state') and record.get('pad'):
                    break
    record['status'] = 'web-gamepad session open and status received; no movement command'

try:
    asyncio.run(main())
finally:
    OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':record.get('status'),'results':record['messages'],
                  'pad':record.get('pad')},ensure_ascii=False,indent=2))
