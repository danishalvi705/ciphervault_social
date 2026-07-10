with open('main.py', 'r') as f:
    content = f.read()

content = content.replace(
    'page = await browser.new_page(viewport={"width": 720, "height": 1280})',
    'page = await browser.new_page(viewport={"width": 1080, "height": 1920})'
)

content = content.replace(
    '.card {{ width: 920px;',
    '.card {{ width: 960px;'
)

with open('main.py', 'w') as f:
    f.write(content)
print("Done!")
