from pathlib import Path
import html
import os
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Resolve paths (works both standalone and inside submission package)
root = Path(__file__).resolve().parent
folder = Path(os.environ.get('VECTOR_REPORT_DIR', str(root.parent / 'report')))
stem = os.environ.get('VECTOR_REPORT_STEM', '51295903131_赵信喆_系统优化课程报告')
md_path = folder / (stem + '.md')
pdf_path = folder / (stem + '.pdf')
text = md_path.read_text(encoding='utf-8')

# Register fonts (works seamlessly on Windows, WSL, and pure Linux servers)
fontroot = 'C:/Windows/Fonts' if os.name == 'nt' else '/mnt/c/Windows/Fonts'
linux_cjk_fallbacks = [
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/arphic/uming.ttc',
]


def pick_font(env_var, candidates, default_fallback=None):
    env_p = os.environ.get(env_var)
    if env_p and Path(env_p).exists():
        return env_p
    for c in candidates:
        p = Path(c) if Path(c).is_absolute() else (Path(fontroot) / c)
        if p.exists():
            return str(p)
    if default_fallback and Path(default_fallback).exists():
        return default_fallback
    for lf in linux_cjk_fallbacks:
        if Path(lf).exists():
            return lf
    raise FileNotFoundError(f'No usable CJK font found for {env_var}; set VECTOR_REPORT_FONT.')


song_path = pick_font('VECTOR_REPORT_FONT', ['simsun.ttc', 'STSONG.TTF', 'msyh.ttc'])
hei_path = pick_font('VECTOR_REPORT_BOLD_FONT', ['msyhbd.ttc', 'simhei.ttf', 'Dengb.ttf'], default_fallback=song_path)
yahei_path = pick_font('VECTOR_REPORT_SANS_FONT', ['msyh.ttc', 'Deng.ttf', 'simhei.ttf'], default_fallback=song_path)
mono_path = pick_font('VECTOR_REPORT_MONO_FONT', ['consola.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 'msyh.ttc'], default_fallback=song_path)

pdfmetrics.registerFont(TTFont('Song', song_path, subfontIndex=0))
pdfmetrics.registerFont(TTFont('Hei', hei_path, subfontIndex=0))
pdfmetrics.registerFont(TTFont('YaHei', yahei_path, subfontIndex=0))
pdfmetrics.registerFont(TTFont('Mono', mono_path, subfontIndex=0))
pdfmetrics.registerFontFamily('Song', normal='Song', bold='Hei', italic='Song', boldItalic='Hei')

# Palette
NAVY = colors.HexColor('#1e3a5f')
ACCENT = colors.HexColor('#2563eb')
SLATE = colors.HexColor('#475569')
DARK = colors.HexColor('#0f172a')
ROW_ALT = colors.HexColor('#f8fafc')
HEADER_BG = colors.HexColor('#eaf0f6')
CALLOUT_BG = colors.HexColor('#f4f7fb')
BORDER_LIGHT = colors.HexColor('#cbd5e1')

# Page geometry
PAGE_W, PAGE_H = A4
LEFT_M, RIGHT_M = 50, 50
TOP_M, BOTTOM_M = 46, 43
CONTENT_W = PAGE_W - LEFT_M - RIGHT_M  # ~495 pt

styles = {
    'title': ParagraphStyle(
        'title', fontName='Hei', fontSize=18.0, leading=25,
        textColor=NAVY, alignment=1, spaceAfter=6
    ),
    'meta': ParagraphStyle(
        'meta', fontName='YaHei', fontSize=9.3, leading=14,
        textColor=SLATE, alignment=1, spaceAfter=4
    ),
    'h2': ParagraphStyle(
        'h2', fontName='Hei', fontSize=12.6, leading=18.2,
        textColor=NAVY, spaceBefore=10.5, spaceAfter=4.0, keepWithNext=True
    ),
    'h3': ParagraphStyle(
        'h3', fontName='Hei', fontSize=10.6, leading=15.2,
        textColor=colors.HexColor('#1e40af'), spaceBefore=7.8, spaceAfter=3.2, keepWithNext=True
    ),
    'h4': ParagraphStyle(
        'h4', fontName='Hei', fontSize=9.6, leading=13.8,
        textColor=DARK, spaceBefore=5.5, spaceAfter=2.2, keepWithNext=True
    ),
    'body': ParagraphStyle(
        'body', fontName='Song', fontSize=9.8, leading=14.4,
        textColor=DARK, spaceAfter=3.4, wordWrap='CJK'
    ),
    'abstract': ParagraphStyle(
        'abstract', fontName='Song', fontSize=9.3, leading=13.8,
        textColor=DARK, spaceAfter=3.2, wordWrap='CJK'
    ),
    'bullet': ParagraphStyle(
        'bullet', fontName='Song', fontSize=9.6, leading=14.1,
        textColor=DARK, leftIndent=14, firstLineIndent=-10, spaceAfter=2.7, wordWrap='CJK'
    ),
    'subbullet': ParagraphStyle(
        'subbullet', fontName='Song', fontSize=9.3, leading=13.6,
        textColor=DARK, leftIndent=26, firstLineIndent=-10, spaceAfter=2.1, wordWrap='CJK'
    ),
    'cell': ParagraphStyle(
        'cell', fontName='Song', fontSize=8.0, leading=11.2,
        textColor=DARK, wordWrap='CJK'
    ),
    'cell_head': ParagraphStyle(
        'cell_head', fontName='Hei', fontSize=8.1, leading=11.2,
        textColor=NAVY, wordWrap='CJK'
    ),
    'cell_dense': ParagraphStyle(
        'cell_dense', fontName='Song', fontSize=7.5, leading=10.3,
        textColor=DARK, wordWrap='CJK'
    ),
    'cell_head_dense': ParagraphStyle(
        'cell_head_dense', fontName='Hei', fontSize=7.6, leading=10.3,
        textColor=NAVY, wordWrap='CJK'
    ),
    'caption': ParagraphStyle(
        'caption', fontName='YaHei', fontSize=8.4, leading=12.2,
        textColor=SLATE, alignment=1, spaceBefore=2, spaceAfter=6, wordWrap='CJK'
    ),
    'ref': ParagraphStyle(
        'ref', fontName='Song', fontSize=8.9, leading=13.0,
        textColor=DARK, leftIndent=18, firstLineIndent=-18, spaceAfter=2.2, wordWrap='CJK'
    ),
}

def format_inline(t: str) -> str:
    # Protect inline code first so regexes don't mangle code
    codes = []

    def stash_code(m):
        idx = len(codes)
        codes.append(f'<font name="Mono" size="8.4" color="#1e3a5f">{html.escape(m.group(1))}</font>')
        return f'@@CODE{idx}@@'

    t = re.sub(r'`([^`]+)`', stash_code, t)
    safe = html.escape(t)

    # Markdown links [text](url)
    safe = re.sub(
        r'\[([^\]]+)\]\((https?://[^\s)]+)\)',
        lambda m: f'<link href="{m.group(2)}" color="#2563eb"><u>{m.group(1)}</u></link>',
        safe,
    )
    # Bold **text**
    safe = re.sub(r'\*\*([^*]+)\*\*', lambda m: f'<font name="Hei">{m.group(1)}</font>', safe)

    # Clean mathematical superscripts/subscripts & symbols in prose (all glyphs verified in SimSun/YaHei)
    safe = safe.replace('2^24', '2<sup>24</sup>').replace('2^31', '2<sup>31</sup>').replace('255^2', '255<sup>2</sup>')
    safe = safe.replace('||x - q||^2', '‖x - q‖<sup>2</sup>')
    safe = safe.replace('||x||^2', '‖x‖<sup>2</sup>').replace('||q||^2', '‖q‖<sup>2</sup>')
    safe = safe.replace('d_{2j}^2', 'd<sub>2j</sub><sup>2</sup>').replace('d_{2j+1}^2', 'd<sub>2j+1</sub><sup>2</sup>')
    safe = safe.replace('d_i^2', 'd<sub>i</sub><sup>2</sup>')
    safe = safe.replace('d_i', 'd<sub>i</sub>').replace('x_i', 'x<sub>i</sub>').replace('q_i', 'q<sub>i</sub>')
    safe = safe.replace('w_i', 'w<sub>i</sub>').replace('Δt_i', 'Δt<sub>i</sub>')
    safe = safe.replace('y_r', 'y<sub>r</sub>').replace('Q_batch', 'Q<sub>batch</sub>')
    safe = safe.replace('&lt;=', '≤').replace('&gt;=', '≥')
    safe = safe.replace('1e-5', '10<sup>-5</sup>').replace('1e-4', '10<sup>-4</sup>').replace('1e-6', '10<sup>-6</sup>')
    safe = safe.replace('1.63e-7', '1.63×10<sup>-7</sup>').replace('2.22e-16', '2.22×10<sup>-16</sup>')

    # Restore code spans
    for idx, c in enumerate(codes):
        safe = safe.replace(f'@@CODE{idx}@@', c)

    return safe


def P(t: str, style: str = 'body') -> Paragraph:
    return Paragraph(format_inline(t), styles[style])


def compute_col_widths(raw_rows):
    ncols = len(raw_rows[0])

    def text_weight(s):
        s = re.sub(r'\*\*|`', '', s)
        return sum(1.72 if ord(ch) > 127 else 0.92 for ch in s)

    def max_ascii_token(s):
        s = re.sub(r'\*\*|`', '', s)
        toks = re.findall(r'[A-Za-z0-9_.\-×/]+', s)
        return max((len(tok) * 0.95 for tok in toks), default=0.0)

    max_w = [0.0] * ncols
    min_tok = [0.0] * ncols
    for r_idx, row in enumerate(raw_rows):
        for c_idx, cell in enumerate(row):
            w = text_weight(cell)
            if r_idx == 0:
                w = max(w, 6.0)
            max_w[c_idx] = max(max_w[c_idx], min(w, 34.0))
            min_tok[c_idx] = max(min_tok[c_idx], min(max_ascii_token(cell) + 2.0, 15.0))
    weights = [max(w, t, 7.2) for w, t in zip(max_w, min_tok)]
    total = sum(weights)
    return [CONTENT_W * (w / total) for w in weights]


story = []
lines = text.splitlines()
i = 0
fig_counter = 0
in_abstract = False
abstract_paras = []
in_refs = False
meta_lines = []
doc_h1_title = None


def flush_abstract():
    global in_abstract, abstract_paras
    if abstract_paras:
        hdr = Paragraph('<font name="Hei" size="10.6" color="#1e3a5f">摘　要</font>', styles['abstract'])
        box_data = [[[hdr] + abstract_paras]]
        tbl = Table(box_data, colWidths=[CONTENT_W])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CALLOUT_BG),
            ('LINEBEFORE', (0, 0), (0, -1), 3.0, NAVY),
            ('LEFTPADDING', (0, 0), (-1, -1), 11),
            ('RIGHTPADDING', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 7.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6.5),
        ]))
        story.extend([tbl, Spacer(1, 7)])
        abstract_paras = []
    in_abstract = False


while i < len(lines):
    raw_line = lines[i]
    line = raw_line.strip()
    i += 1
    if not line:
        continue

    # Title
    if line.startswith('# '):
        doc_h1_title = line[2:].strip()
        story.append(P(doc_h1_title, 'title'))
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                i += 1
                continue
            if nxt.startswith('姓名：') or nxt.startswith('课程：'):
                meta_lines.append(nxt)
                i += 1
            else:
                break
        if meta_lines:
            story.append(P('　｜　'.join(meta_lines), 'meta'))
            story.append(Spacer(1, 2))
            story.append(HRFlowable(width='100%', thickness=1.2, color=NAVY, spaceBefore=2, spaceAfter=9))
        continue

    # H2
    if line.startswith('## '):
        flush_abstract()
        heading = line[3:].strip()
        if heading == '摘要':
            in_abstract = True
            continue
        in_refs = (heading == '参考材料')
        hr = HRFlowable(width='100%', thickness=0.6, color=BORDER_LIGHT, spaceBefore=0, spaceAfter=4.5)
        hr.keepWithNext = True
        story.append(P(heading, 'h2'))
        story.append(hr)
        continue

    # H3 / H4
    if line.startswith('### '):
        flush_abstract()
        story.append(P(line[4:].strip(), 'h3'))
        continue
    if line.startswith('#### '):
        flush_abstract()
        story.append(P(line[5:].strip(), 'h4'))
        continue

    # Tables
    if line.startswith('|'):
        flush_abstract()
        raw_rows = []
        tbl_lines = [line]
        while i < len(lines) and lines[i].strip().startswith('|'):
            tbl_lines.append(lines[i].strip())
            i += 1
        for row in tbl_lines:
            if re.match(r'^\|[\s:|\-]+\|$', row):
                continue
            raw_rows.append([c.strip() for c in row.strip('|').split('|')])
        col_widths = compute_col_widths(raw_rows)
        is_dense = (len(raw_rows[0]) >= 7 or len(raw_rows) >= 16)
        data_rows = []
        for r_idx, row in enumerate(raw_rows):
            if is_dense:
                st = 'cell_head_dense' if r_idx == 0 else 'cell_dense'
            else:
                st = 'cell_head' if r_idx == 0 else 'cell'
            data_rows.append([P(c, st) for c in row])

        pad_x = 3.6 if is_dense else 4.8
        pad_y = 3.0 if len(data_rows) > 10 else 4.2
        tstyle = [
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('LINEABOVE', (0, 0), (-1, 0), 1.1, NAVY),
            ('LINEBELOW', (0, 0), (-1, 0), 0.8, NAVY),
            ('LINEBELOW', (0, -1), (-1, -1), 1.0, NAVY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), pad_x),
            ('RIGHTPADDING', (0, 0), (-1, -1), pad_x),
            ('TOPPADDING', (0, 0), (-1, -1), pad_y),
            ('BOTTOMPADDING', (0, 0), (-1, -1), pad_y),
        ]
        for r_idx in range(1, len(data_rows)):
            if r_idx % 2 == 0:
                tstyle.append(('BACKGROUND', (0, r_idx), (-1, r_idx), ROW_ALT))
        table = Table(data_rows, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle(tstyle))
        if len(data_rows) <= 10 and story and isinstance(story[-1], Paragraph) and story[-1].style.name == 'h4':
            hdr_h4 = story.pop()
            story.append(KeepTogether([hdr_h4, table, Spacer(1, 6.5)]))
        elif len(data_rows) <= 10:
            story.append(KeepTogether([table, Spacer(1, 6.5)]))
        else:
            story.extend([table, Spacer(1, 6.5)])
        continue

    # Images + Caption
    if line.startswith('!['):
        flush_abstract()
        m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
        assert m, line
        fig_counter += 1
        alt_text, rel_path = m.group(1).strip(), m.group(2).strip()
        # Strip manual '图N：' prefix from alt_text if present to avoid double numbering
        alt_text = re.sub(r'^图\s*\d+\s*[：:]\s*', '', alt_text)
        img_path = folder / rel_path
        iw, ih = ImageReader(str(img_path)).getSize()
        scale = min(CONTENT_W / iw, 268.0 / ih)
        img_flow = Image(str(img_path), width=iw * scale, height=ih * scale)
        img_flow.hAlign = 'CENTER'

        cap_desc = alt_text
        look = i
        while look < len(lines) and not lines[look].strip():
            look += 1
        if look < len(lines) and (lines[look].strip().startswith('图中') or re.match(r'^图\s*\d+\s*[：:]', lines[look].strip())):
            extra = re.sub(r'^图\s*\d+\s*[：:]\s*', '', lines[look].strip())
            cap_desc = f'{alt_text}。{extra}'
            i = look + 1

        cap_para = P(f'**图 {fig_counter}**：{cap_desc}', 'caption')
        story.append(KeepTogether([Spacer(1, 3.5), img_flow, Spacer(1, 3.5), cap_para]))
        continue

    # Sub-bullets
    if raw_line.startswith('  - ') or raw_line.startswith('    - '):
        flush_abstract()
        story.append(P('◦  ' + line[2:].strip(), 'subbullet'))
        continue

    # Top-level bullets
    if line.startswith('- '):
        flush_abstract()
        story.append(P('•  ' + line[2:].strip(), 'bullet'))
        continue

    # Numbered lists
    m_num = re.match(r'^(\d+)\.\s+(.*)$', line)
    if m_num:
        flush_abstract()
        story.append(P(f'**{m_num.group(1)}.** {m_num.group(2)}', 'bullet'))
        continue

    if in_abstract:
        abstract_paras.append(P(line, 'abstract'))
    elif in_refs:
        story.append(P(line, 'ref'))
    else:
        story.append(P(line, 'body'))

flush_abstract()

default_title = doc_h1_title or '面向 CPU 精确向量检索的跨层优化与跨机器自动校准'
report_title = os.environ.get('VECTOR_REPORT_TITLE', default_title)
report_subtitle = os.environ.get('VECTOR_REPORT_SUBTITLE', '软件系统优化课程项目研究报告')


def draw_header_footer(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont('YaHei', 8.0)
        canvas.setFillColor(SLATE)
        canvas.drawString(LEFT_M, PAGE_H - 30, report_title)
        canvas.drawRightString(PAGE_W - RIGHT_M, PAGE_H - 30, report_subtitle)
        canvas.setStrokeColor(BORDER_LIGHT)
        canvas.setLineWidth(0.5)
        canvas.line(LEFT_M, PAGE_H - 35, PAGE_W - RIGHT_M, PAGE_H - 35)
    canvas.setStrokeColor(BORDER_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(LEFT_M, 34, PAGE_W - RIGHT_M, 34)
    canvas.setFont('YaHei', 8.0)
    canvas.setFillColor(SLATE)
    footer_left = os.environ.get('VECTOR_REPORT_FOOTER', '赵信喆  51295903131  软件系统优化')
    canvas.drawString(LEFT_M, 21, footer_left)
    canvas.drawRightString(PAGE_W - RIGHT_M, 21, f'第 {doc.page} 页')
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(pdf_path),
    pagesize=A4,
    rightMargin=RIGHT_M,
    leftMargin=LEFT_M,
    topMargin=TOP_M,
    bottomMargin=BOTTOM_M,
    title=report_title,
    author=os.environ.get('VECTOR_REPORT_AUTHOR', '赵信喆'),
)
doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
print('Rendered PDF successfully:', pdf_path)
