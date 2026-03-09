import requests, json, time

BASE = 'http://localhost:8011'
DOC_ID = 17

# Wait for server
for i in range(12):
    try:
        if requests.get(f'{BASE}/health', timeout=5).status_code == 200:
            print('Backend ready')
            break
    except:
        time.sleep(2)

# Case brief test
r = requests.get(f'{BASE}/api/analysis/case-brief/{DOC_ID}', timeout=30)
j = r.json()
cb = j.get('case_brief', j)
cid = cb.get('case_identification', {})

print('=== CASE BRIEF (doc 17) ===')
print('Case Name :', cid.get('case_name'))
print('Court     :', cid.get('court'))
print('Year      :', cid.get('year'))
print('Citation  :', cid.get('citation'))
print()
print('Executive Summary:')
print(' ', cb.get('executive_summary', '')[:300])
print()
print('Facts:')
print(' ', str(cb.get('facts', ''))[:300])
print()
print('Holding:')
print(' ', str(cb.get('holding', ''))[:200])
print()
issues = cb.get('issues', [])
print(f'Issues ({len(issues)}):')
for ix, iss in enumerate(issues[:3], 1):
    print(f'  {ix}. {str(iss)[:150]}')
