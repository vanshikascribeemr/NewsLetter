from typing import List
import html
import datetime
from .models import CategoryData, Task

class HTMLGenerator:
    """
    Generates an optimized, visually engaging HTML email.
    Updated: Size-optimized to prevent Gmail clipping on large data sets.
    """
    
    # --- DESIGN TOKENS ---
    COLOR_BG = "#E5E5E5" 
    COLOR_CONTAINER = "#FFFFFF"
    COLOR_PRIMARY = "#FCA311"
    COLOR_PRIMARY_DARK = "#d48806"
    COLOR_ACCENT = "#14213D" 
    COLOR_TEXT_MAIN = "#000000"
    COLOR_TEXT_MUTED = "#4b5563"
    COLOR_BORDER = "#d1d5db"
    
    FONT_SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"
    STYLE_BADGE_BASE = "display:inline-block; padding:4px 8px; border-radius:12px; font-size:11px; font-weight:bold; text-transform:uppercase; letter-spacing:0.5px;"
    
    def generate(self, categories: List[CategoryData]) -> str:
        date_str = datetime.datetime.now().strftime("%B %d, %Y")
        total_tasks = sum(len(c.tasks) for c in categories)
        total_cats = sum(1 for c in categories if c.tasks)
        
        # Build Category Navigation Chips
        chips_html = ""
        category_sections = ""
        seen_ids = set()
        
        for i, cat in enumerate(categories):
            if not cat.tasks: continue
            
            base_id = str(cat.categoryId) if cat.categoryId else f"index-{i}"
            safe_id = f"cat-{base_id}"
            counter = 1
            while safe_id in seen_ids:
                safe_id = f"cat-{base_id}-{counter}"
                counter += 1
            seen_ids.add(safe_id)
            
            chips_html += f'<a href="#{safe_id}" style="display:inline-block; text-decoration:none; background-color:#eff6ff; color:#2563eb; padding:5px 12px; border-radius:15px; font-size:12px; margin:0 5px 5px 0; font-weight:600;">{html.escape(cat.categoryName)} ({len(cat.tasks)})</a>'
            
            category_sections += self._render_category_new(cat, safe_id)

        # Assemble high-level components
        email = self._render_doc_start()
        email += self._render_header(date_str)
        
        # Summary Section (Formatted separately to avoid overall format conflicts)
        summary_block = f"""
        <tr>
            <td align="center" style="padding: 0 20px;">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%;">
                    <tr><td height="30" style="font-size:30px; line-height:30px;">&nbsp;</td></tr>
                    <tr>
                        <td align="left" style="background-color:#ffffff; padding:30px; border-radius:8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <h2 style="margin:0 0 15px 0; font-family:{self.FONT_SANS}; font-size:20px; color:#1f2937;">Executive Summary</h2>
                            <p style="margin:0 0 20px 0; font-family:{self.FONT_SANS}; font-size:15px; color:#4b5563; line-height:1.5;">
                                Here is the weekly engineering update. Tracking <strong>{total_tasks} active tasks</strong> across <strong>{total_cats} categories</strong>.
                            </p>
                            <div>{chips_html}</div>
                        </td>
                    </tr>
                    <tr><td height="20" style="font-size:20px; line-height:20px;">&nbsp;</td></tr>
                </table>
            </td>
        </tr>"""
        
        email += summary_block
        email += category_sections
        email += self._render_footer()
        
        return email

    def _render_doc_start(self) -> str:
        return f'<!DOCTYPE html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/></head><body style="margin:0; padding:0; background-color:{self.COLOR_BG}; font-family:{self.FONT_SANS};"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center"><table width="600" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;">'

    def _render_header(self, date_str: str) -> str:
        glass_style = "display:inline-block; background-color:rgba(0,0,0,0.2); color:#ffffff; padding:6px 16px; border-radius:24px; font-size:14px; font-weight:700; border:1px solid rgba(255,255,255,0.4);"
        return f"""
        <tr>
            <td align="center" style="background-color:{self.COLOR_PRIMARY}; padding:50px 20px; border-radius:0 0 24px 24px; background-image: linear-gradient(135deg, {self.COLOR_PRIMARY}, {self.COLOR_PRIMARY_DARK});">
                <a name="top"></a>
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td align="left">
                            <p style="margin:0; font-size:13px; color:#14213d; text-transform:uppercase; letter-spacing:1.5px; font-weight:700;">Engineering Sync</p>
                            <h1 style="margin:10px 0 0 0; font-size:36px; font-weight:800; color:{self.COLOR_ACCENT}; letter-spacing:-1px;">Weekly Bulletin</h1>
                        </td>
                        <td align="right" style="vertical-align:bottom;">
                            <span style="{glass_style}">{date_str}</span>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>"""

    def _render_category_new(self, cat: CategoryData, safe_id: str) -> str:
        rows = "".join(self._render_task_rows(task, "#ffffff" if i % 2 == 0 else "#fbfcfd") for i, task in enumerate(cat.tasks))
        glass_style = "display:inline-block; background-color:rgba(0,0,0,0.2); color:#ffffff; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:800; border:1px solid rgba(255,255,255,0.4);"
        
        return f"""
        <tr>
            <td align="center" style="padding:0 20px;">
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:40px; border:1px solid {self.COLOR_BORDER}; border-radius:12px; overflow:hidden; background-color:#ffffff;">
                    <tr>
                        <td colspan="5" style="background-color:{self.COLOR_PRIMARY}; padding:15px 20px; background-image: linear-gradient(to right, {self.COLOR_PRIMARY}, {self.COLOR_PRIMARY_DARK});">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="left">
                                        <h3 style="margin:0; font-size:18px; color:#14213d; text-transform:uppercase; letter-spacing:1px; font-weight:800;">
                                            <a name="{safe_id}" style="color:#14213d; text-decoration:none;">{html.escape(cat.categoryName)}</a>
                                        </h3>
                                    </td>
                                    <td align="right"><span style="{glass_style}">{len(cat.tasks)} Tasks</span></td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr style="background-color:#f8f9fc;">
                        <th align="left" style="padding:12px 20px; font-size:11px; color:{self.COLOR_TEXT_MUTED}; text-transform:uppercase; font-weight:800; border-bottom:1px solid {self.COLOR_BORDER};">ID</th>
                        <th align="left" style="padding:12px 20px; font-size:11px; color:{self.COLOR_TEXT_MUTED}; text-transform:uppercase; font-weight:800; border-bottom:1px solid {self.COLOR_BORDER};" width="45%">Detail</th>
                        <th align="left" style="padding:12px 20px; font-size:11px; color:{self.COLOR_TEXT_MUTED}; text-transform:uppercase; font-weight:800; border-bottom:1px solid {self.COLOR_BORDER};">Assignee</th>
                        <th align="center" style="padding:12px 20px; font-size:11px; color:{self.COLOR_TEXT_MUTED}; text-transform:uppercase; font-weight:800; border-bottom:1px solid {self.COLOR_BORDER};">Priority</th>
                        <th align="center" style="padding:12px 20px; font-size:11px; color:{self.COLOR_TEXT_MUTED}; text-transform:uppercase; font-weight:800; border-bottom:1px solid {self.COLOR_BORDER};">Status</th>
                    </tr>
                    {rows}
                </table>
                <div style="text-align:left; padding:0 20px 30px 50px;">
                    <a href="#top" style="font-size:12px; color:#14213d; text-decoration:none; font-weight:800; text-transform:uppercase;">&uarr; Back to Top</a>
                </div>
            </td>
        </tr>"""

    def _render_task_rows(self, task: Task, bg_color: str) -> str:
        p_color = "#de350b" if "High" in task.taskPriority else "#ffd100" if "Medium" in task.taskPriority else "#00875a"
        summary = task.summarizedComments or "No changes reported over the last 7 days."
        up_bg = "#f7faff" if task.summarizedComments else "#fafbfc"
        
        return f"""
        <tr style="background-color:{bg_color};">
            <td align="left" style="padding:15px 20px 10px 20px; font-family:monospace; font-size:12px; font-weight:bold; color:{self.COLOR_TEXT_MUTED}; vertical-align:top;">#{task.taskId}</td>
            <td align="left" style="padding:15px 20px 10px 20px; font-size:13px; color:{self.COLOR_TEXT_MAIN}; vertical-align:top; line-height:1.4;">{html.escape(task.taskSubject)}</td>
            <td align="left" style="padding:15px 20px 10px 20px; font-size:13px; color:{self.COLOR_TEXT_MUTED}; vertical-align:top;">{html.escape(task.assigneeName)}</td>
            <td align="center" style="padding:15px 20px 10px 20px; vertical-align:top;">
                <span style="{self.STYLE_BADGE_BASE} color:{p_color}; border:1px solid {p_color}; background-color:#fff;">{html.escape(task.taskPriority)}</span>
            </td>
            <td align="center" style="padding:15px 20px 10px 20px; vertical-align:top;">
                <span style="{self.STYLE_BADGE_BASE} background-color:#f4f5f7; color:#42526e;">{html.escape(task.taskStatus)}</span>
            </td>
        </tr>
        <tr style="background-color:{bg_color};">
            <td colspan="5" style="padding: 0 20px 15px 20px; border-bottom:1px solid {self.COLOR_BORDER};">
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color:{up_bg}; border-left:4px solid {self.COLOR_PRIMARY};">
                    <tr>
                        <td style="padding:12px 16px; font-size:13px; color:#42526e; line-height:1.6; font-style:italic;">
                            <strong style="color:#14213d; font-style:normal; font-size:11px; text-transform:uppercase; margin-right:8px;">Update:</strong>{html.escape(summary)}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>"""

    def _render_footer(self) -> str:
        year = datetime.datetime.now().year
        return f"""
        <tr><td align="center" style="padding:40px 20px;">
            <p style="margin:0; font-size:12px; color:{self.COLOR_TEXT_MUTED}; text-align:center;">
                &copy; {year} ScribeEMR Engineering. All rights reserved.<br>Generated automatically.
            </p>
        </td></tr></table></td></tr></table></body></html>"""
