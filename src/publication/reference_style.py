"""Reference-inspired Chinese journal typesetting with native Word tables/math.

This module changes presentation only. The supplied reference geometry is not
claimed to be a university's submission template.
"""
from __future__ import annotations
import json
import re
from copy import deepcopy
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.shared import Mm, Pt, RGBColor

BEGIN='R3WIDEBEGIN'
END='R3WIDEEND'
BODY='R3BODYSTART'
BACK='R3BACKMATTER'


def load_profile(path):
    p=json.loads(Path(path).read_text(encoding='utf-8'))
    width=p['page_mm'][0]-p['margins_mm']['left']-p['margins_mm']['right']
    if p['body_columns'] not in (1,2) or p['figure_width_mm']>width:
        raise ValueError('Invalid reference layout profile')
    return p


def installed_fonts(profile):
    from matplotlib import font_manager
    available={f.name for f in font_manager.fontManager.ttflist}
    found={}
    for role,choices in profile['font_candidates'].items():
        selected=next((x for x in choices if x in available),None)
        if selected is None:raise RuntimeError(f'No installed {role} font from {choices}; install an authorized font')
        found[role]=selected
    return found


def set_font(style,cn,en,size,bold=False):
    style.font.name=en;style.font.size=Pt(size);style.font.bold=bold;style.font.italic=False
    style.font.color.rgb=RGBColor(0,0,0)
    rpr=style.element.get_or_add_rPr();fonts=rpr.rFonts
    if fonts is None:fonts=OxmlElement('w:rFonts');rpr.insert(0,fonts)
    for key in ('ascii','hAnsi','cs'):fonts.set(qn('w:'+key),en)
    fonts.set(qn('w:eastAsia'),cn)


def template(profile,fonts,path):
    doc=Document();s=doc.sections[0]
    s.page_width=Mm(profile['page_mm'][0]);s.page_height=Mm(profile['page_mm'][1])
    for key,value in profile['margins_mm'].items():setattr(s,key+'_margin',Mm(value))
    s.header_distance=s.footer_distance=Mm(12)
    for name,size,bold in [('Normal',profile['body_font_pt'],False),('Title',profile['title_font_pt'],True),
                           ('Subtitle',12,False),('Heading 1',12,True),('Heading 2',10.5,True),
                           ('Heading 3',10.5,True),('Caption',profile['caption_font_pt'],False)]:
        set_font(doc.styles[name],fonts['heading'] if bold else fonts['body'],fonts['latin'],size,bold)
    normal=doc.styles['Normal'].paragraph_format
    normal.line_spacing=Pt(profile['line_spacing_pt']);normal.space_after=Pt(0)
    normal.first_line_indent=Pt(2*profile['body_font_pt']);normal.widow_control=True
    for name in ('Heading 1','Heading 2','Heading 3'):
        pf=doc.styles[name].paragraph_format;pf.first_line_indent=Pt(0)
        pf.space_before=Pt(7);pf.space_after=Pt(3);pf.keep_with_next=True
        pf.page_break_before=False
    for name in ('Title','Subtitle','Caption'):
        pf=doc.styles[name].paragraph_format;pf.first_line_indent=Pt(0)
        pf.alignment=WD_ALIGN_PARAGRAPH.CENTER;pf.keep_with_next=True
    foot=s.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=foot.add_run();fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),' PAGE ');run._r.addnext(fld)
    settings=doc.settings.element
    if settings.find(qn('w:doNotAutoHyphenate')) is None:
        flag=OxmlElement('w:doNotAutoHyphenate');settings.append(flag)
    doc.save(path)


def _section(base,cols,gap):
    el=deepcopy(base)
    for node in list(el):
        if node.tag in {qn('w:type'),qn('w:cols')}:el.remove(node)
    typ=OxmlElement('w:type');typ.set(qn('w:val'),'continuous');el.append(typ)
    columns=OxmlElement('w:cols');columns.set(qn('w:num'),str(cols));columns.set(qn('w:space'),str(round(gap/25.4*1440)))
    el.append(columns)
    order=['headerReference','footerReference','footnotePr','endnotePr','type','pgSz','pgMar','paperSrc','pgBorders','lnNumType','pgNumType','cols','formProt','vAlign','noEndnote','titlePg','textDirection','bidi','rtlGutter','docGrid','printerSettings','sectPrChange']
    children=list(el)
    for child in children:el.remove(child)
    for child in sorted(children,key=lambda c:order.index(c.tag.split('}')[-1]) if c.tag.split('}')[-1] in order else 100):el.append(child)
    return el


def _boundary(paragraph,base,cols,gap):
    paragraph.clear();pf=paragraph.paragraph_format
    pf.space_before=pf.space_after=Pt(0);pf.line_spacing=Pt(1)
    pf.first_line_indent=Pt(0);pf.keep_with_next=False
    r=paragraph.add_run();r.font.size=Pt(1)
    ppr=paragraph._p.get_or_add_pPr()
    ppr.append(_section(base,cols,gap))


def _rule(parent,tag,points):
    node=OxmlElement(tag);node.set(qn('w:val'),'single' if points else 'nil')
    if points:node.set(qn('w:sz'),str(round(points*8)));node.set(qn('w:color'),'000000')
    parent.append(node)


def three_line_table(table,profile,width_mm):
    table.alignment=WD_TABLE_ALIGNMENT.CENTER;table.autofit=False
    n=len(table.columns)
    # Wider first column for labels, equally sized numeric columns.
    headers=[c.text for c in table.rows[0].cells]
    weights=([1.0,2.0,.9,1.5] if any('原始口径' in h for h in headers) else
             [1.8,1.,1.,1.] if any('频率与主力' in h for h in headers) else
             [1.3,.8,.5,1.3,1.3,.8] if n==6 and 'RMSE' in ''.join(headers) else [1.4]+[1]*(n-1))
    widths=[width_mm*w/sum(weights) for w in weights]
    pr=table._tbl.tblPr
    for old in list(pr):
        if old.tag in {qn('w:tblBorders'),qn('w:tblW'),qn('w:shd')}:pr.remove(old)
    tw=OxmlElement('w:tblW');tw.set(qn('w:type'),'dxa');tw.set(qn('w:w'),str(round(width_mm/25.4*1440)));pr.append(tw)
    borders=OxmlElement('w:tblBorders')
    for name,points in [('top',1),('bottom',1),('left',0),('right',0),('insideH',0),('insideV',0)]:_rule(borders,'w:'+name,points)
    pr.append(borders)
    for j,col in enumerate(table.columns):col.width=Mm(widths[j])
    for i,row in enumerate(table.rows):
        rpr=row._tr.get_or_add_trPr()
        cant=OxmlElement('w:cantSplit');rpr.append(cant)
        if i==0:
            repeat=OxmlElement('w:tblHeader');rpr.append(repeat)
        for j,cell in enumerate(row.cells):
            cell.width=Mm(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cp=cell._tc.get_or_add_tcPr()
            for old in list(cp):
                if old.tag in {qn('w:tcBorders'),qn('w:shd')}:cp.remove(old)
            cb=OxmlElement('w:tcBorders')
            for name in ('top','left','right','bottom'):
                points=1 if (i==0 and name=='top') or (i==len(table.rows)-1 and name=='bottom') else .5 if i==0 and name=='bottom' else 0
                _rule(cb,'w:'+name,points)
            cp.append(cb)
            for p in cell.paragraphs:
                p.style='Normal'
                p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_after=Pt(2)
                p.paragraph_format.space_before=Pt(2);p.paragraph_format.line_spacing=1.12
                p.paragraph_format.keep_with_next=True
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER if i==0 else WD_ALIGN_PARAGRAPH.RIGHT if re.fullmatch(r'[\d,.%−+— \-/]+',p.text.strip()) else WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:r.font.size=Pt(profile['table_font_pt']);r.bold=i==0;r.font.color.rgb=RGBColor(0,0,0)


def wrap_markdown(text):
    text=text.replace('<!-- R3_WIDE_BEGIN -->',BEGIN).replace('<!-- R3_WIDE_END -->',END)
    text=text.replace('# 一、引言',BODY+'\n\n# 一、引言',1)
    text=text.replace('# 参考文献',BACK+'\n\n# 参考文献',1)
    # Each display equation is a short full-width block; number from explicit tag.
    def equation(m):
        expr=m[1].strip();tag=re.search(r'\\tag\{([^{}]+)\}',expr)
        if not tag:raise ValueError('Every display equation needs an explicit tag')
        expr=expr[:tag.start()]+expr[tag.end():]
        # Explicit paired delimiters avoid literal-brace conversion errors in Word/LibreOffice.
        expr=re.sub(r'(?<!left)\\\{',lambda _:r'\left\{',expr)
        expr=re.sub(r'(?<!right)\\\}',lambda _:r'\right\}',expr)
        return f'\n{BEGIN}\n\n$${expr}$$\n\nR3EQNUMBER_{tag[1]}\n\n{END}\n'
    text=re.sub(r'\$\$(.*?)\$\$',equation,text,flags=re.S)
    text=re.sub(BEGIN+r'\s*'+END,'',text)
    text=re.sub(END+r'\s*'+BEGIN,'',text)
    return text


def polish(path,profile,fonts,preview=False):
    doc=Document(path);body=doc.element.body;base=deepcopy(body.sectPr)
    full=profile['page_mm'][0]-profile['margins_mm']['left']-profile['margins_mm']['right']
    cols=1;stack=[];equations=0;last_math=None
    paras=list(doc.paragraphs)
    for p in paras:
        text=p.text.strip();pf=p.paragraph_format
        if text==BODY:
            _boundary(p,base,cols,profile['column_gap_mm']);cols=profile['body_columns'];continue
        if text==BACK:
            if stack:raise ValueError('Unclosed wide block')
            _boundary(p,base,cols,profile['column_gap_mm']);cols=1;continue
        if text==BEGIN:
            if stack:raise ValueError('Nested wide blocks')
            stack.append(cols);_boundary(p,base,cols,profile['column_gap_mm'])
            cols=1;continue
        if text==END:
            if not stack:raise ValueError('Unexpected wide end')
            _boundary(p,base,cols,profile['column_gap_mm'])
            cols=stack.pop();continue
        if text.startswith('R3EQNUMBER_'):
            if last_math is None:raise ValueError('Equation number without math')
            number=text.split('_',1)[1]
            for outer in list(last_math._p.xpath('./m:oMathPara')):
                pos=list(last_math._p).index(outer)
                for math in list(outer.findall(qn('m:oMath'))):
                    last_math._p.insert(pos,deepcopy(math));pos+=1
                last_math._p.remove(outer)
            lead=OxmlElement('w:r');lead.append(OxmlElement('w:tab'))
            last_math._p.insert(1,lead);last_math.add_run('\t（'+number+'）')
            last_math.alignment=WD_ALIGN_PARAGRAPH.LEFT
            last_math.paragraph_format.tab_stops.add_tab_stop(Mm(full/2),WD_TAB_ALIGNMENT.CENTER)
            last_math.paragraph_format.tab_stops.add_tab_stop(Mm(full-1),WD_TAB_ALIGNMENT.RIGHT)
            p._p.getparent().remove(p._p);last_math=None;continue
        if p._p.xpath('.//m:oMathPara'):
            equations+=1;last_math=p;pf.first_line_indent=Pt(0);pf.line_spacing=1.1
            pf.space_before=Pt(3);pf.space_after=Pt(3);pf.keep_together=True
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER;continue
        if re.match(r'^[图表]\s*(?:\d+|[A-Z]\d+)\s',text):
            p.style=doc.styles['Caption'];p.alignment=WD_ALIGN_PARAGRAPH.CENTER;pf.first_line_indent=Pt(0);pf.line_spacing=1.15
            pf.keep_with_next=text.startswith('表');pf.space_before=Pt(4);pf.space_after=Pt(3)
            for r in p.runs:r.font.size=Pt(profile['caption_font_pt'])
        elif text.startswith(('注：','资料来源：','来源：')):
            pf.first_line_indent=Pt(0);pf.line_spacing=1.15;pf.space_after=Pt(5)
            for r in p.runs:r.font.size=Pt(profile['note_font_pt'])
        elif p._p.xpath('.//w:drawing'):
            # An exact 17.5 pt body line spacing clips large inline drawings.
            # A proportional line lets Word reserve the image's actual height.
            pf.first_line_indent=Pt(0);pf.keep_with_next=False;pf.space_after=Pt(0)
            pf.line_spacing=1.0
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        elif p.style.name.startswith('Heading'):
            pf.first_line_indent=Pt(0);pf.keep_with_next=True;pf.page_break_before=False
            if text.startswith('附录：'):pf.page_break_before=True
        elif p.style.name not in ('Title','Subtitle'):
            p.style='Normal'
            p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
            # Pandoc uses Body Text / First Paragraph; normalize them explicitly.
            pf.line_spacing=Pt(profile['line_spacing_pt']);pf.space_after=Pt(0)
            pf.first_line_indent=Pt(21)
            for r in p.runs:
                r.font.name=fonts['latin'];r.font.size=Pt(profile['body_font_pt'])
                rf=r._r.get_or_add_rPr().rFonts
                if rf is not None:rf.set(qn('w:eastAsia'),fonts['body'])
    if stack:raise ValueError('Unclosed wide block')
    body.remove(body.sectPr);body.append(_section(base,cols,profile['column_gap_mm']))
    data_table_count=len(doc.tables)
    for t in doc.tables:three_line_table(t,profile,full)
    # Keep each large image, caption and note in one unsplittable Word row.
    # A bare image paragraph can be clipped at a continuous section boundary
    # even though the drawing remains embedded in the DOCX/PDF.
    for index,p in enumerate(paras):
        if not p._p.xpath('.//w:drawing'):continue
        if index+2>=len(paras) or not re.match(r'^图\s*\d+\s',paras[index+1].text.strip()):
            raise ValueError('Figure caption does not follow drawing')
        if not paras[index+2].text.strip().startswith('注：'):
            raise ValueError('Figure note does not follow caption')
        frame=doc.add_table(rows=1,cols=1)
        frame.autofit=False;frame.columns[0].width=Mm(full)
        frame.cell(0,0).width=Mm(full)
        frame._tbl.tblPr.append(OxmlElement('w:tblBorders'))
        frame.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        p._p.addprevious(frame._tbl)
        cell=frame.cell(0,0)
        for item in paras[index:index+3]:cell._tc.append(item._p)
        for empty in list(cell._tc.xpath('./w:p')):
            if not empty.xpath('.//w:drawing') and not ''.join(empty.itertext()).strip():cell._tc.remove(empty)
    # Pandoc may inherit a colored title border from a default style.
    for root in (doc.element,doc.styles.element):
        for node in list(root.xpath('.//w:pBdr')):node.getparent().remove(node)
    if preview:
        for s in doc.sections:
            h=s.header.paragraphs[0];h.text='排版校样｜省略私有图表，非完整论文图版';h.alignment=WD_ALIGN_PARAGRAPH.CENTER
            for r in h.runs:r.font.size=Pt(8)
    doc.save(path)
    return {'tables':data_table_count,'figures':len(doc.inline_shapes),'equations':equations,
            'fonts':fonts,'profile':profile['version'],'visual_review':'PENDING'}
