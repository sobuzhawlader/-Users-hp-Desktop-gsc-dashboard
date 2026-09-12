import re
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

EMAIL_SENDER = ""      # Gmail address
EMAIL_PASSWORD = ""    # Gmail App Password

def clean_text(text):
    """Sanitizes text for standard PDF core fonts (removes emojis / unsupported chars)."""
    if text is None:
        return ""
    s = str(text)
    s = re.sub(r'[\U00010000-\U0010ffff]', '', s)
    s = s.replace("’", "'").replace("‘", "'").replace('“', '"').replace('”', '"').replace("–", "-").replace("—", "-")
    return s.encode('latin-1', 'replace').decode('latin-1').strip()

class GSCReport(FPDF):
    def header(self):
        self.set_fill_color(26, 35, 126)
        self.rect(0, 0, 210, 25, 'F')
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'GSC Pro Dashboard - Performance Report', 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")} | Page {self.page_no()}', 0, 0, 'C')

    def add_section_title(self, title):
        self.set_fill_color(232, 234, 246)
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(26, 35, 126)
        clean_title = clean_text(title)
        self.cell(0, 10, clean_title, 0, 1, 'L', True)
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def add_kpi_row(self, label, value, change=None):
        self.set_font('helvetica', '', 11)
        self.cell(80, 8, clean_text(label), 1, 0, 'L')
        self.set_font('helvetica', 'B', 11)
        self.cell(50, 8, clean_text(str(value)), 1, 0, 'C')
        if change is not None:
            color = (0, 150, 0) if change >= 0 else (200, 0, 0)
            self.set_text_color(*color)
            self.cell(50, 8, f"{'+' if change >= 0 else ''}{change}%", 1, 1, 'C')
            self.set_text_color(0, 0, 0)
        else:
            self.ln()

    def add_table(self, headers, data, col_widths=None):
        if col_widths is None:
            col_widths = [190 // len(headers)] * len(headers)

        self.set_fill_color(26, 35, 126)
        self.set_text_color(255, 255, 255)
        self.set_font('helvetica', 'B', 9)

        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, clean_text(header), 1, 0, 'C', True)
        self.ln()

        self.set_text_color(0, 0, 0)
        self.set_font('helvetica', '', 8)

        for row_idx, row in enumerate(data):
            if row_idx % 2 == 0:
                self.set_fill_color(245, 245, 255)
            else:
                self.set_fill_color(255, 255, 255)

            for i, cell in enumerate(row):
                val = clean_text(str(cell))[:40]
                self.cell(col_widths[i], 7, val, 1, 0, 'L', True)
            self.ln()

def generate_pdf_report(site_url, overview, top_keywords, top_pages, 
                         quick_wins, filename=None):
    if filename is None:
        filename = f"GSC_Report_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.pdf"

    # Safely convert lists or dictionaries to DataFrames
    if not isinstance(top_keywords, pd.DataFrame):
        top_keywords = pd.DataFrame(top_keywords) if top_keywords else pd.DataFrame()
    if not isinstance(top_pages, pd.DataFrame):
        top_pages = pd.DataFrame(top_pages) if top_pages else pd.DataFrame()
    if not isinstance(quick_wins, pd.DataFrame):
        quick_wins = pd.DataFrame(quick_wins) if quick_wins else pd.DataFrame()

    pdf = GSCReport()
    pdf.add_page()

    # Site Info
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_fill_color(232, 234, 246)
    pdf.cell(0, 8, f"Site: {clean_text(site_url)}", 0, 1, 'L', True)
    pdf.cell(0, 8, f"Report Period: {datetime.now().strftime('%B %Y')}", 0, 1, 'L', True)
    pdf.ln(5)

    # Overview KPIs
    pdf.add_section_title("Performance Overview")
    pdf.add_kpi_row("Total Clicks", f"{overview.get('total_clicks', 0):,}")
    pdf.add_kpi_row("Total Impressions", f"{overview.get('total_impressions', 0):,}")
    pdf.add_kpi_row("Average CTR", f"{overview.get('avg_ctr', 0)}%")
    pdf.add_kpi_row("Average Position", f"{overview.get('avg_position', 0)}")
    pdf.ln(5)

    # Top Keywords
    if not top_keywords.empty and 'query' in top_keywords.columns:
        pdf.add_section_title("Top Keywords")
        headers = ['Keyword', 'Clicks', 'Impressions', 'CTR%', 'Position']
        col_widths = [80, 25, 35, 25, 25]
        data = []
        for _, row in top_keywords.head(15).iterrows():
            data.append([
                clean_text(str(row.get('query', '')))[:35],
                str(int(row.get('clicks', 0))),
                str(int(row.get('impressions', 0))),
                str(row.get('ctr', 0)),
                str(row.get('position', 0))
            ])
        pdf.add_table(headers, data, col_widths)
        pdf.ln(5)

    # Top Pages
    if not top_pages.empty and 'page' in top_pages.columns:
        pdf.add_section_title("Top Pages")
        headers = ['Page URL', 'Clicks', 'Impressions', 'CTR%', 'Position']
        col_widths = [80, 25, 35, 25, 25]
        data = []
        for _, row in top_pages.head(10).iterrows():
            page = str(row.get('page', ''))
            page = page[-35:] if len(page) > 35 else page
            ctr_val = row.get('avg_ctr', row.get('ctr', 0))
            pos_val = row.get('avg_position', row.get('position', 0))
            data.append([
                clean_text(page),
                str(int(row.get('clicks', 0))),
                str(int(row.get('impressions', 0))),
                str(round(float(ctr_val), 2)),
                str(round(float(pos_val), 2))
            ])
        pdf.add_table(headers, data, col_widths)
        pdf.ln(5)

    # Quick Wins
    if not quick_wins.empty and 'query' in quick_wins.columns:
        pdf.add_section_title("Quick Win Opportunities")
        headers = ['Keyword', 'Position', 'Impressions', 'Clicks']
        col_widths = [90, 30, 40, 30]
        data = []
        for _, row in quick_wins.head(10).iterrows():
            data.append([
                clean_text(str(row.get('query', '')))[:40],
                str(round(float(row.get('position', 0)), 1)),
                str(int(row.get('impressions', 0))),
                str(int(row.get('clicks', 0)))
            ])
        pdf.add_table(headers, data, col_widths)

    pdf.output(filename)
    return filename

def send_email_report(recipient_email, site_url, pdf_path):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("Email not configured!")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = recipient_email
        msg['Subject'] = f"GSC Monthly Report - {clean_text(site_url)} - {datetime.now().strftime('%B %Y')}"

        body = f"""
Dear Client,

Please find attached your monthly GSC Performance Report for {site_url}.

Report Summary:
- Period: {datetime.now().strftime('%B %Y')}
- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Best regards,
GSC Pro Dashboard
        """
        msg.attach(MIMEText(body, 'plain'))

        with open(pdf_path, 'rb') as f:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 
                                 f'attachment; filename={pdf_path}')
            msg.attach(attachment)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, recipient_email, msg.as_string())
        server.quit()

        print(f"Email sent to {recipient_email}!")
        return True

    except Exception as e:
        print(f"Email error: {e}")
        return False