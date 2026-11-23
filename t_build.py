# -*- coding: utf-8 -*-
import json
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = ('https://api.github.com/repos/liguokun66/'
        'BloodPressureAssistant/actions/runs?per_page=1')

last = ''
for i in range(45):
    try:
        d = json.loads(OP.open(BASE, timeout=25).read().decode())
        runs = d.get('workflow_runs', [])
        if not runs:
            print('no runs yet', flush=True)
        else:
            r = runs[0]
            cur = '%s/%s' % (r['status'], r['conclusion'])
            if cur != last:
                print('[%s] %s id=%s run_number=%s' %
                      (time.strftime('%H:%M:%S'), cur, r['id'],
                       r.get('run_number')), flush=True)
                last = cur
            if r['status'] == 'completed':
                print('FINISHED conclusion=%s run_id=%s html=%s' %
                      (r['conclusion'], r['id'], r['html_url']), flush=True)
                break
    except Exception as e:
        print('poll err', type(e).__name__, e, flush=True)
    time.sleep(60)
print('POLL DONE', flush=True)
