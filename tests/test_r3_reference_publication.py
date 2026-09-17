"""Portable R3 editorial/typesetting tests; fixtures never replace real figures."""
from pathlib import Path
import re
import json
import ast
import sys
import numpy as np
import pandas as pd
import pytest
from docx import Document
from docx.oxml.ns import qn
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.publication.reference_style import load_profile,installed_fonts,template,three_line_table,wrap_markdown,polish,BEGIN,END
from scripts.build_r3_reference_draft import prepare
from scripts import build_r3_reference_figures as plots
DRAFT=ROOT/'docs/thesis/reference_style_manuscript.md'
PROFILE=ROOT/'configs/hog_reference_style.json'


def test_reference_structure_not_phase_report():
    s=DRAFT.read_text(encoding='utf-8')
    heads=re.findall(r'^# ([一二三四五]、.*)',s,re.M)
    assert heads==['一、引言','二、文献综述','三、理论分析框架与模型构建','四、实证分析','五、结论与启示']
    assert '通过705' not in s and 'git push' not in s


def test_asset_contract_and_result_limits():
    s=DRAFT.read_text(encoding='utf-8')
    assert len(set(re.findall('R3_FIGURE:([A-Z_]+)',s)))==8
    assert s.count('R3_TABLE:CORE_DESCRIPTION')==1
    for value in ['8.91%','21.30%','4.90%','64.89%','0.914','1.240','1.131','0.526','0.475']:
        assert value in s
    assert '六个替代规格' in s and '歧义' in s and '半结构' in s


def test_reference_registry_retained():
    s=DRAFT.read_text(encoding='utf-8')
    assert {int(n) for n in re.findall(r'^\[(\d+)\]',s,re.M)}==set(range(1,21))
    assert '正式发表状态待作者确认' in s


def test_explicit_equation_numbers():
    s=DRAFT.read_text(encoding='utf-8')
    assert re.findall(r'\\tag\{(\d+)\}',s)==[str(i) for i in range(1,13)]
    m=wrap_markdown(s)
    assert 'R3EQNUMBER_12' in m


def test_missing_asset_cannot_make_complete_document():
    with pytest.raises(ValueError):prepare(DRAFT.read_text(encoding='utf-8'),{'figures':{}},ROOT,False,'desc')


def test_preview_explicitly_records_omissions():
    text,missing=prepare(DRAFT.read_text(encoding='utf-8'),{},ROOT,True)
    assert len(missing)==9 and 'CORE_DESCRIPTION' in missing
    assert '<!-- R3_FIGURE' not in text


def test_table_is_native_fixed_width_and_three_line(tmp_path):
    profile=load_profile(PROFILE);fonts=installed_fonts(profile)
    p=tmp_path/'x.docx';template(profile,fonts,p);d=Document(p)
    t=d.add_table(rows=4,cols=3)
    for i,row in enumerate(t.rows):
        for j,c in enumerate(row.cells):c.text=f'{i}.{j}'
    before=[[c.text for c in r.cells] for r in t.rows]
    three_line_table(t,profile,146.5);d.save(p)
    assert before==[[c.text for c in r.cells] for r in t.rows]
    assert t.autofit is False
    assert t.rows[0].cells[0]._tc.xpath('./w:tcPr/w:tcBorders/w:top')[0].get(qn('w:val'))=='single'
    assert t.rows[-1].cells[0]._tc.xpath('./w:tcPr/w:tcBorders/w:bottom')[0].get(qn('w:val'))=='single'
    assert t.rows[1].cells[0]._tc.xpath('./w:tcPr/w:tcBorders/w:left')[0].get(qn('w:val'))=='nil'
    assert all(c.paragraphs[0].style.name=='Normal' for r in t.rows for c in r.cells)


def test_full_width_figure_reserves_image_height_and_keeps_caption(tmp_path):
    profile=load_profile(PROFILE);fonts=installed_fonts(profile)
    image=tmp_path/'figure.png';Image.new('RGB',(800,400),'white').save(image)
    path=tmp_path/'figure.docx';template(profile,fonts,path);doc=Document(path)
    doc.add_paragraph(BEGIN)
    doc.add_picture(str(image))
    doc.add_paragraph('图1 测试图注')
    doc.add_paragraph('注：测试图注与图保持在同一单元。')
    doc.add_paragraph(END)
    doc.save(path)
    result=polish(path,profile,fonts)
    rendered=Document(path)
    figure=rendered.tables[-1].cell(0,0)
    assert result['figures']==1 and len(figure.paragraphs)==3
    assert figure.paragraphs[0].paragraph_format.line_spacing==1.0
    assert figure.paragraphs[1].text=='图1 测试图注'
    assert figure.paragraphs[2].text.startswith('注：')


def test_feved_wrong_sum_rejected(tmp_path):
    rows=[dict(specification='BASELINE',state='p',horizon=h,shock=j,mean=.3) for h in [1,3,6,12,24] for j in plots.SHOCKS]
    with pytest.raises(ValueError):plots.fevd(pd.DataFrame(rows),tmp_path/'bad.png',100)


def test_price_plot_preserves_source(tmp_path):
    p=load_profile(PROFILE);plots.setup(p,installed_fonts(p))
    data=pd.DataFrame({'month':pd.period_range('2020-01','2025-09',freq='M').astype(str),'lc_spot':np.linspace(10000,20000,69)})
    before=data.copy(deep=True);plots.price(data,tmp_path/'synthetic_test.png',100)
    pd.testing.assert_frame_equal(before,data)
    with Image.open(tmp_path/'synthetic_test.png') as im:assert im.width>500 and im.height>250


def test_incomplete_irf_rejected(tmp_path):
    data=pd.DataFrame([{'state':'p','shock':'cost','horizon':0}])
    with pytest.raises(ValueError):plots.irf(data,tmp_path/'bad.png',100)


def test_no_sampling_in_publication_entrypoints():
    for name in ['build_r3_reference_draft.py','build_r3_reference_figures.py']:
        s=(ROOT/'scripts'/name).read_text(encoding='utf-8');ast.parse(s)
        assert 'np.load(' not in s
        assert not re.search(r'\.(?:sample|optimize|fit|mcmc)\s*\(',s)
        assert 'input_checks' in s


def test_profile_matches_reference_page_geometry():
    p=load_profile(PROFILE)
    assert p['page_mm']==[210,297]
    assert p['margins_mm']['left']==p['margins_mm']['right']==31.75
    assert p['body_columns']==2 and p['table_font_pt']>=9
