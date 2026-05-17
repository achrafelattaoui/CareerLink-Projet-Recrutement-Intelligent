import glob, re

files = glob.glob(r'c:\Users\USER\Projet_nosql\frontend\*.html')
new_link = """
        <a class="sidebar-link" href="my-applications.html" id="nav-my-applications">
            <i class="fas fa-history"></i><span>Mes candidatures</span>
        </a>"""

for f in files:
    if f.endswith('login.html') or f.endswith('test-api.html'): continue
    with open(f, 'r', encoding='utf-8', errors='ignore') as file:
        content = file.read()
    
    # Remove existing link if any
    content = re.sub(r'\s*<a class="sidebar-link" href="my-applications\.html"[^>]*>.*?</a>', '', content, flags=re.DOTALL)
    
    # Insert new link right after jobs.html link
    pattern = r'(<a class="sidebar-link[^>]*href="jobs\.html"[^>]*>.*?</a>)'
    
    def repl(m):
        return m.group(1) + new_link
        
    content = re.sub(pattern, repl, content, flags=re.DOTALL)
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print('Updated', f)
