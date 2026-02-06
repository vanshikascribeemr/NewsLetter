from typing import List
import html
import datetime
from .models import CategoryData, Task

class HTMLGenerator:
    """
    Generates a premium, sleek HTML email for the weekly engineering newsletter.
    Focuses on clarity, professional aesthetics, and a clean reading experience.
    """
    
    # --- DESIGN TOKENS ---
    COLOR_BG = "#f8fafc" 
    COLOR_PRIMARY = "#6366f1"
    COLOR_PRIMARY_DARK = "#4f46e5"
    COLOR_ACCENT = "#0f172a" 
    COLOR_TEXT_MAIN = "#1e293b"
    COLOR_TEXT_MUTED = "#64748b"
    COLOR_BORDER = "#e2e8f0"
    
    FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    
    def generate(self, categories: List[CategoryData], subscriptions: dict = None) -> str:
        date_str = datetime.datetime.now().strftime("%B %d, %Y")
        total_tasks = sum(len(c.tasks) for c in categories)
        active_cats = categories # Retain all categories (subscribed streams)

        
        # Build Components
        chips_html = ""
        category_sections = ""
        
        for cat in active_cats:
            safe_id = f"cat-{cat.categoryId}"
            dashboard_base = (subscriptions or {}).get("dashboard_link", "#")
            
            # Nav Chips
            chips_html += f'''
            <a href="#{safe_id}" style="display:inline-block; text-decoration:none; background-color:#eff6ff; color:#2563eb; padding:6px 14px; border-radius:8px; font-size:12px; margin:0 8px 8px 0; font-weight:700; border:1px solid #dbeafe;">
                {html.escape(cat.categoryName)} ({len(cat.tasks)})
            </a>'''
            
            category_sections += self._render_category_item(cat, safe_id, dashboard_base)

        # Assemble
        email = self._render_doc_start()
        manage_link = (subscriptions or {}).get("manage_link")
        email += self._render_header(date_str, manage_link)
        
        # Executive Summary
        summary_text = (
            f"This week, your organization is driving <strong>{total_tasks} work items</strong> "
            f"across <strong>{len(active_cats)} active functional areas</strong>."
        )

        email += f'''
        <tr>
            <td align="center" style="padding: 0 24px;">
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:16px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); border: 1px solid {self.COLOR_BORDER};">
                    <tr>
                        <td style="padding:32px;">
                            <h2 style="margin:0 0 16px 0; font-family:{self.FONT_SANS}; font-size:20px; color:{self.COLOR_ACCENT}; font-weight:800; letter-spacing:-0.02em;">Executive Briefing</h2>
                            <p style="margin:0 0 24px 0; font-family:{self.FONT_SANS}; font-size:16px; color:{self.COLOR_TEXT_MAIN}; line-height:1.6;">
                                Across {len(active_cats)} functional departments, the organization has recorded {total_tasks} active work items. This briefing covers the latest technical progression, architectural decisions, and critical operational updates synthesized for executive review.
                            </p>
                            
                            <div style="padding-top:24px; border-top:1px solid {self.COLOR_BORDER};">
                                <span style="font-size:11px; color:{self.COLOR_TEXT_MUTED}; text-transform:uppercase; letter-spacing:0.1em; font-weight:800; display:block; margin-bottom:12px;">In This Briefing</span>
                                {chips_html}
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr><td height="32"></td></tr>'''
        
        email += category_sections
        email += self._render_footer()
        
        return email

    def _render_doc_start(self) -> str:
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <style>
        @media only screen and (max-width: 620px) {{
            .wrapper {{ width: 100% !important; }}
            .container {{ padding: 20px !important; }}
            .mobile-font {{ font-size: 28px !important; }}
        }}
    </style>
</head>
<body style="margin:0; padding:0; background-color:{self.COLOR_BG}; font-family:{self.FONT_SANS};">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{self.COLOR_BG};">
        <tr>
            <td align="center" style="padding: 24px 0;">
                <table id="top" class="wrapper" width="600" cellpadding="0" cellspacing="0" border="0" style="width: 600px; max-width: 100%;">"""

    def _render_header(self, date_str: str, manage_link: str = None) -> str:
        manage_btn = ""
        if manage_link:
            manage_btn = f'''
            <div style="margin-top:16px;">
                <a href="{manage_link}" style="display:inline-block; color:{self.COLOR_PRIMARY}; font-size:13px; font-weight:700; text-decoration:none; padding:8px 0; border-bottom: 2px solid {self.COLOR_PRIMARY};">Adjust Preferences &rarr;</a>
            </div>'''

        return f"""
        <tr>
            <td align="left" style="padding:48px 24px;">
                <p style="margin:0; font-size:13px; color:{self.COLOR_PRIMARY}; text-transform:uppercase; letter-spacing:0.15em; font-weight:800;">Engineering Sync</p>
                <h1 class="mobile-font" style="margin:8px 0 0 0; font-size:40px; font-weight:800; color:{self.COLOR_ACCENT}; letter-spacing:-0.04em;">The Bulletin</h1>
                <div style="margin-top:8px; font-size:14px; color:{self.COLOR_TEXT_MUTED}; font-weight:500;">{date_str}</div>
                {manage_btn}
            </td>
        </tr>"""

    def _render_category_item(self, cat: CategoryData, safe_id: str, dashboard_base: str) -> str:
        dashboard_url = f"{dashboard_base}#cat-{cat.categoryId}"
        
        synthesis_html = ""
        if cat.categorySummary:
            summary = html.escape(cat.categorySummary)
            
            # Bold task subjects if they appear in the summary (for test compliance and readability)
            for t in cat.tasks:
                if t.taskSubject and t.taskSubject in summary:
                    summary = summary.replace(t.taskSubject, f"<strong>{t.taskSubject}</strong>")
            
            synthesis_html = f'''
            <tr>
                <td style="padding:0 24px 24px 24px;">
                    <div style="background-color:#f8fafc; border-radius:12px; padding:24px; border:1px solid #f1f5f9;">
                        <div style="font-size:11px; color:{self.COLOR_PRIMARY}; text-transform:uppercase; letter-spacing:0.1em; font-weight:800; margin-bottom:8px;"><strong>{html.escape(cat.categoryName)}</strong></div>
                        <div style="font-size:15px; color:{self.COLOR_TEXT_MAIN}; line-height:1.7;">{summary}</div>
                    </div>
                </td>
            </tr>'''

        return f'''
        <tr>
            <td align="center" style="padding:0 24px 32px 24px;">
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:16px; border: 1px solid {self.COLOR_BORDER}; overflow:hidden;">
                    <tr>
                        <td style="padding:24px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="left">
                                        <h3 id="{safe_id}" style="margin:0; font-size:18px; color:{self.COLOR_ACCENT}; font-weight:800; letter-spacing:-0.02em;">{html.escape(cat.categoryName)}</h3>
                                    </td>
                                    <td align="right">
                                        <a href="{dashboard_url}" style="display:inline-block; background-color:{self.COLOR_ACCENT}; color:#ffffff; padding:6px 16px; border-radius:6px; font-size:12px; font-weight:700; text-decoration:none;">{len(cat.tasks)} tasks</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    {synthesis_html}
                    <tr>
                        <td style="padding:0 24px 24px 24px; text-align:right;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="left">
                                        <a href="#top" style="font-size:11px; color:{self.COLOR_TEXT_MUTED}; text-decoration:none; font-weight:700;">&uarr; Back to Top</a>
                                    </td>
                                    <td align="right">
                                        <a href="{dashboard_url}" style="font-size:13px; color:{self.COLOR_PRIMARY}; font-weight:700; text-decoration:none;">View full workstream &rarr;</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>'''

    def _render_footer(self) -> str:
        year = datetime.datetime.now().year
        return f'''
        <tr>
            <td align="center" style="padding:48px 24px;">
                <p style="margin:0; font-size:12px; color:{self.COLOR_TEXT_MUTED}; font-weight:500;">
                    &copy; {year} ScribeEMR Engineering Operations<br>
                    Automated intelligence report generated for internal sync.
                </p>
                <div style="margin-top:24px; color:{self.COLOR_BORDER};">•••</div>
            </td>
        </tr>
        </table></td></tr></table></body></html>'''
