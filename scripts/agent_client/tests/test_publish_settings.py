# -*- coding: utf-8 -*-
"""browser_local 发布设置增强测试: include_hidden + 封面/正文 input 区分 + 话题下拉 + 声明"""
import sys, tempfile, os, json, threading, http.server
sys.path.insert(0, 'scripts/agent_client')
from browser import BrowserSession
from actions import Actions
from platforms import load_platforms

PORT = 5951
HTML = """<!doctype html><html><body>
<textarea placeholder="请输入标题（最多 100 个字）"></textarea>
<div class="DraftEditor" contenteditable="true"></div>
<input type="file" id="doc" accept=".pdf,.md,.txt,.docx">
<input type="file" id="bodyimg" accept="image/webp,image/jpg,image/jpeg,image/png,image/avif,image/heic">
<input type="file" id="cover" accept=".jpeg, .jpg, .png">
<input type="text" placeholder="添加话题" class="TopicEditor">
<div style="display:none" class="dropdown"><ul><li>考研</li><li>考研数学</li></ul></div>
<input type="checkbox" class="declare" checked> 原创声明
<button>发布</button>
</body></html>"""

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b = HTML.encode('utf-8')
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

platforms = load_platforms()
platforms['zhihu']['login_cookie'] = []
tmp = tempfile.mkdtemp(prefix='pub_')
browser = BrowserSession(os.path.join(tmp,'profile'), headless=True).start()
actions = Actions(browser, platforms)
page = browser.page_for('zhihu', platforms['zhihu'])
page.goto('http://127.0.0.1:%d/' % PORT, timeout=15000)
page.wait_for_timeout(600)

ok = True
def check(cond, name):
    global ok
    print(('PASS ' if cond else 'FAIL ')+name, flush=True)
    if not cond: ok = False

# 1) include_hidden
r = actions.extract(page, {'include_hidden': True})
data = json.loads(r['content'])
tags = {x['tag'] for x in data}; ph = {x['ph'] for x in data}; acc = {(x['accept'] or '') for x in data}
opts = [x.get('options','') for x in data if x.get('options')]
check('LI' in tags or any('考研' in o for o in opts), 'include_hidden 含隐藏下拉选项')
check('添加话题' in ph, '含话题输入 placeholder')
check(any('.jpeg' in a for a in acc), '含封面 input accept(.jpeg)')
check(any('webp' in a for a in acc), '含正文插图 input accept(webp)')

# 2) 封面/正文 input 区分
check('input[type=file]' in (actions._pick_upload_input(page,'cover') or ''), '封面 selector 已定位')
check('input[type=file]' in (actions._pick_upload_input(page,'image') or ''), '正文 selector 已定位')

# 3) 话题下拉 + 4) 声明
t1 = actions.publish(page, 'zhihu', {'title':'测试标题','content':'正文','topics':['考研']})
check(t1.get('topics_added',0) >= 1, '话题下拉选择成功: %s' % t1.get('topics_added'))
t2 = actions.publish(page, 'zhihu', {'title':'t','content':'c','declaration':'false'})
check(t2.get('declaration') is False, '声明取消成功: %s' % t2.get('declaration'))

browser.close(); srv.shutdown()
print('== %s ==' % ('ALL PASS' if ok else 'SOME FAILED'), flush=True)
sys.exit(0 if ok else 1)
