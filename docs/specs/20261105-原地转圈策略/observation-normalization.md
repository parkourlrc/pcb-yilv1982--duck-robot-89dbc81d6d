# 观测归一化与双机统计核对

日期：2026-11-06。用户要求详细解释观测均值、方差。仅核对和说明，未改训练配置。

依据：本项目 `training/mjlab_duck/locomotion_env.py:399`；spark1实际依赖 `/home/yilv/dspark/duck-benchmark-20261106/venv/lib/python3.12/site-packages/rsl_rl/modules/normalization.py` 的EmpiricalNormalization、`models/mlp_model.py` 的_get_latent/update_normalization及导出包装、`algorithms/ppo.py:155` 的process_env_step。本机实际版本见正式run.json。在线官方检索未获得可引用正文，具体实现以本次读取的安装源码为准。

61维分别为角速度3、重力方向3、相对HOME关节位置14、关节速度14、上一raw动作14、命令3、保留零10。每个维度单独维护均值/方差，不把61个异单位量混成一个统计。每rank的2048环境提供批次，按历史样本数累计合并，而非每环境独立或只看当前一帧。actor/critic各有归一化模块，当前观测与更新调用相同，不应臆断两者统计一定不同。

本版公式：`normalized=(x-mean)/(sqrt(variance)+0.01)`，epsilon在根号外。mean、var、std、count为buffer，不是Adam学习的权重。训练process_env_step分别更新actor/critic统计；eval模式冻结，checkpoint含统计，官方导出包装也包含normalizer。该处理是尺度变换，不估计缺失速度、不滤波、不保证输出[-1,1]。

示意（非实测）：同一输入0.10，rank0 mean0/std0.04输出2；rank1 mean0.05/std0.09输出0.5。相同MLP权重因此可收到不同输入，不能保证同一raw观测的动作相同。应将完整策略视作归一化状态加网络权重（随机策略另有动作分布参数）。当前启动广播相同状态，但后续normalizer按本地数据更新，梯度同步不合并这些buffer。

这与动作Gaussian探索std是不同量：前者61维输入尺度，后者14维输出随机噪声。已观察到动作std失控与raw动作历史进入观测，可能影响输入统计，但未做两rank统计差异定量对照或归一化消融，不能将归一化认定为首轮失败根因。

后续可选择跨rank汇总count、sum、sum-of-squares或等价稳定在线矩合并，保持归一化坐标一致；不能只平均局部方差，必须包含局部均值差异。同步频率和额外通信需设计，当前仅作解释与备选，不改变已提出的下一版方案。
