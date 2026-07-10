with open('main.py', 'r') as f:
    content = f.read()

# Reduce card width to 700px
content = content.replace(
    '.card {{ width: 720px;',
    '.card {{ width: 700px;'
)

# Reduce card background opacity so video shows through
content = content.replace(
    'background: rgba(5, 5, 10, 0.85);',
    'background: rgba(5, 5, 10, 0.55);'
)

with open('main.py', 'w') as f:
    f.write(content)
print("Done!")
