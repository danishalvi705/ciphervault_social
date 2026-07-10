with open('daily_videos.py', 'r') as f:
    content = f.read()

content = content.replace("'TP3 ✅✅✅', 'green'", "'TP3 ✅', 'green'")
content = content.replace("'TP2 ✅✅',  'green'", "'TP2 ✅', 'green'")

with open('daily_videos.py', 'w') as f:
    f.write(content)
print("Done!")
