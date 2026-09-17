"""Redraw eight R3 figures from existing certified aggregates; never estimate.

Plots are composed at their final print size, with short Chinese labels. Detailed
statistical notes belong below the figure in Word, not as tiny text inside PNGs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.publication.reference_style import load_profile,installed_fonts

LABELS={'demand':'需求冲击','cost':'成本冲击','supply':'供给冲击','price':'价格残差','initial_condition':'初始条件'}
SHOCKS=('demand','cost','supply','price')
GREYS=('.80','.30','.60','.05')
MARKERS=('o','s','^','D','x')
STYLES=('-','--','-.',':','-')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def setup(profile,fonts):
    plt.rcParams.update({'font.family':[fonts['heading'],fonts['latin']],'font.size':9,
                         'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,
                         'savefig.facecolor':'white','pdf.fonttype':42,'ps.fonttype':42})


def canvas(width=146,height=75):
    f=plt.figure(figsize=(width/25.4,height/25.4))
    a=f.add_axes([.13,.21,.84,.71]);a.tick_params(labelsize=8.5)
    a.set_axisbelow(True);a.grid(axis='y',color='.9',lw=.4)
    return f,a


def save(fig,path,dpi):
    fig.savefig(path,dpi=dpi,facecolor='white');plt.close(fig)


def dates(axis,months,every=12):
    pos=list(range(0,len(months),every))
    if len(months)-1-pos[-1]>every//2:pos.append(len(months)-1)
    axis.set_xticks(pos,[str(months[i]) for i in pos],rotation=0)
    axis.set_xlabel('年月')


def price(data,path,dpi):
    if len(data)!=69 or data.month.iloc[0]!='2020-01' or data.month.iloc[-1]!='2025-09':raise ValueError('Price sample is not v1')
    f,a=canvas();a.plot(np.arange(len(data)),data.lc_spot/10000,color='black',lw=1.2)
    a.set_ylabel('万元/吨');dates(a,data.month.tolist());save(f,path,dpi)


def mechanism(path,dpi):
    """Two compact timing panels; no intersecting network arrows or hidden heads."""
    from matplotlib.patches import FancyArrowPatch
    f=plt.figure(figsize=(146/25.4,70/25.4));a=f.add_axes([0,0,1,1]);a.axis('off');a.set_xlim(0,1);a.set_ylim(0,1)
    panels=[
        ('当期价格传导',.0,[
            (r'需求 $d_t$',r'$p_t$',r'$+b_d$'),
            (r'成本 $c_t$',r'$p_t$',r'$+b_c$'),
            (r'供给 $q_t$',r'$p_t$',r'$-b_q$'),
            (r'压力 $n_t$',r'$p_t$',r'$-b_n$')]),
        ('滞后跨状态反馈',.5,[
            (r'价格 $p_{t-1}$',r'$q_t$',r'$+a_p$'),
            (r'成本 $c_{t-1}$',r'$q_t$',r'$-a_c$'),
            (r'供给 $q_{t-1}$',r'$n_t$',r'$+1$'),
            (r'需求 $d_{t-1}$',r'$n_t$',r'$-1$')])]
    for title,offset,rows in panels:
        a.text(offset+.25,.94,title,ha='center',fontsize=9.5,fontweight='bold')
        a.plot([offset+.04,offset+.46],[.875,.875],color='black',lw=.7)
        for i,(source,target,coefficient) in enumerate(rows):
            y=.76-i*.19
            a.text(offset+.12,y,source,ha='center',va='center',fontsize=9)
            a.add_patch(FancyArrowPatch((offset+.25,y),(offset+.37,y),arrowstyle='-|>',mutation_scale=10,lw=.9,color='black'))
            a.text(offset+.31,y+.042,coefficient,ha='center',fontsize=8)
            a.text(offset+.43,y,target,ha='center',va='center',fontsize=10)
    save(f,path,dpi)


def irf(data,path,dpi):
    expected={(shock,h) for shock in SHOCKS for h in range(25)}
    if len(data)!=100 or set(data.state)!={'p'} or set(zip(data.shock,data.horizon))!=expected or data.duplicated(['shock','horizon']).any():raise ValueError('Incomplete IRF grid')
    quantiles=data[['q05','q16','median','q84','q95']].to_numpy(float)
    if not np.isfinite(quantiles).all() or (np.diff(quantiles,axis=1)<0).any():raise ValueError('Invalid IRF quantiles')
    images=[]
    for index,shock in enumerate(SHOCKS):
        r=data[data.shock==shock].sort_values('horizon')
        f=plt.figure(figsize=(72/25.4,58/25.4));a=f.add_axes([.20,.24,.76,.60])
        a.fill_between(r.horizon,r.q05,r.q95,color='.88',lw=0)
        a.fill_between(r.horizon,r.q16,r.q84,color='.65',lw=0)
        a.plot(r.horizon,r['median'],color='black',lw=1.0)
        a.axhline(0,color='.25',ls='--',lw=.6);a.set_xlim(0,24);a.set_xticks([0,12,24])
        a.set_title(f'（{index+1}）{LABELS[shock]}',fontsize=9);a.set_xlabel('冲击后月数',fontsize=8.5);a.set_ylabel('标准化响应',fontsize=8)
        a.tick_params(labelsize=8)
        part=path.with_name(path.stem+'_'+shock+'.png');save(f,part,dpi);images.append(Image.open(part).convert('RGB'))
    # Four independently drawn plots, arranged as an article figure; no data altered.
    w,h=images[0].size;gap=round(dpi*2/25.4)
    combined=Image.new('RGB',(2*w+gap,2*h+gap),'white')
    for i,img in enumerate(images):combined.paste(img,((i%2)*(w+gap),(i//2)*(h+gap)))
    combined.save(path,dpi=(dpi,dpi))
    for img in images:img.close()


def fevd(data,path,dpi):
    r=data[(data.specification=='BASELINE')&(data.state=='p')]
    piv=r.pivot(index='horizon',columns='shock',values='mean').loc[[1,3,6,12,24],list(SHOCKS)]
    if not np.isfinite(piv).all().all() or not np.allclose(piv.sum(axis=1),1,atol=1e-8):raise ValueError('FEVD means not additive')
    f,a=canvas();bottom=np.zeros(5)
    for j,s in enumerate(SHOCKS):
        a.bar(range(5),piv[s]*100,bottom=bottom,width=.55,color=GREYS[j],edgecolor='white',lw=.5,label=LABELS[s]);bottom+=piv[s].to_numpy()*100
    a.set_xticks(range(5),piv.index);a.set_ylim(0,100);a.set_ylabel('后验均值份额（%）');a.set_xlabel('预测期限（月）')
    a.legend(ncol=4,frameon=False,loc='lower center',bbox_to_anchor=(.5,1.02),fontsize=8)
    save(f,path,dpi)


def history(data,path,dpi):
    order=('initial_condition',)+SHOCKS
    p=data.pivot(index='month',columns='component',values='posterior_mean').sort_index()
    if len(p)!=57 or not np.allclose(p[list(order)].sum(axis=1),p.smoothed_state,atol=1e-8):raise ValueError('History is not additive')
    f,a=canvas(height=80);x=np.arange(len(p));pos=np.zeros(len(p));neg=pos.copy()
    for j,k in enumerate(order):
        y=p[k].to_numpy();positive=np.maximum(y,0);negative=np.minimum(y,0);c=('.95',)+GREYS
        a.bar(x,positive,bottom=pos,color=c[j],width=.88,edgecolor='white',lw=.1,label=LABELS[k])
        a.bar(x,negative,bottom=neg,color=c[j],width=.88,edgecolor='white',lw=.1)
        pos+=positive;neg+=negative
    a.plot(x,p.smoothed_state,color='black',lw=.9,label='价格状态');a.axhline(0,color='black',lw=.6)
    dates(a,p.index.tolist(),12);a.set_ylabel('标准化价格变化压力')
    a.legend(ncol=3,frameon=False,loc='lower center',bbox_to_anchor=(.5,1.01),fontsize=8)
    save(f,path,dpi)


def forecast(data,path,dpi):
    names=('RW_NO_DRIFT','AR_BIC','VAR_SPEC_B','BVAR_SPEC_B','STRUCTURAL_MAP_M0')
    labels=('RW','AR','VAR','BVAR','结构模型')
    f,a=canvas()
    for j,(m,label) in enumerate(zip(names,labels)):
        r=data[data.model==m].sort_values('horizon')
        if len(r)!=3 or r.horizon.tolist()!=[1,3,6]:raise ValueError('Missing forecast grid')
        a.plot(r.horizon,r.theil_u2,color=str(.12+j*.14),ls=STYLES[j],marker=MARKERS[j],markersize=4,lw=1,label=label)
    a.set_xticks([1,3,6]);a.set_xlabel('预测期限（月）');a.set_ylabel('Theil U₂');a.axhline(1,color='.45',lw=.5,ls=':')
    a.legend(ncol=5,frameon=False,loc='lower center',bbox_to_anchor=(.5,1.02),fontsize=8)
    save(f,path,dpi)


def inventory(data,path,dpi):
    r=data[(data.specification=='BASELINE')&(data.external_series=='lc_inventory_total_mean')&
           (data.information_use=='SMOOTHED')&data.transformation.isin(['log_level','log_change'])&data.block_length.isin([3,6])].copy()
    if len(r)!=4 or r.duplicated(['transformation','block_length']).any():raise ValueError('Incomplete inventory comparison')
    if not np.isfinite(r[['ci025','ci975','point_correlation']]).all().all() or (r.ci025>r.ci975).any():raise ValueError('Invalid interval')
    r=r.sort_values(['transformation','block_length'])
    f,a=canvas(height=78);ys=[];labels=[]
    for i,row in enumerate(r.itertuples()):
        a.plot([row.ci025,row.ci975],[i,i],color='black',lw=1)
        a.plot(row.point_correlation,i,marker='o' if row.block_length==3 else 's',color='black',ms=4)
        ys.append(i);labels.append(('水平' if row.transformation=='log_level' else '变化量')+f'·{row.block_length}月块')
    a.set_yticks(ys,labels);a.set_xlim(-.6,1);a.set_ylim(-.5,3.5);a.axvline(0,color='.4',lw=.7,ls='--');a.invert_yaxis()
    a.set_xlabel('Pearson相关及95%配对时间块区间');a.spines['left'].set_visible(False)
    save(f,path,dpi)


def futures(data,path,dpi):
    images=[]
    for index,(spec,label) in enumerate([('MATCHED_EOM_PRIMARY','同月末端点'),('DAILY_MATCHED_INTERVAL_PRIMARY','相邻日区间')]):
        f,a=canvas(width=146,height=63)
        for rule,line,marker,name in [('EX_POST_DESCRIPTIVE_MAIN','-','o','当日成交量主力'),('LAGGED_VOLUME_MAIN','--','s','前日成交量主力')]:
            r=data[(data.stratum=='ALL')&(data.specification==spec)&(data.main_rule==rule)].sort_values('lag_spot_periods')
            expected=7 if index==0 else 11
            if len(r)!=expected or r.lag_spot_periods.duplicated().any():raise ValueError('Incomplete lag family')
            a.plot(r.lag_spot_periods,r.pearson,color='black' if line=='-' else '.5',ls=line,marker=marker,ms=3,lw=1,label=name)
        a.axhline(0,color='.5',lw=.5);a.set_xlabel('现货相对期货的滞后期数');a.set_ylabel('Pearson相关')
        a.set_title(label,fontsize=9);a.legend(ncol=2,frameon=False,fontsize=8)
        part=path.with_name(path.stem+f'_{index}.png');save(f,part,dpi);images.append(Image.open(part).convert('RGB'))
    w,h=images[0].size;combined=Image.new('RGB',(w,2*h),'white')
    for i,img in enumerate(images):combined.paste(img,(0,i*h))
    combined.save(path,dpi=(dpi,dpi))
    for img in images:img.close()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run-id',required=True)
    ap.add_argument('--source-r2-run',default='R2_20260917_095514');args=ap.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',args.run_id) or not re.fullmatch(r'[A-Za-z0-9_-]+',args.source_r2_run):raise ValueError('Safe run identifiers required')
    if not args.run_id.startswith('R3_'):raise ValueError('R3_ prefix required')
    from scripts.build_r2_advisor_documents import input_checks
    from scripts.build_r2_figures import select_forecast,select_lags
    before=input_checks();r1=ROOT/'outputs/revisions/R1_20260916_190253'
    registry=r1/'result_registry_final/result_registry.json';reg=json.loads(registry.read_text(encoding='utf-8'))
    oldpath=ROOT/'outputs/thesis'/args.source_r2_run/'文件与结果来源清单.json'
    old=json.loads(oldpath.read_text(encoding='utf-8'))
    if old.get('input_checks',{}).get('registry_sha256')!=before['registry_sha256']:raise ValueError('Wrong R2 provenance')
    proof={}
    def add(path,h):
        path=path.replace('\\','/')
        if path in proof and proof[path]!=h.lower():raise ValueError('Conflicting source hashes '+path)
        proof[path]=h.lower()
    for row in reg['results']:
        if row.get('source_file') and row.get('source_file_sha256'):add(row['source_file'],row['source_file_sha256'])
    for row in old['figures'].values():
        for p,h in row['source_sha256'].items():add(p,h)
    inputs={str(registry.relative_to(ROOT)):digest(registry),str(oldpath.relative_to(ROOT)):digest(oldpath)}
    def read(relative):
        relative=relative.replace('\\','/');p=(ROOT/relative).resolve()
        if not p.is_relative_to(ROOT.resolve()):raise ValueError('Outside checkout')
        if relative not in proof or digest(p)!=proof[relative]:raise ValueError('Uncertified/mutated source '+relative)
        inputs[relative]=digest(p);return pd.read_csv(p)
    prefix='outputs/revisions/R1_20260916_190253/'
    data={
        'PRICE':read('data/processed/core_monthly_panel.csv'),
        'IRF':read('outputs/phase2/phase2e/irf_price_summary.csv'),
        'FEVD':read(prefix+'fevd/fevd_corrected_summary.csv'),
        'HISTORY':read(prefix+'historical/historical_monthly_corrected.csv'),
        'INVENTORY':read(prefix+'external_validation_final/external_validation_block_bootstrap.csv'),
        'FUTURES':read(prefix+'futures/lead_lag_specification_comparison.csv')}
    fc=read(prefix+'forecast_verified/forecast_metric_revision.csv');archive=read('outputs/phase2/phase2g/structural_oos_metrics.csv')
    data['FORECAST']=select_forecast(fc,archive)
    claims=read(prefix+'futures/futures_claim_revision.csv');data['FUTURES']=select_lags(data['FUTURES'],claims)
    profile_path=ROOT/'configs/hog_reference_style.json';profile=load_profile(profile_path);fonts=installed_fonts(profile);setup(profile,fonts)
    out=ROOT/'outputs/thesis'/args.run_id/'figures'
    if out.exists() and any(out.iterdir()):raise FileExistsError('Use a fresh run-id')
    out.mkdir(parents=True,exist_ok=True)
    import subprocess
    subprocess.run(['git','check-ignore','-q',str(out/'manifest.json')],cwd=ROOT,check=True)
    titles={'PRICE':'图1 电池级碳酸锂现货月均价格','MECHANISM':'图2 五状态价格传导框架',
        'IRF':'图3 四类冲击对价格变化状态的脉冲响应','FEVD':'图4 不同预测期限的价格方差来源',
        'HISTORY':'图5 价格变化的有符号历史分解','FORECAST':'图6 五模型相对随机游走的预测误差',
        'INVENTORY':'图7 供需压力与实际库存的外部对照','FUTURES':'图8 同区间期现收益的领先滞后相关'}
    notes={'PRICE':'注：2020年1月至2025年9月，69个月；万元/吨。资料来源：SMM核心冻结序列。',
        'MECHANISM':'注：状态均采用模型变换单位；供需压力不是吨数库存。',
        'IRF':'注：横轴为月数；黑线为后验中位数，深浅灰带分别为68%与90%边际可信区间；纵轴为标准化价格变化响应。',
        'FEVD':'注：使用逐后验样本份额的均值；各期限加总为100%，未绘制边际区间。',
        'HISTORY':'注：后验均值按正负分别堆叠，含初始条件；2021年1月至2025年9月。曲线为模型价格变化状态。',
        'FORECAST':'注：同一预测键，N依次为21、19、16；U₂为模型RMSE相对RW的比率，非前瞻或显著性检验。',
        'INVENTORY':'注：点为固定后验中位路径相关，线为3/6月配对块95%区间；水平28个月、变化量27个月，非完整联合后验。',
        'FUTURES':'注：正滞后为期货t对随后现货。月频26个收益、日频534个收益；探索性相关，不表示因果或交易收益。'}
    functions={'PRICE':price,'IRF':irf,'FEVD':fevd,'HISTORY':history,'FORECAST':forecast,'INVENTORY':inventory,'FUTURES':futures}
    records={}
    for key in titles:
        p=out/(key.lower()+'.png')
        mechanism(p,profile['figure_dpi']) if key=='MECHANISM' else functions[key](data[key],p,profile['figure_dpi'])
        records[key]={'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p),'width_mm':146,'caption':titles[key],'note':notes[key]}
    if before!=input_checks() or any(digest(ROOT/p)!=h for p,h in inputs.items()):raise RuntimeError('Input changed while plotting')
    manifest={'schema':'r3_reference_figures_v1','run_id':args.run_id,'style_sha256':digest(profile_path),
        'input_sha256':inputs,'figures':records,'fonts':fonts,'no_estimation':True,'visual_review':'PENDING'}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Eight R3 figures generated; render and visually review the complete Word/PDF before declaring ready.')


if __name__=='__main__':main()
