from typing import List
import html
import datetime
from .models import CategoryData, Task

class DashboardGenerator:
    """
    Generates a web-based Engineering Dashboard (index.html).
    Features: Sidebar navigation, category breakdown cards, and interactive task views.
    """
    
    def generate(self, categories: List[CategoryData]) -> str:
        total_tasks = sum(len(cat.tasks) for cat in categories)
        total_categories = len(categories)
        high_priority_tasks = sum(1 for cat in categories for task in cat.tasks if task.taskPriority == "High")
        generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Sidebar items (Category Links)
        sidebar_items = '<a href="#dashboard" class="nav-item" onclick="showSection(\'dashboard\')">Running Overview</a>'
        for cat in categories:
            sidebar_items += f'<a href="#cat-{cat.categoryId}" class="nav-item" onclick="showSection(\'cat-{cat.categoryId}\')">{html.escape(cat.categoryName)}</a>'

        # 2. Main Content Sections
        sections_html = self._render_dashboard_overview(categories, total_tasks, total_categories, high_priority_tasks)
        
        for cat in categories:
            sections_html += self._render_category_section(cat)

        return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Engineering Sync Dashboard</title>
    <style>
        :root {{
            --primary: #14213D;
            --primary-light: #FCA311; /* Used as Accent/Highlight */
            --bg: #E5E5E5;
            --text-main: #000000;
            --text-muted: #4b5563;
            --border: #d1d5db;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        body {{ margin: 0; padding: 0; background-color: var(--bg); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: var(--text-main); }}
        a {{ text-decoration: none; color: inherit; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: #ffffff; min-height: 100vh; display: flex; box-shadow: var(--shadow); }}
        
        /* Sidebar Navigation */
        .sidebar {{ width: 280px; background: #FFFFFF; border-right: 1px solid var(--border); height: 100vh; position: sticky; top: 0; overflow-y: auto; padding: 24px 0; }}
        .sidebar-header {{ padding: 0 24px 24px 24px; font-size: 20px; font-weight: 800; color: var(--primary); border-bottom: 2px solid var(--border); margin-bottom: 24px; letter-spacing: -0.5px; }}
        .nav-item {{ display: block; padding: 12px 24px; color: #42526e; font-size: 14px; font-weight: 600; border-left: 4px solid transparent; cursor: pointer; transition: all 0.2s; }}
        .nav-item:hover {{ background: #ebecf0; color: var(--primary); }}
        .nav-item.active {{ background: var(--primary-light); border-left-color: var(--primary); color: var(--primary); }}
        
        /* Main Content Area */
        .main-content {{ flex: 1; padding: 48px; max-width: 1000px; }}
        
        /* Components */
        .section-title {{ font-size: 32px; font-weight: 800; margin-bottom: 12px; color: var(--text-main); letter-spacing: -1px; }}
        .section-subtitle {{ font-size: 16px; color: var(--text-muted); margin-bottom: 40px; }}
        
        .card-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; margin-bottom: 40px; }}
        .stat-card {{ background: white; border: 1px solid var(--border); border-radius: 12px; padding: 24px; box-shadow: var(--shadow); transition: transform 0.2s; }}
        .stat-card:hover {{ transform: translateY(-4px); }}
        .stat-val {{ font-size: 36px; font-weight: 800; color: var(--primary); }}
        .stat-label {{ font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-top: 6px; letter-spacing: 0.5px; }}
        
        .task-list {{ margin-top: 24px; display: flex; flex-direction: column; gap: 16px; }}
        .task-card {{ background: white; border: 1px solid var(--border); border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); position: relative; border-left: 6px solid #dfe1e6; }}
        .task-card.priority-high {{ border-left-color: #de350b; }}
        .task-card.priority-medium {{ border-left-color: #ff991f; }}
        .task-card.priority-low {{ border-left-color: #00875a; }}
        
        .task-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .task-subject {{ font-size: 17px; font-weight: 700; color: var(--text-main); }}
        .task-id {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; font-size: 12px; color: var(--text-muted); background: #ebecf0; padding: 2px 8px; border-radius: 4px; }}
        
        .update-box {{ background: #f9fafb; border: 1px solid var(--border); padding: 16px; border-radius: 8px; margin-top: 16px; font-size: 14px; line-height: 1.6; color: var(--text-main); display: -webkit-box; -webkit-line-clamp: 3; line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
        .update-box strong {{ color: var(--primary); text-transform: uppercase; font-size: 11px; margin-right: 8px; }}
        
        /* Status Badges */
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
        .badge-high {{ background: #ffebe6; color: #de350b; }}
        .badge-medium {{ background: #fffae6; color: #ff991f; }}
        .badge-low {{ background: #e3fcef; color: #006644; }}
        
        .page-section {{ display: none; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(100); }} }}
        .fade-in {{ animation: fadeIn 0.4s ease-out forwards; display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="sidebar-header">Engineering Sync</div>
            {sidebar_items}
        </div>
        <div class="main-content">
            {sections_html}
        </div>
    </div>

    <script>
        function showSection(sectionId) {{
            const sections = document.querySelectorAll('.page-section');
            sections.forEach(s => s.classList.remove('fade-in'));
            
            const target = document.getElementById(sectionId);
            if (target) {{
                target.classList.add('fade-in');
                window.scrollTo(0, 0);
            }}

            const navItems = document.querySelectorAll('.nav-item');
            navItems.forEach(item => {{
                if (item.getAttribute('onclick').includes("'" + sectionId + "'")) {{
                    item.classList.add('active');
                }} else {{
                    item.classList.remove('active');
                }}
            }});
        }}

        window.onload = function() {{
            const hash = window.location.hash.replace('#', '');
            showSection(hash || 'dashboard');
        }};

        window.onhashchange = function() {{
            const hash = window.location.hash.replace('#', '');
            if (hash) showSection(hash);
        }};
    </script>
</body>
</html>
'''

    def _render_dashboard_overview(self, categories, total_tasks, total_categories, high_priority_tasks) -> str:
        cat_cards = ""
        cat_chips = ""
        for cat in categories:
            if not cat.tasks: continue
            cat_cards += f'''
                <div class="stat-card" style="cursor:pointer;" onclick="location.hash='cat-{cat.categoryId}'; showSection('cat-{cat.categoryId}')">
                    <div style="font-weight:700; color:var(--primary); font-size:18px; margin-bottom:8px;">{html.escape(cat.categoryName)}</div>
                    <div style="font-size:14px; color:var(--text-muted);">{len(cat.tasks)} Active Tasks</div>
                    <div style="margin-top:16px; height:4px; width:100%; background:var(--bg); border-radius:2px; overflow:hidden;">
                        <div style="height:100%; width:{min(100, len(cat.tasks)*10)}%; background-color:var(--primary-light);"></div>
                    </div>
                </div>
            '''
            cat_chips += f'''
            <span class="badge" style="background:white; color:var(--primary); margin-right:8px; margin-bottom:12px; cursor:pointer; padding:6px 14px; border:1px solid var(--primary); transition:0.2s;" 
                  onclick="location.hash='cat-{cat.categoryId}'; showSection('cat-{cat.categoryId}')"
                  onmouseover="this.style.background='var(--primary-light)'" onmouseout="this.style.background='white'">
                {html.escape(cat.categoryName)} ({len(cat.tasks)})
            </span>
            '''

        empty_categories = total_categories - sum(1 for c in categories if c.tasks)
        return f'''
        <div id="dashboard" class="page-section">
            <div class="section-title">Weekly Engineering Overview</div>
            <div class="section-subtitle">
                This week: <strong>{total_tasks} active tasks</strong> across <strong>{total_categories - empty_categories} categories</strong> — 
                while <strong>{empty_categories} categories</strong> stand still with zero active tasks.
            </div>
            
            <div style="margin-bottom:40px; background:#fff; padding:24px; border-radius:12px; border:1px solid var(--border);">
                <div style="font-size:12px; font-weight:800; color:var(--text-muted); text-transform:uppercase; margin-bottom:16px; letter-spacing:1px;">Quick Navigation</div>
                {cat_chips}
            </div>

            <div class="card-grid">
                <div class="stat-card">
                    <div class="stat-val">{total_tasks}</div>
                    <div class="stat-label">Total Work Items</div>
                </div>
                <div class="stat-card">
                    <div class="stat-val">{total_categories}</div>
                    <div class="stat-label">Active Categories</div>
                </div>
                <div class="stat-card" style="border-left: 6px solid #de350b;">
                    <div class="stat-val" style="color:#de350b;">{high_priority_tasks}</div>
                    <div class="stat-label">High Priority Issues</div>
                </div>
            </div>
            
            <h3 style="margin-top:48px; color:var(--text-main); font-weight:800; font-size:24px; letter-spacing:-0.5px;">Department Breakdown</h3>
            <div class="card-grid" style="margin-top:24px;">
                {cat_cards}
            </div>
        </div>
        '''

    def _render_category_section(self, cat: CategoryData) -> str:
        task_items = ""
        for task in cat.tasks:
            priority_class = f"badge-{task.taskPriority.lower()}"
            card_priority = f"priority-{task.taskPriority.lower()}"
            summary = task.summarizedComments or "No changes reported over the last 7 days."
            
            task_items += f'''
                <div class="task-card {card_priority}">
                    <div class="task-header">
                        <div class="task-subject">{html.escape(task.taskSubject)}</div>
                        <span class="task-id">#{task.taskId}</span>
                    </div>
                    <div style="display:flex; gap:12px; align-items:center;">
                        <span class="badge {priority_class}">{task.taskPriority}</span>
                        <span style="font-size:13px; color:var(--text-muted); font-weight:600;">STATUS: {html.escape(task.taskStatus)}</span>
                        <span style="font-size:13px; color:var(--text-muted); margin-left:auto;">👤 {html.escape(task.assigneeName)}</span>
                    </div>
                    <div class="update-box">
                        <strong>Update</strong> {html.escape(summary)}
                    </div>
                </div>
            '''

        return f'''
        <div id="cat-{cat.categoryId}" class="page-section">
            <div style="display:flex; align-items:center; margin-bottom:32px;">
                <h2 class="section-title" style="margin-bottom:0;">{html.escape(cat.categoryName)}</h2>
                <span class="badge" style="background:var(--primary); color:white; margin-left:16px;">{len(cat.tasks)} Tasks</span>
            </div>
            <div class="task-list">
                {task_items}
            </div>
        </div>
        '''
