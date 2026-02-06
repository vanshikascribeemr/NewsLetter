import html
from typing import List
from .database import User

class AdminGenerator:
    """
    Generates a sleek, executive admin dashboard for user and subscription management.
    """
    
    def generate(self, users: List[User]) -> str:
        user_rows = ""
        for user in users:
            subs_count = len(user.subscriptions)
            subs_list = ", ".join([s.name for s in user.subscriptions]) if user.subscriptions else "Disconnected (No Subscriptions)"
            
            user_rows += f'''
            <tr id="user-row-{user.id}">
                <td>
                    <div style="font-weight: 700; color: #1e293b;">{html.escape(user.email)}</div>
                    <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Internal ID: {user.id}</div>
                </td>
                <td>
                    <span class="badge" style="background: { '#dae5ed' if subs_count > 0 else '#f1f5f9' }; color: { '#5c8ca3' if subs_count > 0 else '#94a3b8' };">
                        {subs_count} Streams
                    </span>
                </td>
                <td style="max-width: 300px; font-size: 12px; color: #475569;">
                    <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        {html.escape(subs_list)}
                    </div>
                </td>
                <td style="text-align: right;">
                    <button class="btn btn-danger" onclick="deleteUser({user.id}, '{html.escape(user.email)}')">Remove</button>
                </td>
            </tr>
            '''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registry Admin | The Engineering Sync</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #5c8ca3;
            --danger: #e11d48;
            --bg: #f8fafc;
            --card: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            font-family: 'Inter', sans-serif; 
            background: var(--bg); 
            color: var(--text-main);
            padding: 40px 20px;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}

        header {{
            margin-bottom: 40px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}

        .logo {{
            text-transform: uppercase;
            font-weight: 900;
            font-size: 24px;
            color: var(--primary);
            letter-spacing: -0.02em;
        }}

        .subline {{
            font-size: 14px;
            color: var(--text-muted);
            margin-top: 4px;
        }}

        .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            margin-bottom: 30px;
        }}

        .card-header {{
            padding: 24px 30px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .card-title {{ font-size: 18px; font-weight: 800; color: var(--text-main); }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            text-align: left;
            padding: 16px 30px;
            background: #f1f5f9;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }}

        td {{
            padding: 20px 30px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}

        .badge {{
            padding: 4px 10px;
            border-radius: 100px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .btn {{
            padding: 10px 20px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            transition: 0.2s;
            border: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }}

        .btn-primary {{ background: var(--primary); color: white; }}
        .btn-primary:hover {{ opacity: 0.9; transform: translateY(-1px); }}

        .btn-danger {{ background: #fef2f2; color: var(--danger); border: 1px solid #fee2e2; }}
        .btn-danger:hover {{ background: var(--danger); color: white; }}

        .form-group {{
            display: flex;
            gap: 12px;
            padding: 30px;
            background: #f8fafc;
        }}

        input {{
            flex: 1;
            padding: 12px 16px;
            border-radius: 6px;
            border: 1px solid var(--border);
            font-family: inherit;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }}

        input:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px rgba(92, 140, 163, 0.1); }}

        /* Toast notifications */
        .toast {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 16px 24px;
            background: #1e293b;
            color: white;
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
            display: none;
            z-index: 1000;
            font-weight: 600;
            font-size: 14px;
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <div>
            <div class="logo">Registry Admin</div>
            <div class="subline">Central intelligence recipient management system</div>
        </div>
        <div style="font-size: 12px; font-weight: 700; color: var(--text-muted);">
            ScribeEMR Operations Engine v2.0
        </div>
    </header>

    <div class="card">
        <div class="card-header">
            <div class="card-title">Enlist New Recipient</div>
        </div>
        <div class="form-group">
            <input type="email" id="new-email" placeholder="Enter recipient email address (e.g. director@scribeemr.com)">
            <button class="btn btn-primary" onclick="addUser()">Add Recipient</button>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <div class="card-title">Active Distribution List ({len(users)})</div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Recipient Information</th>
                    <th>Status</th>
                    <th>Subscribed Streams</th>
                    <th style="text-align: right;">Operations</th>
                </tr>
            </thead>
            <tbody>
                {user_rows if user_rows else '<tr><td colspan="4" style="text-align:center; padding: 60px; color: var(--text-muted);">No recipients found in the registry.</td></tr>'}
            </tbody>
        </table>
    </div>
</div>

<div id="toast" class="toast"></div>

<script>
    function showToast(msg, isError = false) {{
        const t = document.getElementById('toast');
        t.innerText = msg;
        t.style.background = isError ? '#e11d48' : '#1e293b';
        t.style.display = 'block';
        setTimeout(() => {{ t.style.display = 'none'; }}, 3000);
    }}

    async function addUser() {{
        const email = document.getElementById('new-email').value.trim();
        if (!email) return showToast('Please enter an email address', true);
        
        try {{
            const resp = await fetch('/admin/users', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ email: email }})
            }});
            
            if (resp.ok) {{
                showToast('User added successfully. Refreshing...');
                setTimeout(() => location.reload(), 1000);
            }} else {{
                const err = await resp.json();
                showToast(err.detail || 'Failed to add user', true);
            }}
        }} catch (e) {{
            showToast('Network error', true);
        }}
    }}

    async function deleteUser(id, email) {{
        if (!confirm(`Are you sure you want to remove ${{email}} from the distribution list?`)) return;
        
        try {{
            const resp = await fetch(`/admin/users/${{id}}`, {{ method: 'DELETE' }});
            if (resp.ok) {{
                showToast('User removed successfully');
                document.getElementById(`user-row-${{id}}`).remove();
            }} else {{
                showToast('Failed to remove user', true);
            }}
        }} catch (e) {{
            showToast('Network error', true);
        }}
    }}
</script>

</body>
</html>
'''
