/** Two-slide presentation layer; does not alter or solve the economic model.
 * Run from repository root: npm install --prefix scripts/presentation &&
 * node scripts/presentation/build_core_structure.js [output.pptx]
 * Text/diagrams are editable shapes; equations are vector SVG with source here.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {TeX} = require('mathjax-full/js/input/tex.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
const {AllPackages} = require('mathjax-full/js/input/tex/AllPackages.js');
const ROOT = path.resolve(__dirname, '../..');
const OUT = process.argv[2] ? path.resolve(process.argv[2]) : path.join(ROOT, 'outputs', 'core_structure_2slides.pptx');
fs.mkdirSync(path.dirname(OUT), {recursive:true});
const md = fs.readFileSync(path.join(ROOT,'docs/presentations/core_structure.md'), 'utf8');
const talks = [...md.matchAll(/### 口头讲稿[^\n]*\n\n([\s\S]*?)(?=\n### 备注中的完整对应)/g)].map(m=>m[1].trim());
const noteBlocks = [...md.matchAll(/### 备注中的完整对应\n\n([\s\S]*?)(?=\n## |$)/g)].map(m=>m[1].trim());
if (talks.length !== 2 || noteBlocks.length !== 2) throw new Error('Expected exactly two source scripts and notes.');
const C={bg:'F6F8FB',ink:'17344A',muted:'566675',teal:'146C6B',blue:'315C90',gold:'8E6423',line:'CAD6E0',white:'FFFFFF',light:'EAF4F3',sand:'F8F1E6'};
const FONT='Noto Sans CJK SC';
const pptx=new pptxgen();
pptx.layout='LAYOUT_WIDE'; pptx.author='李江涛'; pptx.subject='碳酸锂核心结构：两页主体方程与机制';
pptx.title='碳酸锂：现货定价与跨期反馈'; pptx.company=''; pptx.lang='zh-CN';
pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'zh-CN'};
const W=13.333333,H=7.5;
const adaptor=liteAdaptor(); RegisterHTMLHandler(adaptor);
const mj = mathjax.document('', {InputJax:new TeX({packages:AllPackages}), OutputJax:new SVG({fontCache:'local'})});
const eqLog=[]; const boxes=[];
function text(s,t,x,y,w,h,opt={}){
  s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:16,color:C.ink,margin:0,breakLine:false,paraSpaceAfterPt:0,fit:'resize',valign:'mid',...opt});
  boxes.push({slide:s._slideNum,type:'text',text:typeof t==='string'?t:'rich_text',x,y,w,h});
}
function rect(s,x,y,w,h,fill=C.white,line=C.line,radius=false){
 s.addShape(radius?pptx.ShapeType.roundRect:pptx.ShapeType.rect,{x,y,w,h,rectRadius:0.1,radius:0.1,fill:{color:fill},line:{color:line,width:0.7}});
}
function line(s,x1,y1,x2,y2,{color=C.teal,width=1.4,arrow=true,start=false,dash=false}={}){
 const o={x:x1,y:y1,w:x2-x1,h:y2-y1,line:{color,width,beginArrowType:start?'triangle':undefined,endArrowType:arrow?'triangle':undefined,dashType:dash?'dash':undefined}};
 s.addShape(pptx.ShapeType.line,o);
}
function eq(s,tex,x,y,w,h){
 const node=mj.convert(tex,{display:true});
 let svg=adaptor.outerHTML(adaptor.firstChild(node));
 if(svg.includes('data-mjx-error')) throw new Error('Math conversion failed: '+tex);
 const vb=svg.match(/viewBox="([^"]+)"/)[1].split(/\s+/).map(Number);
 const ratio=vb[2]/vb[3]; let ww=w,hh=ww/ratio;
 if(hh>h){hh=h;ww=hh*ratio;}
 svg=svg.replace(/width="[^"]+"/,`width="${Math.ceil(ww*140)}px"`).replace(/height="[^"]+"/,`height="${Math.ceil(hh*140)}px"`).replace(/currentColor/g,`#${C.ink}`);
 s.addImage({data:'image/svg+xml;base64,'+Buffer.from(svg).toString('base64'),x:x+(w-ww)/2,y:y+(h-hh)/2,w:ww,h:hh,altText:tex});
 eqLog.push({slide:s._slideNum,latex:tex,x,y,w,h});
}
function header(s,num,title,subtitle){
 s.background={color:C.bg};
 s.addShape(pptx.ShapeType.rect,{x:0,y:0,w:W,h:0.10,line:{color:C.teal},fill:{color:C.teal}});
 text(s,`${num}  /  碳酸锂期现定价`,0.5,0.34,5,0.23,{fontSize:11,bold:true,color:C.teal,charSpacing:1});
 text(s,'月度 · 同口径商品 · 动态部分均衡',8.35,0.32,4.48,0.28,{fontSize:11,color:C.muted,align:'right'});
 text(s,title,0.5,0.77,12.3,0.52,{fontSize:28,bold:true});
 text(s,subtitle,0.5,1.37,12.3,0.30,{fontSize:15,color:C.muted});
}
function footer(s,left,num){
 text(s,left,0.5,7.18,11.55,0.18,{fontSize:9.4,color:C.muted});
 text(s,`${num} / 2`,12.12,7.12,0.7,0.28,{fontSize:11,color:C.muted,align:'right'});
}
// SLIDE 1 -----------------------------------------------------------------
{
 const s=pptx.addSlide();
 header(s,'01','现货价格由生产、耗用与留货共同决定','先看实物分配：本月生产多少、实际用多少，又留下多少？');
 const cards=[{x:0.5,title:'生产者',q:'本月生产多少？',id:'E09',color:C.blue},
              {x:4.665,title:'当期使用者',q:'本月灵活耗用多少？',id:'E04 / E05',color:C.teal},
              {x:8.83,title:'库存中介',q:'留到下一期，是否划算？',id:'E24',color:C.gold}];
 for(const c of cards){
  rect(s,c.x,1.91,4.0,2.63);
  s.addShape(pptx.ShapeType.rect,{x:c.x,y:1.91,w:4.0,h:0.055,line:{color:c.color},fill:{color:c.color}});
  text(s,c.title,c.x+0.2,2.10,2.6,0.32,{fontSize:19,bold:true,color:c.color});
  text(s,c.id,c.x+2.97,2.12,0.83,0.23,{fontSize:10,color:C.muted,align:'right'});
  text(s,c.q,c.x+0.2,2.57,3.6,0.33,{fontSize:16});
 }
 eq(s,String.raw`P_t=MC_t^d+\lambda_t-\mu_t^Q`,0.70,3.05,3.6,0.40);
 text(s,'MCᵈ含基础、负荷与跨期调产成本\n产量不能超过有效产能；保留两端约束',0.70,3.73,3.6,0.58,{fontSize:13.6,color:C.muted,breakLine:false});
 eq(s,String.raw`D_t^s=A_t^s(P_t/P_*)^{-\eta_s}`,4.865,3.05,3.6,0.40);
 eq(s,String.raw`D_t=D_t^s+C_{t-1}`,4.865,3.70,3.6,0.30);
 text(s,'上期承诺，本期实际执行',4.865,4.08,3.6,0.23,{fontSize:13.2,color:C.muted,align:'center'});
 eq(s,String.raw`0\le I_t\perp P_t+G'(I_t)-b_t\alpha_I F_t\ge0`,9.03,3.03,3.6,0.43);
 text(s,'比较购货、净持有成本与套保后价值\n⊥：有库存时等号成立，也允许零库存',9.03,3.73,3.6,0.58,{fontSize:13.6,color:C.muted});
 for(const x of [2.5,6.665,10.83]) line(s,x,4.58,x,4.91,{start:true,width:1.2});
 rect(s,0.5,4.94,12.33,1.24,C.light,'C3DCDA');
 text(s,'现货市场同时清算',0.72,5.08,4,0.25,{fontSize:14,bold:true,color:C.teal});
 text(s,'E25',11.93,5.08,0.65,0.25,{fontSize:10,color:C.muted,align:'right'});
 eq(s,String.raw`Q_t+N_t+\alpha_I I_{t-1}=D_t^s+C_{t-1}+I_t`,1.7,5.43,9.94,0.43);
 text(s,'本期生产 + 净进口 + 上期留存   =   本期实际耗用 + 期末留货',1.05,5.95,11.3,0.20,{fontSize:12.3,color:C.muted,align:'center'});
 text(s,'C 是下期耗用承诺，I 是期末实物库存；期货持仓不进入吨数账。',0.72,6.39,11.8,0.32,{fontSize:15,bold:true});
 text(s,'P / F：现货 / 一期期货价    Q：产量    Dˢ：灵活耗用    N：成品净进口    α_I：库存留存率',0.72,6.86,11.8,0.22,{fontSize:11.4,color:C.muted});
 footer(s,'规范：E04—E05、E09、E24—E25。MCᵈ、G′及边界完整定义见备注；箭头表示价格与选择的联立关系。',1);
 s.addNotes('【主讲】\n'+talks[0]+'\n\n【完整条件与来源】\n'+noteBlocks[0]+'\n\n固定模型提交：3580f3b1da7cd24c90312c30d4ee200ceee281bc。该页不是独立的新模型。');
}
// SLIDE 2 -----------------------------------------------------------------
{
 const s=pptx.addSlide();
 header(s,'02','期货与扩产，把今天的选择带到未来','短期由库存与采购调整，长期由新产能释放；两条路径共同反馈到价格。');
 rect(s,0.5,1.91,7.32,3.12);
 rect(s,8.02,1.91,4.81,3.12);
 text(s,'短期：谁承接套保风险？',0.72,2.08,6.85,0.33,{fontSize:18.5,bold:true,color:C.teal});
 const roles=[['库存：卖出套保',0.72,2.09],['采购：买入套保',2.94,2.09],['投资者：有限风险承担',5.16,2.43]];
 for(const [t,x,w] of roles){rect(s,x,2.57,w,0.38,C.light,'D5E7E5',true);text(s,t,x+0.06,2.62,w-0.12,0.25,{fontSize:12.5,align:'center',color:C.teal});}
 eq(s,String.raw`F_t=\mu_t^P-(v_t^P/\mathcal T_t)(\alpha_I I_t-C_t)`,0.85,3.11,6.62,0.50);
 text(s,'μᴾ、vᴾ：下期现货的条件均值与方差\n𝒯：总风险承受能力；括号内为净产业套保敞口',0.80,3.70,6.70,0.49,{fontSize:12.3,color:C.muted});
 eq(s,String.raw`C_t=A_t^c(F_t/P_*)^{-\eta_c}`,0.84,4.30,3.57,0.33);
 text(s,'F 同时影响留货 I（见上一页）',4.47,4.31,3.1,0.30,{fontSize:12.7,color:C.ink});
 text(s,'新 C 下期执行；I 跨期留存。风险分担 ≠ 信息主导。',0.80,4.74,6.70,0.21,{fontSize:12.2,color:C.muted});
 text(s,'长期：何时值得新开工？',8.24,2.08,4.37,0.33,{fontSize:18.5,bold:true,color:C.blue});
 eq(s,String.raw`0\le J_t\perp p_t^J+\chi J_t+\omega_BX_t^B-V_t^J\ge0`,8.23,2.65,4.38,0.41);
 text(s,'Vᴶ 是新项目的贴现续期价值\n其中已扣除未来建设拥挤的影响',8.28,3.23,4.29,0.51,{fontSize:13.2,color:C.muted});
 const xs=[8.27,9.39,10.51,11.63],labs=['开工 J','建设 B','爬坡 Z','产能 Kᵉ'];
 xs.forEach((x,i)=>{rect(s,x,4.00,0.96,0.49,'EEF2F8','D9E1ED',true);text(s,labs[i],x+0.01,4.11,0.94,0.25,{fontSize:12.5,align:'center',color:C.blue});if(i<3)line(s,x+0.98,4.245,xs[i+1]-0.025,4.245,{color:C.blue,width:1});});
 text(s,'t+L 首次可用，再逐步达产；无该阶段时跳过。',8.24,4.74,4.35,0.21,{fontSize:11.7,color:C.muted});
 // Shared feedback, not a causal ordering of market prices.
 text(s,'共同要求：未来预期必须与这套决策规则一致',0.72,5.28,10.2,0.27,{fontSize:14,bold:true});
 const nodes=[{x:0.5,w:3.55,t:'今天的选择',b:'Q、J、I、C'},
              {x:4.62,w:4.07,t:'下一期状态 S′',b:'库存、承诺、能力队列 + 新冲击'},
              {x:9.26,w:3.57,t:'同一模型计算未来量',b:'价格均值/方差、产量和项目价值'}];
 nodes.forEach((n,i)=>{rect(s,n.x,5.77,n.w,0.75,i===2?C.light:'EEF2F6',i===2?'C3DCDA':C.line,true);text(s,n.t,n.x+0.14,5.87,n.w-0.28,0.25,{fontSize:14.3,bold:true,align:'center'});text(s,n.b,n.x+0.10,6.22,n.w-0.20,0.20,{fontSize:11.8,color:C.muted,align:'center'});});
 line(s,4.09,6.13,4.57,6.13,{width:1.4});line(s,8.73,6.13,9.21,6.13,{width:1.4});
 // Feedback route on right margin, then back to both current-decision panels.
 line(s,12.97,6.13,12.97,5.17,{arrow:false,dash:true,width:1});
 line(s,12.84,6.13,12.97,6.13,{arrow:false,dash:true,width:1});
 line(s,12.97,5.17,4.20,5.17,{arrow:false,dash:true,width:1});
 line(s,4.20,5.17,4.20,5.04,{dash:true,width:1});
 line(s,10.42,5.17,10.42,5.04,{dash:true,width:1});
 text(s,'预期回代上面的生产、持货、采购与投资条件，直到相互一致。',0.72,6.66,11.85,0.25,{fontSize:13.4,color:C.muted,align:'center'});
 footer(s,'已整理：结构条件与确定性校核。待完成：完整随机均衡、数据识别与真实估计。规范：E10—E17、E22—E30。',2);
 s.addNotes('【主讲】\n'+talks[1]+'\n\n【完整条件与来源】\n'+noteBlocks[1]+'\n\n模型为动态部分均衡。金融参与不创造吨数；零方差时头寸不唯一；真实合约需期限/结算匹配。');
}
fs.writeFileSync(path.join(path.dirname(OUT),'presentation_sources.json'), JSON.stringify({model:'LC_V2_MACRO_REVIEW_20261030',baseline_commit:'3580f3b1da7cd24c90312c30d4ee200ceee281bc',equations:eqLog,text_boxes:boxes,slides:2},null,2));
pptx.writeFile({fileName:OUT}).then(()=>console.log('Created '+OUT)).catch(err=>{console.error(err);process.exit(1);});
