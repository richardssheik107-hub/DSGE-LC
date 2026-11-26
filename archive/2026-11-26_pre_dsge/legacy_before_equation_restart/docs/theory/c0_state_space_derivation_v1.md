# C0 状态方程推导 v1：从主体行为到状态空间

日期：2026-09-19。状态：CANDIDATE_DERIVATION_NOT_ESTIMATED。

本文件完成“状态方程从哪里来”这一工作包：从已经选定的 C0 两类主体、E24 库存闭合和市场清算出发，推导出

\[
x_t=A(\theta)x_{t-1}+B(\theta)\varepsilon_t+C(\theta)u_t.
\]

它不是新实证结果，不改变 M0/R1/R3，不代表导师批准或 D02 已冻结。

## 1. 仿照生猪论文的是建模顺序

生猪参考稿值得借鉴的是：

\[
主体目标与约束
\rightarrow 一阶条件
\rightarrow 市场关系
\rightarrow 稳态或局部化
\rightarrow 状态空间
\rightarrow 观测方程.
\]

本项目采用相同顺序，但不复制家庭、Taylor rule、Harvey 周期和期货部门。C0 只保留参考锂盐生产商、一个直接耗用 LC 的材料制造商、实物库存核算和市场清算。

## 2. 先区分 state、control 与 equilibrium output

候选定义：

- 动态状态：需求环境 \(z_t^D\)、单位成本环境 \(c_t\)、参考产量 \(Q_t\)；
- 会计状态：实物库存 \(I_t\)。在 E24 下它记录跨期存量，但不反馈价格；
- 当期控制变量：材料产出 \(Y_t\)；
- 当期均衡变量：LC 价格 \(P_t\)；
- 条件输入：非 LC 成本 \(v_t\)、其他用途 \(U_t^{other}\)、净补库 \(J_t\)、成品 LC 净进口 \(N_t\)、其他 LC 成品产量 \(R_t\)。

扩展会计状态向量为

\[
x_t=[z_t^D,\ c_t,\ Q_t,\ I_t]'.
\]

其中真正进入价格—生产反馈的核心维数为前三个；\(I_t\) 在 E24 中是被动会计状态。若未来改用 E23，库存才成为行为反馈状态。

## 3. 原始经济方程

### 3.1 需求环境与成本环境

为了得到最小动态系统，先写：

\[
z_t^D=\rho_D z_{t-1}^D+\sigma_D\varepsilon_t^D,
\qquad |\rho_D|<1,
\tag{S01}
\]

\[
c_t=\rho_C c_{t-1}+\sigma_C\varepsilon_t^C,
\qquad |\rho_C|<1.
\tag{S02}
\]

经济水平映射为

\[
A_t=\bar A+z_t^D,\qquad m_t=\bar m+c_t.
\tag{S03}
\]

这里 \(c_t\) 不是原 M0 的标准化 SC6 月涨幅；它是同单位 LC 可变成本 \(m_t\) 相对参考点的偏离。若以后能够完整观测 \(m_t\)，可把 \(c_t\) 从状态移到已知输入，进一步降维。

### 3.2 生产商

沿用 C02/C03：

\[
\max_{0\le Q_t\le K_t}
(P_t-m_t)Q_t-\frac g2Q_t^2-\frac\kappa2(Q_t-Q_{t-1})^2,
\]

内点时

\[
(g+\kappa)Q_t=P_t-m_t+\kappa Q_{t-1}.
\tag{S04}
\]

### 3.3 材料制造商

沿用 C04/C05，并固定本轮下游调整成本 \(\zeta=0\)：

\[
\max_{0\le Y_t\le\bar Y_t}
A_tY_t-\frac b2Y_t^2-(v_t+aP_t)Y_t,
\]

\[
bY_t=A_t-v_t-aP_t.
\tag{S05}
\]

### 3.4 物量守恒与 E24

\[
I_t=(1-\ell_I)I_{t-1}+Q_t+R_t+N_t-aY_t-U_t^{other}.
\tag{S06}
\]

定义净补库

\[
J_t\equiv I_t-(1-\ell_I)I_{t-1},
\]

得到市场清算

\[
Q_t+R_t+N_t=aY_t+U_t^{other}+J_t.
\tag{S07}
\]

E24 的含义是：本轮条件于独立给定或核验的 \(J_t\)，不同时使用 E23 决定库存选择。

## 4. 先解价格，再解产量

记

\[
G\equiv g+\kappa>0,
\qquad
D\equiv \frac{a^2}{b}+\frac1G>0.
\]

由 S04、S05、S07 联立，得到条件内点价格：

\[
P_t=
\frac{
\frac{a(A_t-v_t)}b
+U_t^{other}+J_t-N_t-R_t
+\frac{m_t-\kappa Q_{t-1}}G
}{
D
}.
\tag{S08}
\]

在参考点附近写偏离量，定义

\[
\phi_A\equiv\frac{a/b}{D},\quad
\phi_m\equiv\frac{1/G}{D},\quad
\phi_Q\equiv-\frac{\kappa/G}{D},\quad
\phi_F\equiv\frac1D.
\]

则

\[
p_t=
\phi_A z_t^D+\phi_m c_t+\phi_Q q_{t-1}
-\phi_A v_t+\phi_F U_t^{other}
+\phi_F J_t-\phi_F N_t-\phi_F R_t.
\tag{S09}
\]

价格因此是均衡输出，不是另加一个独立 AR 状态。

将 S09 代回生产一阶条件：

\[
q_t=\eta_D z_t^D+\eta_C c_t+\eta_Qq_{t-1}
+\frac1G f_P'u_t,
\tag{S10}
\]

其中

\[
\eta_D=\frac{\phi_A}{G}>0,
\qquad
\eta_C=\frac{\phi_m-1}{G}<0,
\]

\[
\eta_Q=
\frac{\kappa}{G}+\frac{\phi_Q}{G}
=
\frac{\kappa}{G}\left(1-\frac1{GD}\right)\ge0,
\]

\[
u_t=[v_t,\ U_t^{other},\ J_t,\ N_t,\ R_t]',
\]

\[
f_P=[-\phi_A,\ \phi_F,\ \phi_F,\ -\phi_F,\ -\phi_F]'.
\]

这样，原 M0 中“产量有惯性、价格促进生产、成本抑制生产”的直觉，被同一组 \(g,\kappa,a,b\) 共同约束。

## 5. 显式写出 A、B、C

把 S01/S02 代入 S10，并把库存写成

\[
i_t=(1-\ell_I)i_{t-1}+j_t.
\tag{S11}
\]

于是

\[
x_t=A(\theta)x_{t-1}+B(\theta)\varepsilon_t+C(\theta)u_t,
\]

其中

\[
x_t=
\begin{bmatrix}
z_t^D\\ c_t\\ q_t\\ i_t
\end{bmatrix},
\qquad
\varepsilon_t=
\begin{bmatrix}
\varepsilon_t^D\\ \varepsilon_t^C
\end{bmatrix}.
\]

状态转移矩阵：

\[
A(\theta)=
\begin{bmatrix}
\rho_D&0&0&0\\
0&\rho_C&0&0\\
\eta_D\rho_D&\eta_C\rho_C&\eta_Q&0\\
0&0&0&1-\ell_I
\end{bmatrix}.
\tag{S12}
\]

冲击矩阵：

\[
B(\theta)=
\begin{bmatrix}
\sigma_D&0\\
0&\sigma_C\\
\eta_D\sigma_D&\eta_C\sigma_C\\
0&0
\end{bmatrix}.
\tag{S13}
\]

条件输入矩阵：

\[
C(\theta)=
\begin{bmatrix}
0&0&0&0&0\\
0&0&0&0&0\\
-\phi_A/G&\phi_F/G&\phi_F/G&-\phi_F/G&-\phi_F/G\\
0&0&1&0&0
\end{bmatrix}.
\tag{S14}
\]

这就是当前“状态方程”的最明确答案：矩阵元素由主体条件和清算式消元得到，不是先手写矩阵再解释。

## 6. 价格与材料产出的均衡输出映射

可进一步写：

\[
\begin{bmatrix}
p_t\\y_t
\end{bmatrix}
=
H^e(\theta)x_{t-1}
+D^e(\theta)\varepsilon_t
+F^e(\theta)u_t.
\tag{S15}
\]

价格行：

\[
H^e_P=
[\phi_A\rho_D,\ \phi_m\rho_C,\ \phi_Q,\ 0],
\]

\[
D^e_P=
[\phi_A\sigma_D,\ \phi_m\sigma_C],
\]

\[
F^e_P=
[-\phi_A,\ \phi_F,\ \phi_F,\ -\phi_F,\ -\phi_F].
\]

材料产出来自

\[
y_t=(z_t^D-v_t-a p_t)/b,
\]

因此第二行不是新的自由方程，而是 S05 的代数结果。

注意：\(H^e\) 是经济均衡输出映射，不是最终统计观测矩阵。

## 7. 真正的观测方程仍需单独冻结

真实观测口径是混合变换，因此最终观测不能简单写成“变量等于状态”：

\[
y_t^{P,obs}
=
\frac{\Delta\log P_t-\mu_P}{s_P}
+e_t^P,
\tag{S16}
\]

\[
y_t^{Q,obs}
=
\frac{\Delta_{12}\log(Q_t+R_t)-\mu_Q}{s_Q}
+e_t^Q.
\tag{S17}
\]

如果只有装车数据，则

\[
Battery_t^{obs}\neq Y_t,\qquad Battery_t^{obs}\neq aY_t.
\]

它只能在有产业映射证据后作为 \(z_t^D\) 或 \(A_t\) 的 noisy proxy。SC6 也不能直接等同于 \(c_t\)，而要经过同单位成本映射。库存若进入观测，应优先使用同口径月末存量。

所以本轮完成的是 transition derivation，而不是把旧 measurement.py 直接接到新模型。

## 8. 为什么库存虽然在 x 中，却不是本轮价格反馈状态

E24 给定 \(J_t\) 后：

\[
i_t=(1-\ell_I)i_{t-1}+j_t,
\]

而 S09 中价格依赖的是 \(J_t\)，不是 \(I_{t-1}\)。所以库存是有物理跨期性的会计 state，但不是 active feedback state。

若导师要求“库存水平本身影响储存决策和价格”，必须进入 C1，用 E23 替换 E24；届时 \(I_t\) 会进入前瞻行为系统，并需要重新求解，不能沿用 S12–S14。

## 9. 与原 M0 的关系

| M0 | C0 中的位置 | 关系 |
|---|---|---|
| \(d_t\) | \(z_t^D\) | 旧需求代理对应新需求环境思想，但参数不迁移 |
| \(c_t\) | \(c_t\) | 名称相似但对象不同；新对象是 CNY/tLC 单位成本偏离 |
| \(q_t\) | \(q_t\) | 旧经验调整式升级为生产最优条件推导 |
| \(n_t\) | \(I_t/J_t\) | 旧增长失衡指数不能改名成物理库存 |
| \(p_t\) | \(p_t\) 均衡输出 | 新价格由清算推出，不再独立 AR |

原 M0 继续作为半结构实证基线；新 C0 的矩阵和观测改变后必须新估计。

## 10. 导师面前最短解释

> 我们不是先规定一个状态矩阵。先选择锂盐生产商和材料制造商，写出生产调整成本下的利润最大化与材料产出选择，再用 LC 物量守恒闭合市场。需求环境和单位成本环境具有跨期持续性，参考产量因为调整成本继承上一期，库存因为物理存量继承上一期；因此它们才进入状态向量。价格和材料产量是当期均衡结果。把一阶条件与清算式联立消元后，矩阵 A、B、C 的每个系数都能追溯到 \(g,\kappa,a,b,\rho_D,\rho_C\) 等经济参数，而不是独立拍定。

## 11. 当前边界

本推导只在内点、单参考生产块、单材料组、E24 条件净补库、需求/成本 AR 候选过程下成立。容量角点、停产、内生储存、前瞻投资、贸易行为、回收队列都会改变系统。

矩阵可写、合成代数通过，不等于参数已识别、数据已匹配或线性 Kalman 已适用于真实样本。
