with open('main.py', 'r') as f:
    content = f.read()

# Shrink card width and fonts to fit within 1080px viewport
content = content.replace(
    '.card {{ width: 960px;',
    '.card {{ width: 820px;'
)
content = content.replace(
    'font-size: 64px; font-weight: bold; margin-bottom: 30px;',
    'font-size: 52px; font-weight: bold; margin-bottom: 25px;'
)
content = content.replace(
    'padding: 20px 0; border-bottom: 1px solid rgba(255,255,255,0.15); font-size: 36px;',
    'padding: 16px 0; border-bottom: 1px solid rgba(255,255,255,0.15); font-size: 30px;'
)
content = content.replace(
    'padding: 50px 60px;',
    'padding: 40px 50px;'
)

with open('main.py', 'w') as f:
    f.write(content)
print("Done!")
