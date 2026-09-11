import requests, json

BASE = 'http://localhost:8000'

# 1. Login
r = requests.post(BASE + '/auth/login', json={'email': 'officer@labelsure.in', 'password': 'Test1234'})
token = r.json()['access_token']
headers = {'Authorization': 'Bearer ' + token}
print('Login:', r.status_code, 'role:', r.json()['user']['role'])

# 2. Upload compliant label
with open('backend/sample_data/compliant_label.png', 'rb') as f:
    r2 = requests.post(
        BASE + '/scans/upload',
        headers=headers,
        files={'file': ('compliant_label.png', f, 'image/png')},
        data={'font_type': 'printed'},
    )

resp = r2.json()
print('Scan HTTP status:', r2.status_code)
print('Verdict:', resp.get('verdict'))
print('Confidence:', resp.get('overall_confidence'))
rules = resp.get('rule_results', [])
passed = sum(1 for x in rules if x['passed'])
print('Rules:', str(passed) + '/' + str(len(rules)), 'passed')
for rr in rules:
    status = 'PASS' if rr['passed'] else 'FAIL'
    rid = rr.get('rule_id', '?')
    expl = (rr.get('explanation') or '')[:60]
    print('  [' + status + '] ' + rid + ' - ' + expl)

# 3. List scans
r3 = requests.get(BASE + '/scans', headers=headers)
print('\nList scans status:', r3.status_code, 'total:', r3.json().get('total'))
