with open('main.py', 'r') as f:
    content = f.read()

content = content.replace(
    '.card {{ width: 820px;',
    '.card {{ width: 720px;'
)

with open('main.py', 'w') as f:
    f.write(content)
print("Done!")
