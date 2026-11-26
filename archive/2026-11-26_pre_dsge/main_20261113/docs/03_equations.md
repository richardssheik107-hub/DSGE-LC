# 03｜规范方程：LC_V2_REVIEW_20261029

**31组包含目标、定义、约束、推导和观测，不是31个状态或31条独立限制。** 以用户收到的V2候选草案为来源重排；未把它升级为已批准或已求解模型。来源SHA256和改动记录见[迁移记录](08_migration.md)。

先读[范围](01_scope.md)与[主体时点](02_agents.md)。所有E编号在[登记表](../model/registry.json)有性质、依赖和来源映射；原文对照及核验层级见[证据](05_evidence.md)。未有相同原式的函数明确属于本文设定。

记号：Q为同口径总生产，D为不含库存的实际耗用，N为成品净进口，I为期末库存，C为下一期耗用承诺，J为启动能力。F_t为t报价、t+1结算的合约；h_t^i为净多头，持有费用h与其不同。K^M为成熟能力，K^e为有效能力；R为爬坡阶段数，mathsf R为外部转移矩阵。

价格正、有效能力正、二阶矩有限是工作域条件，必须经均衡验证，不能靠截断负结果假装满足。

## 2. 外部环境与工程锚

### E01

$$
z_{t+1}=\mathsf Rz_t+\mathsf\Sigma\varepsilon_{t+1},\quad E_t\varepsilon_{t+1}=0,\quad \operatorname{Var}_t\varepsilon_{t+1}=I.
$$

选择五个驱动：z=(z^A,z^m,z^J,z^N,z^f)'，分别为订单、加工成本、建设成本、净进口、金融风险承受环境。R可先取稳定对角阵；扰动分布和参数须使所研究状态域物量可行、价格为正、二阶矩有限。不把这些过程归为某篇文献已验证的行业定律。

### E02

$$
A_t^s=(1-\omega)D_0e^{z_t^A},\quad A_t^c=\omega D_0e^{z_t^A},\quad 0<\omega<1,
$$
$$
m_t=m_0e^{z_t^m},\quad p_t^J=p_0^Je^{z_t^J},\quad N_t=N_0+N_*z_t^N,\quad a_{f,t}=a_{f,0}e^{z_t^f}.
$$

A^s和A^c是参考价格下、不同决策时点的需求规模，不是两份完整总需求。m、p^J的水平由投入和项目资料约束。

工程核算接口（用于成本测量，不另当作第二条独立的成本动态）：
$$
m_t^{eng}=\sum_r w_r\left[\sum_\ell a_{r\ell}\pi_{r\ell,t}^{RMB}+v_{r,t}^{proc}\right],\quad \sum_rw_r=1.
$$
原料量乘人民币投入价格，加未重复计入的可变加工费。该指数是基础成本锚，不等于整条行业边际成本曲线；CAPEX不同时计入生产成本和投资支出。

## 3. 需求：实际耗用与未来排产分开

### E03

对j=s,c定义凹净收益：
$$
\mathcal B_t^j(x)=\int_{x_*}^x P_*\left(\frac{u}{A_t^j}\right)^{-1/\eta_j}du,\quad x_*>0,\quad\eta_j>0.
$$
因此B'>0、B''<0；从正参考量积分避免eta小于1时从0积分发散。它是LC使用的聚合净收益，不是对某家材料企业销售收入的直接测量。

### E04

灵活耗用最优条件：
$$
D_t^s=\arg\max_{x>0}\{\mathcal B_t^s(x)-P_tx\}
=A_t^s(P_t/P_*)^{-\eta_s}.
$$

### E05

实际耗用与数据映射：
$$
D_t=D_t^s+C_{t-1},\qquad D_t^{data}\approx\sum_r a_rY_{r,t}+D_t^{other}.
$$
第二式仅为数据/物量桥，不能再把其右侧重复加进清算。给定既有承诺的短期总耗用弹性为-eta_s D_s/D；文献报告的总弹性不直接等于eta_s或eta_c。

## 4. 生产、投资与约束

### E06

$$
C_t^Q=m_tQ_t+\frac{\alpha}{\nu+1}\frac{Q_t^{\nu+1}}{(K_t^e)^\nu}
+\frac\kappa2(Q_t-Q_{t-1})^2,\quad\alpha>0,\nu>0,\kappa\ge0.
$$
nu=1退回旧负荷函数；nu和alpha仍为待行业证据约束的本文参数，不声称近期工程论文直接给出此式。

### E07

$$
X_t^B=\sum_{h=1}^{L-1}B_t^{(h)},\qquad C_t^J=p_t^JJ_t+\frac\chi2J_t^2+\omega_BJ_tX_t^B,
\quad \chi>0,\omega_B\ge0.
$$
新增的是在建工程拥挤成本，不是永久累计资源耗竭成本。其跨期依赖通过B传播；omega_B=0回到旧投资基准。这是本文可检验设定，不是Pothen原式的等价改写。

### E08

$$
\max_{\{Q_s,J_s\}}E_t\sum_{s=t}^{\infty}\beta^{s-t}
[P_sQ_s-C_s^Q-C_s^J],\quad\beta=(1+r)^{-1}\in(0,1),
$$
受以下物理递推、0≤Q≤K^e、J≥0约束，选择有限价值且满足相应横截条件的解。

### E09

$$
P_t=m_t+\alpha(Q_t/K_t^e)^\nu+\kappa(Q_t-Q_{t-1})
-\beta\kappa E_t(Q_{t+1}-Q_t)+\lambda_t-\mu_t,
$$
$$
0\le Q_t\perp\mu_t\ge0,\qquad0\le K_t^e-Q_t\perp\lambda_t\ge0.
$$
价格在竞争性个体决策中视为给定，在总体均衡中内生。

## 5. 建设与爬坡（L≥2、R≥1）

### E10

$$
B_{t+1}^{(h)}=B_t^{(h+1)},\quad h=1,\ldots,L-2;\qquad B_{t+1}^{(L-1)}=J_t.
$$

### E11

$$
Z_{t+1}^{(0)}=B_t^{(1)},\qquad Z_{t+1}^{(a+1)}=(1-\delta)Z_t^{(a)},\quad a=0,\ldots,R-2.
$$
Z记录已首次投产、尚在爬坡的名义能力；建设期不折旧，投产后按delta退出。

### E12

$$
K_{t+1}^{M}=(1-\delta)(K_t^{M}+Z_t^{(R-1)}),
\qquad K_t^e=K_t^M+\sum_{a=0}^{R-1}g_aZ_t^{(a)}.
$$
0<g_0≤...≤g_{R-1}≤1，达产后系数为1；g由项目资料校准，不默认首年50%。t期开工在t+L进入Z^(0)。L=1时Z'^(0)=J；R=0时取消Z队列，完工量直接进入成熟能力。

## 6. 能力与项目影子价值：不能沿用旧的beta^L W而不作调整

### E13

一单位可用能力的本期服务：
$$
v_t^K=-\partial_{K_t^e}C_t^Q+\lambda_t
=\frac{\alpha\nu}{\nu+1}(Q_t/K_t^e)^{\nu+1}+\lambda_t.
$$

### E14

成熟能力与爬坡能力的边际价值：
$$
W_t^M=v_t^K+\beta(1-\delta)E_tW_{t+1}^M,
$$
$$
W_t^{Z,a}=g_av_t^K+\beta(1-\delta)E_tW_{t+1}^{Z,a+1},\quad a=0,\ldots,R-1,
$$
其中末项W_{t+1}^{Z,R}按W_{t+1}^M解释。

### E15

在建能力的边际价值：
$$
W_t^{B,1}=-\omega_BJ_t+\beta E_tW_{t+1}^{Z,0},
$$
$$
W_t^{B,h}=-\omega_BJ_t+\beta E_tW_{t+1}^{B,h-1},\quad h=2,\ldots,L-1.
$$
负项记录既有在建负荷对本期新开工成本的影响。

### E16

投资条件：
$$
0\le J_t\perp p_t^J+\chi J_t+\omega_BX_t^B-\beta E_tW_{t+1}^{B,L-1}\ge0.
$$
L=1时右侧未来价值改为beta E W^(Z,0)；R=0时W^(Z,0)改为W^M。当omega_B=0且R=0时退回旧beta^L E W^M_(t+L)投资条件。

## 7. 库存、采购套保与投资者

### E17

共同的理性条件矩：
$$
\mu_t^P=E_tP_{t+1},\qquad v_t^P=\operatorname{Var}_t(P_{t+1})>0,
\quad\Delta_t^F=\mu_t^P-F_t.
$$

### E18

净持有成本：
$$
G(I)=hI-\xi\ln(1+I/I_0),\quad I_0>0,\xi\ge0,h\ge0,
\quad G'(I)=h-\frac\xi{I+I_0}.
$$
使用正偏移I0使零库存可行；不是原稿log(I)的无条件等价替换。

### E19

持货/贸易者的一期均值—方差选择：
$$
\max_{I_t\ge0,h_t^I}\{-P_tI_t-G(I_t)
+\beta[\alpha_I I_t\mu_t^P+h_t^I\Delta_t^F
-\tfrac{a_I}{2}v_t^P(\alpha_I I_t+h_t^I)^2]\}.
$$
旧库存本期销售收入对新选择是常数，故从目标中省略。alpha_I=1-ell。

### E20

接到下一期产品订单的采购者：
$$
\max_{C_t>0,h_t^D}\beta[\mathcal B_t^c(C_t)-C_t\mu_t^P+h_t^D\Delta_t^F
-\tfrac{a_D}{2}v_t^P(h_t^D-C_t)^2].
$$
假定订单净收益曲线已在t确定，输入成本存在风险。若成品收入也随机，须增加协方差/另一市场；本候选不宣称包含该风险。

### E21

金融投资者：
$$
\max_{h_t^f}\beta[h_t^f\Delta_t^F-\tfrac{a_{f,t}}2v_t^P(h_t^f)^2].
$$
三类a>0为有效风险厌恶参数（反映总风险承受能力）。一期风险目标为明确的本文简化，非从长期福利函数自动推得。

### E22

持仓一阶条件：
$$
h_t^I=-\alpha_I I_t+\frac{\Delta_t^F}{a_Iv_t^P},\quad
h_t^D=C_t+\frac{\Delta_t^F}{a_Dv_t^P},\quad
h_t^f=\frac{\Delta_t^F}{a_{f,t}v_t^P}.
$$
第一项分别为库存的卖出套保和未来采购的买入套保；共同的第二项为承担风险的头寸。

### E23

新排产数量：
$$
(\mathcal B_t^c)'(C_t)=F_t\quad\Longrightarrow\quad C_t=A_t^c(F_t/P_*)^{-\eta_c}.
$$
这是E20两项一阶条件联合推出，不是额外把期货价格硬塞进现货需求。

### E24

库存条件：
$$
0\le I_t\perp P_t+G'(I_t)-\beta\alpha_I F_t\ge0.
$$
它由E19对库存的一阶条件和E22第一式联合推出；不能再同时保留旧风险中性Euler等式作为另一条约束。

## 8. 两个市场清算与价格连接

### E25

现货清算：
$$
Q_t+N_t+\alpha_I I_{t-1}=D_t^s+C_{t-1}+I_t.
$$
排产承诺在实现耗用时计一次，库存按存量差计；期货换手和持仓不加入物量账。

### E26

期货清算与结算：
$$
h_t^I+h_t^D+h_t^f=0,\qquad F_{t+1}(t+1)=P_{t+1}.
$$

### E27

由E22+E26推出（是等价简化，不能额外计作独立限制）：
$$
\mathcal T_t=\frac1{a_I}+\frac1{a_D}+\frac1{a_{f,t}},\qquad
F_t=\mu_t^P-\frac{v_t^P}{\mathcal T_t}(\alpha_I I_t-C_t).
$$
风险溢价由净实物套保压力和风险承受能力共同决定；可正可负，不预设期货恒低于预期现货。这里不能再硬加F=beta E[P]。

### E28

正库存时，E24与E27合并为：
$$
P_t+h-\frac\xi{I_t+I_0}
=\beta\alpha_I\left[\mu_t^P-\frac{v_t^P}{\mathcal T_t}(\alpha_I I_t-C_t)\right].
$$
此式呈现“风险承担环境→期货价格/套保→库存与新排产→现货及未来供需”的反馈，仍须与全部条件联立，不单独作为外生因果回归。

## 9. 理性预期、状态与观测

### E29

$$
s_t=(z_t',Q_{t-1},I_{t-1},C_{t-1},K_t^M,B_t^{(1)},\ldots,B_t^{(L-1)},Z_t^{(0)},\ldots,Z_t^{(R-1)})'.
$$
五个外部状态下维数n_s=L+R+8；一般式n_z+L+R+3。完整状态数不是沿用旧L+4。影子价值、P、F为政策函数/当期结果，不独立加AR。

### E30

$$
u_t=\mathcal G(s_t;\theta),\quad s_{t+1}=\mathcal F(s_t,u_t,\varepsilon_{t+1};\theta),\quad P_t=\mathcal P(s_t;\theta).
$$
E17中mu、v由同一mathcal F和mathcal P产生的下期分布计算。这是闭合预期的固定点，不能独立填入另一条价格预测。

### E31

$$
y_t^{obs}=\mathcal M_t\big(P_t,F_t,Q_t,D_t,I_t,K_t^e,m_t,p_t^J,N_t\big)+e_t.
$$
M按单位、品级、交割地点、统计范围及发布时间映射。基线为月度，只使用到期距离匹配的报价；多期限不能全部当同一个一期F。若建混频模型，日度状态转换、月度流量加总和存量时点都要重新一致定义，不能把月度T每天乘一次。

局部近似可写为u~=U s~、s~'=T s~+S eps，且T=A0+B0 U；但新模型不是旧共同剩余最大化问题，不能未经证明直接复用旧Riccati目标。风险溢价包含条件方差，围绕无风险确定性稳态的一阶近似可能抹去金融渠道，需非线性或保留风险的高阶求解。
