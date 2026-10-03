# -*- coding: utf-8 -*-
"""隧道端到端临时测试:文本 / 轮询 / 分块上传 经 Cloudflare 回环。"""
import json
import os
import time
import urllib.error
import urllib.request

from channels import TunnelManager
from mobile_page import PAGE_HTML
from server import LiteDropServer, TransferState

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Ev:
    def __getattr__(self, n):
        return lambda *a: None


def main():
    st = TransferState('.')
    srv = LiteDropServer(8765, st, Ev(), PAGE_HTML)
    srv.start()
    tm = TunnelManager(on_log=lambda m: print('[log]', m),
                       on_url=lambda u: None, on_state=lambda s: None)
    tm.start(8765)
    while not tm.url:
        time.sleep(2)
    url = tm.url
    print('TUNNEL:', url)
    for i in range(12):
        time.sleep(4)
        try:
            r = opener.open(url + '/', timeout=10)
            print('页面:', r.status, '| X-LiteDrop:', r.headers.get('X-LiteDrop'))
            break
        except urllib.error.HTTPError as e:
            print('页面:', e.code, '| X-LiteDrop:', e.headers.get('X-LiteDrop'))
            break
        except Exception:
            continue

    k = st.token
    try:
        req = urllib.request.Request(
            url + '/api/text',
            data=json.dumps({'text': 'tunnel test'}).encode(),
            headers={'X-Auth': k, 'Content-Type': 'application/json'},
            method='POST')
        print('POST /api/text:', opener.open(req, timeout=20).read())
    except urllib.error.HTTPError as e:
        print('POST /api/text:', e.code, e.read(300))
    except Exception as e:
        print('POST /api/text 异常:', type(e).__name__, e)

    try:
        d = json.loads(opener.open(
            url + f'/api/updates?k={k}&cursor=0', timeout=20).read())
        print('GET /api/updates ok:', d['ok'])
    except urllib.error.HTTPError as e:
        print('GET /api/updates:', e.code, e.read(300))
    except Exception as e:
        print('GET /api/updates 异常:', type(e).__name__, e)

    uid = 'beef0000-0000-4000-8000-0000000000aa'
    try:
        req = urllib.request.Request(
            url + f'/api/upload/chunk?uploadId={uid}&name=t.bin&index=0&total=1&k={k}',
            data=os.urandom(1024 * 1024),
            headers={'X-Auth': k, 'Content-Type': 'application/octet-stream'},
            method='POST')
        print('POST chunk:', opener.open(req, timeout=90).read())
        req = urllib.request.Request(
            url + '/api/upload/finish?k=' + k,
            data=json.dumps({'uploadId': uid, 'name': 't.bin'}).encode(),
            headers={'X-Auth': k, 'Content-Type': 'application/json'},
            method='POST')
        print('POST finish:', opener.open(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        print('上传:', e.code, e.read(300))
    except Exception as e:
        print('上传异常:', type(e).__name__, e)

    tm.stop()
    srv.stop()
    try:
        os.remove(os.path.join('.', 't.bin'))
    except OSError:
        pass


if __name__ == '__main__':
    main()
