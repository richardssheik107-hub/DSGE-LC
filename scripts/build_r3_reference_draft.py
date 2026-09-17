"""Compose the five-section R3 manuscript from verified figure assets.

Default requires R1/private R3 inputs. --preview-text-only is explicitly labelled
and never counted as a full-figure empirical deliverable. No estimation occurs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.publication.reference_style import BEGIN,END,load_profile,installed_fonts,template,wrap_markdown,polish
MARKER=re.compile(r'<!-- R3_FIGURE:([A-Z_]+) -->')
SOURCE=ROOT/'docs/thesis/reference_style_manuscript.md'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(text,manifest,root,preview=False,description=None):
    used=[];omitted=[]
    def embed(match):
        key=match[1]
        if key in used:raise ValueError('Duplicate figure '+key)
        used.append(key)
        if preview:omitted.append(key);return ''
        row=manifest['figures'].get(key)
        if row is None:raise ValueError('Missing figure '+key)
        path=(root/row['path']).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path)!=row['sha256']:raise ValueError('Invalid figure '+key)
        if row['width_mm']>146.5:raise ValueError('Figure exceeds print width')
        return f'\n{BEGIN}\n\n![]({path.as_posix()}){{width={row["width_mm"]}mm}}\n\n{row["caption"]}\n\n{row["note"]}\n\n{END}\n'
    text=MARKER.sub(embed,text)
    token='<!-- R3_TABLE:CORE_DESCRIPTION -->'
    if text.count(token)!=1:raise ValueError('Description marker missing/duplicated')
    if description is None:
        if not preview:raise ValueError('Private descriptive table required')
        text=text.replace(token,'');omitted.append('CORE_DESCRIPTION')
    else:text=text.replace(token,description)
    if not preview and set(used)!=set(manifest['figures']):raise ValueError('Extra/missing figure manifest entries')
    if re.search(r'<!-- R[23]_(FIGURE|TABLE):',text):raise ValueError('Unresolved asset marker')
    return wrap_markdown(text),omitted


def render_pdf(docx):
    docx=Path(docx).resolve();pdf=docx.with_suffix('.pdf')
    if pdf.exists():raise FileExistsError('PDF already exists')
    if os.name=='nt':
        subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'scripts/export_r3_word_pdf.ps1'),'-Docx',str(docx)],check=True)
    else:
        executable=shutil.which('libreoffice') or shutil.which('soffice')
        if executable is None:raise RuntimeError('No authorized PDF renderer installed')
        with tempfile.TemporaryDirectory(prefix='r3-profile-') as folder:
            subprocess.run([executable,'-env:UserInstallation='+Path(folder).as_uri(),'--headless','--convert-to','pdf','--outdir',str(docx.parent),str(docx)],check=True)
    if not pdf.is_file() or pdf.stat().st_size<1000:raise RuntimeError('Renderer produced no usable PDF')
    return pdf


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run-id',required=True)
    ap.add_argument('--preview-text-only',action='store_true');ap.add_argument('--render-pdf',action='store_true')
    ap.add_argument('--output-dir',type=Path,help='Labelled preview only; full drafts remain in ignored outputs/thesis')
    args=ap.parse_args()
    if not re.fullmatch(r'R3_[A-Za-z0-9_-]+',args.run_id):raise ValueError('Safe R3_ run-id required')
    if args.output_dir and not args.preview_text_only:raise ValueError('Private document output must remain ignored')
    out=args.output_dir or ROOT/'outputs/thesis'/args.run_id/'documents'
    if out.exists() and any(out.iterdir()):raise FileExistsError('Fresh document output directory required')
    profile_path=ROOT/'configs/hog_reference_style.json';profile=load_profile(profile_path);fonts=installed_fonts(profile)
    manifest={};before=None;description=None
    if not args.preview_text_only:
        from scripts.build_r2_advisor_documents import input_checks,core_description_markdown
        subprocess.run(['git','check-ignore','-q',str(out/'论文初稿.docx')],cwd=ROOT,check=True)
        before=input_checks()
        fp=ROOT/'outputs/thesis'/args.run_id/'figures/manifest.json';manifest=json.loads(fp.read_text(encoding='utf-8'))
        if manifest.get('schema')!='r3_reference_figures_v1' or manifest.get('run_id')!=args.run_id:raise ValueError('Wrong figure manifest')
        if manifest['style_sha256']!=digest(profile_path):raise ValueError('Figure/Word style profile differs')
        for relative,h in manifest['input_sha256'].items():
            p=(ROOT/relative).resolve()
            if not p.is_relative_to(ROOT.resolve()) or digest(p)!=h:raise ValueError('Changed figure source '+relative)
        description=core_description_markdown().replace('表3-2 冻结核心月度水平序列描述统计（2020-01—2025-09）','表2 核心变量描述统计（2020年1月至2025年9月）')
        description=description.replace('来源：Data Freeze v1冻结水平面板；商业派生统计仅供本地导师讨论稿使用，不公开源序列。','注：基于69个月核心水平观测计算，标准差为样本标准差。资料来源：SMM与动力电池联盟同口径资料。')
    text,omitted=prepare(SOURCE.read_text(encoding='utf-8'),manifest,ROOT,args.preview_text_only,description)
    out.mkdir(parents=True,exist_ok=True)
    md=out/'prepared_manuscript.md';md.write_text(text,encoding='utf-8')
    reference=out/'reference.docx';template(profile,fonts,reference)
    docx=out/('参考式排版校样.docx' if args.preview_text_only else '论文初稿_例文体例.docx')
    subprocess.run(['pandoc',str(md),'--from=markdown+tex_math_dollars+pipe_tables','--to=docx','--standalone','-M','date=',
        '--reference-doc='+str(reference),'--resource-path='+str(ROOT),'--output='+str(docx)],check=True,cwd=ROOT)
    report=polish(docx,profile,fonts,args.preview_text_only)
    report.update({'run_id':args.run_id,'source_sha256':digest(SOURCE),'style_sha256':digest(profile_path),'docx_sha256':digest(docx),
                   'scope':'LAYOUT_PREVIEW_ONLY' if args.preview_text_only else 'PRIVATE_FULL_FIGURE_GENERATED',
                   'omitted':omitted,'school_submission_ready':False,'no_estimation':True})
    if args.render_pdf:
        pdf=render_pdf(docx);report['pdf_sha256']=digest(pdf)
    if not args.preview_text_only and before!=input_checks():raise RuntimeError('Frozen inputs changed')
    (out/'publication_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'docx':str(docx),'scope':report['scope'],'visual_review':'PENDING'},ensure_ascii=False))


if __name__=='__main__':main()
