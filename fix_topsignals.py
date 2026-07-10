with open('daily_videos.py', 'r') as f:
    content = f.read()

old = '''        rows_html += f"""
        <div class="row">
            <span style="font-size:24px">{s.get('symbol','')}</span>
            <span class="badge {badge_cls}">{direction}</span>
            <span class="yellow">{grade}</span>
            <span class="gray">{score}/10</span>
        </div>"""'''

new = '''        status = s.get('status', 'pending')
        if 'tp3' in status:   status_str, status_cls = 'TP3 ✅✅✅', 'green'
        elif 'tp2' in status: status_str, status_cls = 'TP2 ✅✅',  'green'
        elif 'tp1' in status: status_str, status_cls = 'TP1 ✅',    'green'
        elif 'sl'  in status: status_str, status_cls = 'SL ❌',     'red'
        elif status == 'active':  status_str, status_cls = 'ACTIVE 🟢', 'green'
        else:                     status_str, status_cls = 'PENDING ⏳', 'gray'
        rows_html += f"""
        <div class="row">
            <span style="font-size:22px">{s.get(\'symbol\',\'\')}</span>
            <span class="badge {badge_cls}" style="font-size:16px">{direction}</span>
            <span class="yellow" style="font-size:22px">{grade}</span>
            <span class="{status_cls}" style="font-size:20px">{status_str}</span>
        </div>"""'''

if old in content:
    content = content.replace(old, new)
    print("✅ Patched!")
else:
    print("❌ Not found")

with open('daily_videos.py', 'w') as f:
    f.write(content)
