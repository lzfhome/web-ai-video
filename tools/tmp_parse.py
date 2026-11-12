import re
from pathlib import Path
s = Path(r'D:\AIWork\out_covers.html').read_text(encoding='utf-8', errors='ignore')
urls = re.findall(r'"murl":"(.*?)"', s)
print(len(urls))
for u in urls[:20]:
    print(u)
