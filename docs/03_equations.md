# 03｜规范方程 宏观与行业联合闭合版本

当前候选：`LC_V2_MACRO_REVIEW_20261030`；修订：`ALL_CONDITIONS_CLOSURE_20261105`。以用户10月30日材料的宏观、常弹性需求、采购承诺、幂次负荷、在建拥挤、爬坡及三类期货参与者为既有设定。本页补齐全部条件，保持E01—E31编号。早先五行业状态、常数β的版本是受限子模型，不能代表本页的完整扩展。

31组包括原始目标、定义、约束、最优条件、清算和观测，并非31个独立标量方程。完整包络、边界、未知量计数和来源对照见[全条件闭合](14_complete_conditions.md)及[附件对齐](15_source_alignment_1030.md)。

单位为月度、同品级/地点/税费的碳酸锂。Q、D、N是当月吨数，I、C、h^i按吨计，K/B/Z/J按吨每月的能力计，数值式隐含Δt＝1月。所有货币现金流使用同一人民币名义口径；b由匹配口径的月度利率定义。Q是总产量，D是实际耗用，C是下一期耗用承诺，不能重复加入其他总量。h>0为净多头；持有费用h与h^i不同。

## 外部状态与决策参数

### E01

宏观状态和行业余项为
$$
x_t=(g_t,e_t,r_t,\zeta_t)',\qquad
z_t^{id}=(z_t^{A,id},z_t^{m,id},z_t^{J,id},z_t^{N,id},z_t^{f,id})'.
$$
$$
x_{t+1}=A_xx_t+B_x\varepsilon_{t+1}^M,\qquad
z_{t+1}^{id}=R_{id}z_t^{id}+\Sigma_{id}\varepsilon_{t+1}^{id}.
$$
声明联合创新核Π(dε｜x,z)，E_tε＝0、Var_tε＝I_9；基准令两个创新块条件独立，ρ(A_x)<1、ρ(R_id)<1。Π是原始参数的一部分，不能只给一、二阶矩而让未来积分无定义。可复算的有界离散候选是9维独立±1创新，共512个等权分支；这是计算近似，不是行业估计。其他联合核须另行给出并检查状态域。

宏观量对本部分均衡外生，不另添家庭Euler或央行最优规则。计量VAR中的利率创新只有在识别限制成立后才能解释为政策冲击；统计相关不自动等于因果通道。

### E02

宏观量进入既有行为参数：
$$
A_t=D_0\exp(\lambda_g g_t+\lambda_\tau\tau(t)+z_t^{A,id}),\quad
A_t^s=(1-\omega)A_t,\quad A_t^c=\omega A_t,\quad0<\omega<1,
$$
$$
E_t^{FX}=\bar E^{FX}e^{e_t},\qquad
m_t=e^{z_t^{m,id}}\big(\bar m^D+E_t^{FX}\bar m^U\big),
$$
$$
p_t^J=p_0^Je^{z_t^{J,id}},\quad
N_t=N_0+N_*z_t^{N,id},\quad
a_{f,t}=a_{f,0}\exp(\gamma_\zeta\zeta_t+z_t^{f,id}).
$$
\(\bar m^D\)为每吨LC的人民币本地可变成本，\(\bar m^U\)为每吨LC的美元计价投入成本，均非负且合计正；汇率只换算美元部分。此式是为九个外部状态明确指定的聚合成本映射，由本模型选择，不是工程论文原式。工程锚可按路线权重、投入强度与基准投入价核定；CAPEX不进入m。若把多种美元原料价建成独立随机过程，须相应增广状态，不能仍声称只有九个外部状态。

附件中的τ未附状态方程。本候选把τ(t)明确声明为预先给定的确定性技术路径，允许G_t随日历时间变化；定常分析取常数τ。若研究技术随机冲击，应新增其转移和状态维数，而不是凭空增加创新。

月度利率、一期折现和路径折现为
$$
i_t^{(m)}=\bar i^{(m)}+r_t,\qquad
b_t=(1+i_t^{(m)})^{-1}>0,\qquad
d_{t,t}=1,\quad d_{t,s}=\prod_{j=t}^{s-1}b_j.
$$
b_t在t已知。所有一期续期项用b_t；多期随机贴现保留在期望内部。必须要求1+i_t^(m)>0，并验期望折现积的衰减和价值有限性。均值利率为正、AR稳定均不能单独代替此项；见E30。基准常数β仅是b_t≡β的特例。

## 下游使用与收益

### E03

对j=s,c定义
$$
\mathcal B_t^j(x)=\int_{x_*}^xP_*\left(\frac{u}{A_t^j}\right)^{-1/\eta_j}du,
\quad x_*>0,\quad\eta_j>0.
$$
$$
(\mathcal B_t^j)'(x)=P_*(x/A_t^j)^{-1/\eta_j}>0,\quad
(\mathcal B_t^j)''(x)=-\frac{(\mathcal B_t^j)'(x)}{\eta_jx}<0.
$$
η＝1时收益为P_*A_t^j log(x/x_*)；η≠1时为P_*(A_t^j)^(1/η)[x^(1−1/η)−x_*^(1−1/η)]/(1−1/η)。η≤1时零量收益可趋负无穷，不能宣称正参考积分消除了这一边界。正价格下净收益严格凹、有唯一正最优量；大数量时线性支出支配次线性/对数收益。

### E04

当期灵活使用者：
$$
D_t^s=\arg\max_{x>0}\{\mathcal B_t^s(x)-P_tx\},\qquad
(\mathcal B_t^s)'(D_t^s)-P_t=0,
$$
$$
D_t^s=A_t^s(P_t/P_*)^{-\eta_s}.
$$

### E05

实际耗用及数据桥：
$$
D_t=D_t^s+C_{t-1},\qquad
D_t^{data}\simeq\sum_j a_jY_{j,t}+D_t^{other}.
$$
第二式仅用于观测校核，不向清算再加一份耗用。给定旧承诺时，总耗用价格弹性为−η_sD_s/D，不直接等于任一分组弹性。

## 生产者目标与条件

### E06

$$
C_t^Q=m_tQ_t+\frac{\alpha}{\nu+1}\frac{Q_t^{\nu+1}}{(K_t^e)^\nu}
+\frac\kappa2(Q_t-Q_{t-1})^2,
\quad\alpha>0,\nu>0,\kappa\ge0.
$$

### E07

$$
X_t^B=\sum_{h=1}^{L-1}B_t^{(h)},\quad
C_t^J=p_t^JJ_t+\frac\chi2J_t^2+\omega_BJ_tX_t^B,
\quad p_t^J>0,\chi>0,\omega_B\ge0.
$$
保留附件已经加入的在建拥挤，并明确X_t^B是价格接受生产者自身的在建队列合计；对称企业按单位质量归一后汇总。此处采用内部项目拥挤解释，故已有B会影响本企业的未来开工成本。它与永久累计扩产成本不同，不称作Pothen式(7)的等价改写。若b_t≤b_max<∞，χ>2ω_BΣ_(k=1)^(L−1)b_max^(k/2)是贴现平方可和扰动下跨期开工成本严格凸的统一充分条件；价值收敛另验。ω_B＝0只是嵌套对照，不替代本扩展。

### E08

价格接受的生产者选择适应信息集的可行Q/J路径：
$$
\max E_t\sum_{s=t}^{\infty}d_{t,s}
[P_sQ_s-C_s^Q-C_s^J],\qquad 0\le Q_s\le K_s^e,\quad J_s\ge0.
$$
与E10—E12的物理状态转移及有限价值/横截条件共同组成问题。个体Bellman把自己的q_−、K/B/Z与其面对的总量状态分开；偏离自己的选择时不改变市场价格政策。详见[完整个体问题](14_complete_conditions.md)。生产者不开放无限制风险中性期货账户，否则既有风险溢价机制可能消失或出现无界投机。

过去产量的包络量为
$$
W_t^q=\partial_{Q_{t-1}}V_t=\kappa(Q_t-Q_{t-1}).
$$
它是恢复量，不是额外外生过程；其下一期值形成生产条件中的预期调产项。

### E09

$$
P_t=m_t+\alpha(Q_t/K_t^e)^\nu+\kappa(Q_t-Q_{t-1})
-b_t\kappa E_t(Q_{t+1}-Q_t)+\lambda_t-\mu_t^Q,
$$
$$
0\le Q_t\perp\mu_t^Q\ge0,\qquad
0\le K_t^e-Q_t\perp\lambda_t\ge0.
$$
令MC_t^d为第一式除λ−μ^Q外的右侧，则等价于(MC_t^d−P_t)(q−Q_t)≥0，对所有q∈[0,K_t^e]成立。K_t^e>0时恢复λ＝max(P−MC^d,0)、μ^Q＝max(MC^d−P,0)，再代入E13。此max是乘子的等价表达，不是对非法市场量裁剪。

## 建设与爬坡 全部边界

### E10

L≥1为开工到首次可用的月数。定义本期末完成量c_t^K：
$$
c_t^K=\begin{cases}B_t^{(1)},&L\ge2,\\J_t,&L=1.\end{cases}
$$
L≥2时
$$
B_{t+1}^{(h)}=B_t^{(h+1)},\quad h=1,\ldots,L-2;\qquad B_{t+1}^{(L-1)}=J_t.
$$
L＝1时B是空向量，X_t^B＝0，不访问B^(0)。建设阶段不折旧。

### E11

R≥1时
$$
Z_{t+1}^{(0)}=c_t^K,\qquad
Z_{t+1}^{(a+1)}=(1-\delta)Z_t^{(a)},\quad a=0,\ldots,R-2.
$$
R＝0时Z为空向量，新完成量直接进入成熟能力，使用E12第二分支。

### E12

$$
K_{t+1}^M=\begin{cases}
(1-\delta)(K_t^M+Z_t^{(R-1)}),&R\ge1,\\
(1-\delta)K_t^M+c_t^K,&R=0,
\end{cases}
$$
$$
K_t^e=K_t^M+\sum_{a=0}^{R-1}g_aZ_t^{(a)},\quad
0\le\delta<1,\quad0<g_0\le\cdots\le g_{R-1}\le1.
$$
R＝0时求和为空。新完成量在首次进入可用状态前不先折旧；R≥1时退出从已投产的Z和成熟K开始。t期开工首次在t+L可用，其后按g逐步释放。

## 能力价值与投资 全部续期条件

### E13

$$
v_t^K=-\partial_{K_t^e}C_t^Q+\lambda_t
=\frac{\alpha\nu}{\nu+1}(Q_t/K_t^e)^{\nu+1}+\lambda_t.
$$

### E14

$$
W_t^M=v_t^K+b_t(1-\delta)E_tW_{t+1}^M.
$$
R≥1时
$$
W_t^{Z,a}=g_av_t^K+b_t(1-\delta)E_tW_{t+1}^{Z,a+1},\quad a=0,\ldots,R-1,
$$
其中W^(Z,R)按W^M解释。令U_t＝W_t^(Z,0)（R≥1），U_t＝W_t^M（R＝0）。无泡沫基础价值为
$$
W_t^M=E_t\sum_{j=0}^{\infty}d_{t,t+j}(1-\delta)^jv_{t+j}^K,
$$
并要求lim_(n→∞)E_t[d_(t,t+n)(1−δ)^n W_(t+n)^M]＝0。多期d与未来v/W一般相关，不可把期望拆成乘积。

### E15

L≥2时
$$
W_t^{B,1}=-\omega_BJ_t+b_tE_tU_{t+1},
$$
$$
W_t^{B,h}=-\omega_BJ_t+b_tE_tW_{t+1}^{B,h-1},\quad h=2,\ldots,L-1.
$$
已有在建负荷提高本期新开工成本，故负项不能省略。L＝1时不设W^B。等价展开为
$$
W_t^{B,h}=E_t\left[-\omega_B\sum_{j=0}^{h-1}d_{t,t+j}J_{t+j}
+d_{t,t+h}U_{t+h}\right].
$$

### E16

定义开工续期价值V_t^J＝b_tE_tW_(t+1)^(B,L−1)（L≥2），V_t^J＝b_tE_tU_(t+1)（L＝1）。投资KKT为
$$
0\le J_t\perp p_t^J+\chi J_t+\omega_BX_t^B-V_t^J\ge0.
$$
完整多期展开为
$$
0\le J_t\perp p_t^J+\chi J_t+\omega_BX_t^B
+\omega_B\sum_{k=1}^{L-1}E_t[d_{t,t+k}J_{t+k}]
-E_t[d_{t,t+L}U_{t+L}]\ge0.
$$
这是同一条件的两种表示，不能重复施加。未来新开工的拥挤项必须保留；L＝1时相关求和为空。b恒定且ω_B＝0时才恢复β^L E U_(t+L)。

## 一期风险承担主体

### E17

$$
\mu_t^P=E_tP_{t+1},\quad
v_t^P=\operatorname{Var}_t(P_{t+1})\ge0,\quad
\Delta_t=\mu_t^P-F_t.
$$
E30从同一G_t、Φ、Π生成全部条件量，不另设价格或方差AR。正风险分支0<v<∞；v＝0的退化分支单独处理。

### E18

$$
G(I)=hI-\xi\log(1+I/I_0),\quad
G'(I)=h-\frac\xi{I+I_0},\quad
G''(I)=\frac\xi{(I+I_0)^2},
$$
I≥0、I0>0、h≥0、ξ≥0。正偏移允许零库存；这是本文函数设定。

### E19

库存中介选择
$$
\max_{I_t\ge0,h_t^I\in\mathbb R}
\left\{-P_tI_t-G(I_t)+b_t\left[
\alpha_I I_t\mu_t^P+h_t^I\Delta_t-\frac{a_I}{2}v_t^P(\alpha_I I_t+h_t^I)^2\right]\right\},
$$
0<α_I＝1−ℓ≤1，a_I>0。旧存货销售收入和旧合约本期结算对新选择是既定财富项，在无财富效应的逐期进入/退出设定下省略；不是永久企业价值函数的额外库存Euler。

优化头寸后，库存相关目标为−k_t I+ξlog(1+I/I0)，k_t＝P_t+h−b_tα_I F_t。ξ>0时有限最优要求k_t>0；k＝0仍无界。ξ＝0时k<0无界、k＝0库存无差异、k>0选择零库存。

### E20

采购者在t锁定下一期净收益曲线，选择
$$
\max_{C_t>0,h_t^D\in\mathbb R}
 b_t\left[\mathcal B_t^c(C_t)-C_t\mu_t^P+h_t^D\Delta_t
-\frac{a_D}{2}v_t^P(h_t^D-C_t)^2\right],\quad a_D>0.
$$
收益在t+1兑现，但其数量函数和系数在t已知。若收益、基差或履约概率另有随机性，应重新写协方差/约束；本候选未假设这些风险已经包含。

### E21

金融投资者选择
$$
\max_{h_t^f\in\mathbb R}
 b_t\left[h_t^f\Delta_t-\frac{a_{f,t}}2v_t^P(h_t^f)^2\right].
$$
风险参数a_i按下一期人民币收益定义，因此b_t乘整个下一期确定性等价；若对当前贴现现金流直接取方差，方差项为b_t²并须重定义a_i。三类风险资本每期外部给定，均值—方差为直接偏好设定；没有声称由无限期CARA财富问题自动推出。因此不额外引入财富预算Euler。若未来保留结算财富、保证金或融资约束，须新增状态和最优条件。

### E22

所有方差下都有效的持仓FOC为
$$
\Delta_t-a_Iv_t^P(\alpha_I I_t+h_t^I)=0,\quad
\Delta_t-a_Dv_t^P(h_t^D-C_t)=0,\quad
\Delta_t-a_{f,t}v_t^Ph_t^f=0.
$$
v>0时得到
$$
h_t^I=-\alpha_I I_t+\frac{\Delta_t}{a_Iv_t^P},\quad
h_t^D=C_t+\frac{\Delta_t}{a_Dv_t^P},\quad
h_t^f=\frac{\Delta_t}{a_{f,t}v_t^P}.
$$
v＝0时有限最优必须有F＝μ，各头寸目标不再严格凹，头寸不唯一。不要把v＝0放入除法式。

### E23

原始采购数量FOC：
$$
(\mathcal B_t^c)'(C_t)-\mu_t^P+a_Dv_t^P(h_t^D-C_t)=0.
$$
联立E22后
$$
(\mathcal B_t^c)'(C_t)=F_t,\qquad
C_t=A_t^c(F_t/P_*)^{-\eta_c}.
$$
b_t对一期采购整个目标为已知正因子，故在此FOC中约去；不能因此把b从生产或库存条件中删去。

### E24

原始库存数量KKT：
$$
0\le I_t\perp P_t+G'(I_t)
-b_t\alpha_I[\mu_t^P-a_Iv_t^P(\alpha_I I_t+h_t^I)]\ge0.
$$
联立E22后
$$
0\le I_t\perp P_t+G'(I_t)-b_t\alpha_IF_t\ge0.
$$
两式等价，不同时作为额外独立限制。零库存时保留不等式，不强制内点等式。

## 清算与期现联系

### E25

$$
Q_t+N_t+\alpha_I I_{t-1}=D_t^s+C_{t-1}+I_t.
$$
只有实际货物进入物量账；金融持仓和成交量不创造LC。

### E26

$$
h_t^I+h_t^D+h_t^f=0,\qquad
\text{到期支付}=h_t^i(P_{t+1}-F_t),\quad F_{t+1}(t+1)=P_{t+1}.
$$
这定义匹配商品、一期、期末净结算的模型合约。全部头寸支付之和为0。真实广期所逐日盯市、保证金和交割价另在E31匹配。多期利率随机时不另硬加F＝E^Q[P]或F＝bE[P]；本候选的F由上述主体清算产生。

### E27

$$
\mathcal T_t=a_I^{-1}+a_D^{-1}+a_{f,t}^{-1},\quad
H_t=\alpha_I I_t-C_t,\quad
F_t=\mu_t^P-\frac{v_t^P}{\mathcal T_t}H_t.
$$
令w_i＝(1/a_i)/T，恢复持仓为
$$
h_t^I=-\alpha_I I_t+w_IH_t,\qquad
h_t^D=C_t+w_DH_t,\qquad h_t^f=w_fH_t.
$$
v>0时与E22/E26等价；v＝0时仅为连续极限选择。风险溢价RP＝μ−F与当期基差F−P不同。只观测价格通常不足以分别识别三类a，需分类持仓或独立风险容量信息。

### E28

正库存分支可合并为
$$
P_t+h-\frac\xi{I_t+I_0}
=b_t\alpha_I\left[\mu_t^P-\frac{v_t^P}{\mathcal T_t}(\alpha_I I_t-C_t)\right].
$$
此式仅用于解释或事后校核，不是E24/E27之外的新约束，也不用于替代零库存KKT。

## 状态 固定点 观测

### E29

$$
S_t=(x_t',z_t^{id\prime},Q_{t-1},I_{t-1},C_{t-1},K_t^M,
B_t^{(1)},\ldots,B_t^{(L-1)},Z_t^{(0)},\ldots,Z_t^{(R-1)})'.
$$
$$
\dim S=n_x+n_{id}+L+R+3=L+R+12\quad(n_x=4,n_{id}=5).
$$
确定性日历t及τ(t)是给定索引，不新增随机状态；随机技术或美元原料价必须扩维。P/F、μ/v及影子价值是政策或恢复量，不额外加AR。

### E30

写G_t(S)＝(Q,J,D_s,C,I,P,F,W^M,W^B,W^Z)，以及
$$
S'=\Phi(S,G_t(S),\varepsilon),\qquad
\mu_t^P(S)=\int P_{t+1}(S')\Pi(d\varepsilon\mid x,z),
$$
$$
v_t^P(S)=\int[P_{t+1}(S')-\mu_t^P(S)]^2\Pi(d\varepsilon\mid x,z).
$$
E Q'、E W'、E[dJ]和E[dU]都使用同一Φ/Π/G。当前可计算系统为E09、E16、E04、E23、E24、E25、E27七条件，加E14—E15共L+R条价值递推。乘子、W^q和三类持仓随后恢复；企业价值水平V可在政策给定后恢复并作Bellman复核，不是额外独立结构限制；原始条件再独立重算。若保留持仓，则改用E22/E26替代E27，不重复限制。

对每个S应同时满足可行和终值条件：K^e>0、P/F>0、Q∈[0,K^e]、J/I≥0、D_s/C>0；价格二阶矩和个体目标有限；非空域在Π几乎处处后继不变。最大产能下的必要物量条件为K^e+N+α_I I_−−C_−>0。

一个明确的充分折现条件是存在M<∞和ρ_d<1，使sup_S E[d_(t,t+n)]≤Mρ_d^n；有界状态、收益和价值政策下再要求贴现终值为零。均匀0<b_t≤b_max<1是较强的方便特例，不是唯一允许的利率模型。完整TVC、随机折现算子和定义域见[全条件闭合](14_complete_conditions.md)。这些是均衡定义和验收条件，不是已完成全局存在唯一性证明。

### E31

观测采用以下参数明确的映射
$$
y_t^{obs}=H_t\begin{pmatrix}
\log(P_t/P_*)\\\log(F_t/P_*)\\Q_t\\D_t^s+C_{t-1}\\I_t\\K_t^e\\m_t\\p_t^J\\N_t\\C_t\\x_t
\end{pmatrix}+e_t^{obs},\qquad
E[e_t^{obs}\mid\mathcal I_{t-1}]=0,\quad
\operatorname{Var}(e_t^{obs}\mid\mathcal I_{t-1})=\Omega_{obs,t}.
$$
H_t为n_obs,t×14的给定选择/缩放矩阵，须按单位、统计边界、发布时刻和可用观测固定后才能估计；没有C观测时删除对应行，而不是伪造一条数据。I可为0，不默认取log I。风险/景气指标尺度及宏观状态载荷须归一化，避免与λ_g、γ_ζ重复自由缩放。为把统计接口明确给全，本候选取逐期独立的测量噪声 e_t^obs∼N(0,Ω_obs,t)，并与结构创新及初始状态独立；Ω_obs,t为给定的半正定矩阵。这是本文观测假设，非已估计事实。改变噪声核、异方差形式或H须作为显式模型变更。

仅把期限、品级、地点和结算定义匹配的合约观测接到F；主力连续合约不能未经处理代入。年化利率按来源的复利约定转换至月度后接到i^(m)，名义/实际价格与利率不能混用。H_t和工程成本桥用于观测，不再生成第二套独立状态动态。

局部状态空间来自以上政策回代，而非另外估自由转移矩阵。风险补偿依赖条件方差，无风险确定性点的一阶近似可能删除该渠道；数值求解与识别必须保留这一点。
