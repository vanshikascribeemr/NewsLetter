from typing import List
import html
import datetime
import json
import re
from .models import CategoryData, Task

class DashboardGenerator:
    """
    Generates a high-fidelity, editorial newsletter dashboard based on the provided wireframe.
    Features a clean headline, a stylized promo banner, and alternating article blocks.
    """
    
    async def generate(self, categories: List[CategoryData], subscribed_ids: List[int] = None, subscribed_names: List[str] = None, is_warming: bool = False) -> str:
        timestamp = datetime.datetime.now().strftime("%B %d, %Y")
        subscribed_ids = subscribed_ids or []
        subscribed_names = subscribed_names or []
        
        # Pre-filter all categories to remove "Done" tasks
        for cat in categories:
            cat.tasks = [t for t in cat.tasks if (t.taskStatus or "").lower() != "done"]
            
        # Include categories that have tasks OR are explicitly subscribed by the user (by ID or Name).
        active_cats = [
            c for c in categories 
            if c.tasks or c.categoryId in subscribed_ids or c.categoryName.lower().strip() in subscribed_names
        ]
        total_tasks = sum(len(c.tasks) for c in active_cats)
        
        # Build category label map for JS
        label_map = {f"cat-{c.categoryId}": c.categoryName for c in active_cats}
        label_map["home"] = "The Engineering Sync"
        label_map_json = json.dumps(label_map)

        nav_subscribed = ""
        nav_others = ""
        
        category_sections = ""
        
        for cat in active_cats:
            safe_id = f"cat-{cat.categoryId}"
            cat_name_esc = html.escape(cat.categoryName)
            cat_name_norm = cat.categoryName.lower().strip()
            
            # Subscribed styling: Match by ID OR Name
            is_sub = cat.categoryId in subscribed_ids or cat_name_norm in subscribed_names
            style = 'font-weight: 800; color: #5c8ca3;' if is_sub else ''
            
            link_html = f'<a href="#{safe_id}" class="nav-item" style="{style}" onclick="showSection(\'{safe_id}\', \'{cat_name_esc}\')">{cat_name_esc}</a>'
            
            if is_sub:
                nav_subscribed += link_html
            else:
                nav_others += link_html
                
            category_sections += self._render_category_section(cat, safe_id)

        # Build Sidebar HTML
        # Using <details> and <summary> for accordion folders
        
        sidebar_links = f'''
            <details open class="nav-folder">
                <summary class="nav-folder-header">My Streams</summary>
                <div class="nav-folder-content">
                    {nav_subscribed if nav_subscribed else '<div style="padding:10px 16px; font-size:12px; color:#a0aec0;">No subscriptions active.</div>'}
                </div>
            </details>
            
            <details class="nav-folder">
                <summary class="nav-folder-header">All Categories</summary>
                <div class="nav-folder-content">
                    {nav_others}
                </div>
            </details>
        '''


        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Engineering Sync | Web Intelligence</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --sidebar-width: 280px;
            --sidebar-collapsed-width: 64px;
            --paper: #ffffff;
            --ink: #1a202c;
            --ink-muted: #718096;
            --accent: #5c8ca3; /* Muted slate blue from reference */
            --accent-light: #dae5ed;
            --border: #edf2f7;
            --header-font: 'Inter', sans-serif;
            --body-font: 'Inter', sans-serif;
            --serif-font: 'Source Serif 4', serif;
        }}

        * {{ box-sizing: border-box; scroll-behavior: smooth; }}
        body {{ 
            margin: 0; 
            background: #ffffff; 
            color: var(--ink); 
            font-family: var(--body-font); 
            display: flex;
            min-height: 100vh;
        }}

        /* Sidebar Styling */
        .sidebar {{
            width: var(--sidebar-width);
            background: #f7fafc;
            border-right: 1px solid var(--border);
            height: 100vh;
            position: fixed;
            left: 0;
            top: 0;
            transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 1000;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        .sidebar.collapsed {{ width: var(--sidebar-collapsed-width); }}

        .sidebar-header {{
            padding: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            min-width: var(--sidebar-width);
        }}

        .sidebar-logo {{
            text-transform: uppercase;
            font-weight: 900;
            font-size: 24px;
            color: var(--accent);
            letter-spacing: 0.05em;
            transition: opacity 0.2s;
        }}

        .sidebar.collapsed .sidebar-logo {{
            display: none;
        }}

        .sidebar.collapsed .sidebar-header {{
            min-width: var(--sidebar-collapsed-width);
            justify-content: center;
            padding: 24px 0;
            border-bottom: none;
        }}

        .sidebar.collapsed .nav-list {{
            display: none;
        }}

        .toggle-btn {{
            background: none;
            border: none;
            cursor: pointer;
            padding: 8px;
            color: var(--ink-muted);
            display: flex;
            align-items: center;
        }}

        .nav-list {{ flex: 1; padding: 20px 12px; overflow-y: auto; min-width: var(--sidebar-width); }}
        .nav-item {{
            display: flex;
            align-items: center;
            padding: 12px 16px;
            margin-bottom: 4px;
            border-radius: 6px;
            color: var(--ink-muted);
            text-decoration: none;
            font-size: 14px;
            font-weight: 700;
            white-space: nowrap;
            transition: 0.2s;
        }}
        .nav-item span {{ margin-right: 16px; font-size: 18px; }}
        .nav-item:hover, .nav-item.active {{ background: #e2e8f0; color: var(--accent); }}
        
        /* Accordion Folder Styling */
        .nav-folder {{
            margin-bottom: 8px;
        }}
        
        .nav-folder-header {{
            padding: 12px 16px;
            font-size: 11px;
            font-weight: 800;
            color: #a0aec0;
            text-transform: uppercase;
            cursor: pointer;
            list-style: none; /* Hide default triangle */
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(0,0,0,0.02);
            border-radius: 6px;
            margin-bottom: 4px;
            transition: background 0.2s;
        }}
        
        .nav-folder-header:hover {{
            background: rgba(0,0,0,0.05);
            color: var(--ink);
        }}
        
        /* Custom arrow using ::after */
        .nav-folder-header::after {{
            content: "▼";
            font-size: 8px;
            transition: transform 0.2s;
        }}
        
        details[open] .nav-folder-header::after {{
            transform: rotate(180deg);
        }}
        
        /* Hide default marker in Safari/Chrome */
        .nav-folder-header::-webkit-details-marker {{
            display: none;
        }}

        .nav-folder-content {{
            padding-left: 0; 
            margin-top: 4px;
            animation: slideDown 0.2s ease-out;
        }}

        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-5px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Content Container */
        .main-content {{
            flex: 1;
            margin-left: var(--sidebar-width);
            transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            padding: 40px;
            display: flex;
            justify-content: center;
        }}

        .newsletter-envelope {{
            width: 100%;
            max-width: 800px;
            border: 1px solid var(--border);
            background: white;
            box-shadow: 0 10px 25px rgba(0,0,0,0.03);
            display: flex;
            flex-direction: column;
        }}

        /* Newsletter Header Components */
        .top-band {{
            display: flex;
            align-items: flex-end;
            padding: 20px 30px;
            border-bottom: 1px solid var(--border);
            justify-content: space-between;
        }}

        .logo-text {{
            font-size: 30px;
            font-weight: 900;
            color: var(--accent);
            letter-spacing: -0.03em;
            line-height: 1;
            text-transform: uppercase;
        }}

        .top-subline {{
            font-size: 14px;
            color: var(--ink-muted);
            text-align: right;
            max-width: 280px;
            line-height: 1.4;
            font-weight: 500;
        }}

        .nav-bar {{
            background: var(--accent);
            display: flex;
            padding: 0 30px;
            height: 50px;
            align-items: center;
            color: white;
            justify-content: space-between;
        }}

        .nav-link-group {{ display: flex; gap: 30px; font-weight: 800; font-size: 13px; text-transform: uppercase; }}
        .nav-link-group span {{ cursor: pointer; transition: opacity 0.2s; }}
        .nav-link-group span:hover {{ opacity: 0.8; text-decoration: underline; }}
        .issue-date {{ font-size: 13px; font-weight: 500; opacity: 0.9; border-left: 1px solid rgba(255,255,255,0.3); padding-left: 20px; height: 100%; display: flex; align-items: center; }}

        .promo-banner {{
            margin: 30px;
            background: var(--accent);
            height: 100px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .promo-text {{
            color: white;
            font-size: 42px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.15em;
        }}

        .newsletter-summary-heading {{
            padding: 0 30px;
            margin-bottom: 30px;
        }}

        .news-headline-main {{
            font-size: 32px;
            font-weight: 800;
            color: var(--accent);
            margin: 0 0 5px 0;
        }}

        .news-headline-sub {{
            font-size: 16px;
            color: var(--ink-muted);
            font-weight: 500;
        }}

        /* Article Block Styling */
        .article-block {{
            display: flex;
            padding: 30px;
            gap: 40px;
            align-items: flex-start;
            border-bottom: 1px solid var(--border);
            transition: transform 0.2s, background 0.2s;
        }}

        .article-block:hover {{
            background: #fdfdfd;
        }}

        .article-block.alt {{ flex-direction: row-reverse; }}

        .article-content {{ flex: 1; }}
        .article-photo {{
            flex: 0 0 160px;
            height: 100px;
            background: var(--accent-light);
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 15px;
            position: relative;
        }}

        .photo-label {{
            font-size: 20px;
            font-weight: 800;
            color: var(--accent);
            text-align: center;
            line-height: 1;
        }}

        .photo-icon {{
            position: absolute;
            bottom: 15px;
            right: 15px;
            opacity: 0.5;
        }}

        .article-headline {{
            font-size: 16px;
            font-weight: 800;
            color: var(--accent);
            margin: 0 0 14px 0;
            letter-spacing: -0.01em;
        }}

        .article-summary {{
            font-family: var(--serif-font);
            font-size: 16px;
            line-height: 1.8;
            color: #1a202c;
            margin: 0;
            letter-spacing: -0.005em;
        }}

        /* Sections SPA behavior */
        .content-section {{ display: none; width: 100%; }}
        .content-section.active {{ display: block; }}

        .footer {{
            background: var(--accent);
            padding: 15px 30px;
            text-align: center;
            color: white;
            font-size: 13px;
            font-weight: 500;
            margin-top: auto;
        }}

        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .spin {{ animation: spin 1s linear infinite; }}

        @media (max-width: 900px) {{
            .main-content {{ padding: 20px; }}
            .article-block {{ flex-direction: column !important; }}
            .article-photo {{ width: 100%; flex: none; }}
        }}
    </style>
</head>
<body>

    <aside class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-logo">THE SYNC</div>
            <button class="toggle-btn" onclick="toggleSidebar()">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
            </button>
        </div>
        <nav class="nav-list">
            <a href="#home" class="nav-item active" onclick="showSection('home', 'The Engineering Sync')">Home</a>
            {sidebar_links}
            <div style="margin-top: auto; border-top: 1px solid var(--border); padding-top: 20px;">
                <a href="/admin" class="nav-item" style="opacity: 0.6; font-size: 12px;">Admin Panel</a>
            </div>
        </nav>
    </aside>

    <main class="main-content" id="main-content">
        {f'<div style="background: var(--accent-light); color: var(--accent); padding: 12px 20px; border-radius: 8px; margin-bottom: 30px; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 10px;"><div class="spin" style="width:12px; height:12px; border:2px solid var(--accent); border-top-color:transparent; border-radius:50%;"></div> Summary Intelligence Engine: Synthesizing latest task comments in background. Please refresh in 1 minute for full summaries.</div>' if is_warming else ''}
        <div class="newsletter-envelope">
            
            <header class="top-band">
                <div class="logo-text" id="main-logo-text">The Engineering Sync</div>
                <div class="top-subline">Technical progression and architectural decisions for executive review</div>
            </header>

            <nav class="nav-bar">
                <div class="nav-link-group">
                    <span onclick="showSection('home', 'The Engineering Sync')">HOME</span>
                </div>
                <div class="issue-date">{timestamp}</div>
            </nav>

            <!-- HOME SECTION -->
            <div id="home" class="content-section active">
                <div class="promo-banner">
                    <div class="promo-text" style="font-size: 32px; letter-spacing: 0.1em;">
                        Bulletin <span style="font-weight: 500; margin-left:15px; font-size: 14px;">{timestamp}</span>
                    </div>
                </div>


                <div class="newsletter-summary-heading">
                    <h1 class="news-headline-main">Weekly Operational Sync</h1>
                    <p class="news-headline-sub">Across {len(active_cats)} functional departments, organizational workstreams summarized.</p>
                </div>

                <div style="padding: 0 30px 40px;">
                    <p style="font-family: var(--serif-font); font-size: 18px; line-height: 1.8; color: #2d3748;">
                        This briefing covers the latest technical progression and critical operational updates synthesized for executive review.
                        Select a department from the directory below to view detailed task narratives and historical context.
                    </p>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; margin-top: 30px;">
                        {sidebar_links.replace('class="nav-item"', 'class="nav-item" style="background:#f7fafc; border:1px solid var(--border); height:auto; padding:20px; font-size:16px;"')}
                    </div>
                </div>
            </div>

            <!-- CATEGORY SECTIONS -->
            {category_sections}

            <footer class="footer">
                ScribeEMR Engineering Operations &copy; {datetime.datetime.now().year}
            </footer>
        </div>
    </main>

    <script>
        const SECTION_LABELS = {label_map_json};

        function toggleSidebar() {{
            const sidebar = document.getElementById('sidebar');
            const mainContent = document.getElementById('main-content');
            sidebar.classList.toggle('collapsed');
            mainContent.style.marginLeft = sidebar.classList.contains('collapsed') ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)';
        }}

        function showSection(id, label) {{
            // Use provided label or find it in the map
            const finalLabel = label || SECTION_LABELS[id || 'home'];
            
            // Toggle Header/Nav visibility for Home
            const topBand = document.querySelector('.top-band');
            const navBar = document.querySelector('.nav-bar');
            const isHome = (id === 'home' || id === '');
            
            if (isHome) {{
                topBand.style.display = 'none';
                navBar.style.display = 'none';
            }} else {{
                topBand.style.display = 'flex';
                navBar.style.display = 'flex';
            }}

            document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
            const target = document.getElementById(id || 'home');
            if (target) target.classList.add('active');
            
            document.querySelectorAll('.nav-item').forEach(link => {{
                const href = link.getAttribute('href').replace('#', '');
                link.classList.toggle('active', href === (id || 'home'));
            }});

            if (finalLabel && finalLabel !== 'null') {{
                document.getElementById('main-logo-text').innerText = finalLabel;
            }}

            window.scrollTo({{ top: 0, behavior: 'auto' }});
            const hash = id ? '#' + id : '#home';
            if (window.location.hash !== hash) {{
                history.pushState(null, null, hash);
            }}
        }}

        window.onpopstate = () => {{
            const hash = window.location.hash.replace('#', '') || 'home';
            showSection(hash);
        }};
        window.onload = () => {{
            const hash = window.location.hash.replace('#', '') || 'home';
            showSection(hash);
        }};
    </script>
</body>
</html>
'''

    def _render_category_section(self, cat: CategoryData, safe_id: str) -> str:
        tasks_html = ""
        for i, task in enumerate(cat.tasks):
            alt_class = "alt" if i % 2 != 0 else ""
            
            # Clean summary
            summary = task.summarizedComments or "Generating recent activity summary..."
            id_pattern = rf'^#?\s*{task.taskId}\s*[:\-–—]?\s*'
            summary = re.sub(id_pattern, '', summary, flags=re.IGNORECASE)
            
            # Priority Color Mapping
            priority_map = {
                "critical": "#5C8CA3", # Pure Red
                "urgent": "#5C8CA3",   # Red
                "high": "#5C8CA3",     # Red
                "medium": "#5C8CA3",   # Yellow
                "normal": "#5C8CA3",   # Yellow
                "low": "#5C8CA3",      # Green
                "none": "var(--ink-muted)"
            }

            p_lower = (task.taskPriority or "").lower()
            p_color = priority_map.get(p_lower, "var(--accent)")

            # Metadata Box Content
            meta_box_content = f'''
                <div class="photo-label">#{task.taskId}</div>
                <div style="font-size:10px; font-weight:700; margin-top:8px; text-align:center; text-transform:uppercase; line-height:1.4;">
                    <span style="color:{p_color};">{task.taskPriority} Priority</span><br>
                    <span style="color:var(--ink); font-weight:900;">{task.assigneeName}</span>
                </div>
            '''


            
            tasks_html += f'''
            <div class="article-block {alt_class}">
                <div class="article-photo">
                    {meta_box_content}
                </div>
                <div class="article-content">
                    <h3 class="article-headline">{html.escape(task.taskSubject)}</h3>
                    <p class="article-summary">{html.escape(summary)}</p>
                </div>
            </div>'''

        if not cat.tasks:
            tasks_html = f'''
            <div style="padding: 60px 30px; text-align: center; background: #fdfdfd; border-radius: 8px; border: 1px dashed var(--border); margin: 30px;">
                <div style="font-size: 40px; margin-bottom: 20px; opacity: 0.3;">📂</div>
                <h3 style="color: var(--accent); margin-bottom: 10px;">No Active Work Items</h3>
                <p style="color: var(--ink-muted); font-family: var(--serif-font);">There are currently no open or in-progress items recorded for this functional stream in the last period.</p>
            </div>'''

        return f'''
        <div id="{safe_id}" class="content-section">
            <div class="task-list" style="margin-top: 40px;">
                {tasks_html}
            </div>
        </div>'''
