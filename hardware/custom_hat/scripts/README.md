# HAT 工程处理流程

2026-10-31：修改先在完整副本执行，再核源摘要及差异后回写；不得按路由结果放宽规则凑通过。明确制造工艺变更须有来源、范围和反例。使用KiCad Python（含pcbnew），必要时设置KICAD_CLI。

A.1接口/钢网阶段：`repair_qwiic_pinout.py`在完整候选交换J502四针和局部引线，`verify_qwiic_pinout.py`仅豁免这四针的有意改网并核其正确锚点，其余旧连接/I2S取样必须保持。构建已执行，勿盲重跑。`export_dnp_stencil.py`只在绘图副本去DNP paste，逐项比较拟装开口及其它9层；`audit_complete_bom.py`重新解析原始/最终paste，防止仅改manifest放过旧开口。

当前只读软件审计通过`pipeline.current_checkpoint()`读取`hardware/custom_hat/current-review.json`，核完整源指纹、checkpoint/原生报告SHA、DRU加载及规则SHA；不能凭目录名或mtime选版本。`bind_current_review.py`只绑定已检查/导出的身份，不放行制造。`build_fabrication_review_bundle.py`生成本地便携CAM资料，白名单打包并排除内部运行路径，不发送、不下单。

主控软件阶段：`inspect_radxa_runtime_package.py`只解析官方deb的配置/模块/DTB，不安装包；`prepare_codec_module_build.py`和`build_codec_module.py`在本机私人缓存/WSL构建codec模块，拒绝覆盖已有交付目录。`verify_codec_overlay.py`核两种官方Zero3W DTB合并后的实际pinctrl/供电/DAI引用，`audit_offline_audio_package.py`绑定源码、ABI、overlay及未改变的PCB审查身份。运行使用普通Python和本机WSL，不会部署到Radxa；硬件和现场适用性仍未验收。

音频路由阶段：`build_audio_control_catalog.py`从已编译驱动的精确源提取AIC3104控件，排除该型号没有的额外控件；`verify_audio_routing.py`用模拟amixer后端检查元数据拒绝、写入顺序、失败/中断静音及组合。`audit_audio_routing.py`用KiCad Python核真实针网、资料/源码/模块/模拟报告与主板身份。实际用户入口是software/codec/hat_audio.py；默认plan无设备访问，inspect只读，apply需显式指定新报告。实际声卡与声音未验收。

BMI088阶段：`build_bmi088_adapter.py`构建普通BMI088的双I2C端点Linux程序；`verify_bmi088_transport_faults.py`仅以host假设备系统调用检查身份错误、部分读、NACK和内核占用，未访问真实I2C；两者用普通Python/WSL。`audit_bmi088_adapter.py`用KiCad Python把产物/源码/故障报告绑定到主板SDO/PS/CSB/SCL/SDA真实焊盘和原SHA，确认无PCB变化。WSL路径统一先resolve真实Windows位置，避免应用LOCALAPPDATA重定向导致源码找不到。

codec复位阶段已执行：`connect_codec_hardware_reset.py`建立指定GPIO完整副本，`route_codec_reset_multilayer.py`基于现有参考铜保护搜索；`bridge_codec_supply_after_reset.py`用已有孔补回3.3V，`verify_codec_reset_route.py`核原铜/连接及参考铜逐点差异。采用Pin33，Pin15/36失败历史不能重跑覆盖。`tidy_interface_schematic_labels.py`整理图纸，`render_codec_reset_review.py`生成原生预览，`audit_codec_reset_checkpoint.py`确认四端RESET、原RC和同版绑定。

`generate_rev_a.py`默认入口已禁用，历史生成函数仅留为研究代码。载入PCB必须使用完整副本内的同名工程路径；从独立备份载入再保存可能把默认设置写进项目。先复制回工作路径再LoadBoard，保存后检查项目/DRU哈希；不要忽略这种变化产生的报告。

规则加载勘误已落实：旧DRU缺单位，CLI仍可出报告。pipeline先用临时完整副本的9mm孔径哨兵证明加载，正式/哨兵报告分开；缺证据即失败。promote要求加载证明与DRU哈希一致。两条过宽原型规则已退役，align_rules默认入口禁用，不能重写主工程。

功放阶段：improve_amplifier_decoupling.py、finish_amplifier_feed.py和verify_amplifier_decoupling.py处理C323/C328及局部VDD/地回路，calculate_amplifier_cap_margin.py仅计算厂商典型模型情景。已完成的候选不可盲重跑。

原理图显示：颜色/全局线宽试验未起效并已撤回；最终set_candidate_netclass_wire_style.py只补网络类wire_width=6、line_style=0（原理图显示值）。manifest登记批准的项目设置SHA，其他电气/制造字段结构等价。shift_passive_schematic_labels.py只移位号/值显示坐标；Sheet.component仅改未来新增被动件的标注位置，禁止运行旧生成器main重建主工程。

装配导出：export_assembly_plan.py产生拟装/SMT BOM、SMT坐标和逐件意向；render_assembly_views.py仅改一次性显示副本，源不变，随后清除。底面图镜像，CSV不再镜像。checkpoint核导出前后源指纹，audit_complete_bom核坐标/方向和过滤子集。现行58拟装件传--expected-fitted 58；旧数量按对应源哈希，不改数量检查掩盖缺件。

主控5V阶段：inspect_five_volt_paths.py的铜相交图仅用于找路径，其整段L/W代价不是等效电阻；widen_five_volt_header.py与fit_five_volt_trunk.py只改指定内层负载路径，verify_five_volt_header.py保留全部原连接和F面反馈铜。calculate_five_volt_budget.py只算明确铜段/假设负载，不能当整板端点电压验收。已执行的构建脚本有基线和重复保护，不盲重跑。

checkpoint_i2c_review.py review可显式传--reuse-lifecycle：先逐项比较位号/MPN/DNP身份，完全一致才复制前版结果并记录来源SHA、原日期和“未新查询”；换料则拒绝。布局变化仍重跑受影响的PCB/Gerber/交叉/EMC等检查，不把36个unknown升级为在产或库存通过。

电流路径阶段：widen_main_power_paths.py、fit_widened_power_paths.py仅改共用入口及SERVO_VBAT指定铜段，verify_main_power_paths.py核全部原连接；calculate_power_path_budget.py按明确的1oz/25°C等假设计算指定正极铜段，不能出整板额定。构建已执行，不盲重跑。

导出新增quarantine_default_gerber_job.py：PCB无明确stackup时，将KiCad自动合成默认叠层的.gbrjob原件按SHA移到专题证据，生产审查包不包含它；checkpoint_i2c_review.py已接入。audit_complete_bom.py同时核默认Job策略、归档SHA和意外输出文件；旧包保留为历史证据，不用来补齐新包。显式stackup也不代表厂商已接受或自动允许下单。

I2S参考铜阶段：inspect_i2s_reference_planes.py核原生填铜和连通；单网换层/扇出以及reroute_lrck_ground_reference.py的未连通候选已停用。inspect_reference_stitch_obstacles.py定位真正挡孔的音频线，complete_i2s_reference_stitch.py仅绕行该线并加1个地孔，verify_i2s_reference_stitch.py核全板原连接及地铜变化，render_reference_stitch_review.py生成对照图。第二个补孔没有目标线路收益，已拒绝恢复。构建脚本有基线/重复执行保护，不能盲重跑或把失败副本当主工程。

电容阶段：upgrade_buck_capacitors.py及verify_capacitor_upgrade.py管理四颗1210替换；calculate_capacitor_checkpoint.py只计算已归档模型。LDO阶段用improve_ldo_capacitors.py、fit_ldo_candidate.py和verify_ldo_capacitors.py建立/修正/核对完整候选，analyze_ldo_margin.py输出有边界的被动网络计算，render_ldo_review.py制作局部图；均已执行，不盲重跑有基线保护的构建脚本。R703只串C309支路，验证器核其隔离网和其余所有原连接。新增R703后BOM独立预期为55，运行audit_complete_bom.py时显式传--expected-fitted 55；旧检查点默认仍54。pcbnew封装须先加入board再Flip，否则本机KiCad10原生接口可发生access violation。

从仓库根目录执行：

```powershell
$kiPython = Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin\python.exe'
& $kiPython hardware/custom_hat/scripts/pipeline.py prepare
```

输出工作目录 `hardware/custom_hat/runs/<时间-编号>/work` 与报告目录。完整副本含主 PCB、工程规则、原理图/子页、库表/本地库和契约；历史路由/生产文件不作为输入。manifest 保存每个源文件 SHA256。不会运行 build、stitch、autoroute，不改变源文件。

修改工作副本后重新检查：

```powershell
& $kiPython hardware/custom_hat/scripts/pipeline.py check --project 'hardware/custom_hat/runs/<时间-编号>/work'
```

每次报告独立保存：CLI 版本/命令/日志、实际导出网表、ERC、重铺铜且含 schematic parity 的 DRC、网表与板焊盘/契约差异、源摘要。violations、unconnected_items、schematic_parity 分列。NC空网兼容历史副本；现行32个NC已有独立网，4个带斜杠的NC按XML `/` 与PCB `{slash}`精确等价核对，并单列nc_escaped，不忽略其他引脚差异。

退出码：0=离线检查无未解释项（仍不是制造放行）；2=已执行检查但设计有阻塞；1=工具/输入失败。不得把非零码忽略后继续读旧报告。源或工作副本在检查期间变化，检查报失败。

只有电气/几何与一致性前置检查通过后才允许自动路由；允许尚有未连接，必须显式传入工作副本：

```powershell
& $kiPython hardware/custom_hat/scripts/autoroute.py --project 'hardware/custom_hat/runs/<时间-编号>/work' --passes 20
```

路由另建完整候选，不改输入工作副本或主工程。使用唯一 DSN/SES 路径，检查导出、路由退出码、导入成功、源与 DSN 摘要。原制造规则保持不变；输出还需检查，不能因为 SES 存在就认为完成。当前主板一致性已经清零，但这不自动授权改变制造规则或重做已通过的布线。

`build_pcb_rev_a.py` 与 `dsn_power_class.py` 已停止命令行执行，保留历史实现供追溯。其余旧补孔/扇出脚本不是新流程入口，部分写死主路径，禁止直接用于现行工程。先完成几何/网络依据再修复相应脚本，不盲跑实验。

本流程只生成候选和检查点，不自动回写主工程。设计者审查实际修复、制造条件与变化后再决定回写；默认不提交、不下单、不操作硬件。工作副本在 runs 下本地留存；审计证据长期保存在 docs/references 对应专题。

`repair_release_metadata.py`、`finish_release_metadata.py` 为指定基线的元数据修复；`verify_release_metadata.py` 将两份完整副本重新铺铜并保存，再比较焊盘/走线几何与连通分区。`promote_release_metadata.py` 仅在源摘要、已检查候选和几何检查全部匹配时回写逐项文件并备份。已经执行的修复不要盲目重跑；记录见 metadata-repair-20261030。
## I2C5修复检查点补充

控制回路阶段：inspect_buck_control.py冻结原网/支路；relayout_buck_control.py移动4个无源件并重布；finish_buck_control.py修电容间距、用原生铜形状简化取样支路；verify_buck_control.py核刚体几何、拓扑、保护字段和取样接触范围，已回写。render_buck_control_annotations.py生成已检查标注，见[控制回路专题](../../../docs/references/hat-simulation-tools-20261029/buck-control-20261031/research.md)。

电容数据：collect_capacitor_models.py取原厂逐料号specsheet；extract_capacitor_plots.py提取原生PNG；digitize_capacitor_bias.py做明确标为典型模型/假设的敏感性计算，不会改CAD或给出实物稳定性结论。失败地址、模型误差与候选见[电容专题](../../../docs/references/hat-simulation-tools-20261029/capacitor-models-20261031/research.md)。

Buck阶段：plan_buck_thermal_vias.py作全层候选检查；relocate_ldo_input_cap.py/route_relocated_ldo_cap.py腾出背面空间、重接C308及音频使能；add_buck_thermal_vias.py加5个热孔并标填孔盖铜；move_buck_input_cap.py/finish_buck_input_cap.py移C303与局部BUCK_EN；verify_buck_thermal.py核允许变更、原连接及三层地铜接触。export_buck_fabrication_requirements.py导6处工艺清单和有边界的损耗示意，render_buck_thermal_annotations.py生成已检查标注图。均已回写，不能在新基线上盲重跑；详见[Buck专题](../../../docs/references/hat-simulation-tools-20261029/buck-thermal-20261031/research.md)。

全量料号阶段：collect_final_bom_sources.py归档JST官方目录/原厂镜像和Vishay数据；select_final_bom.py针对ac2df157基线选择最后8件、修改L301/R309焊盘；fit_final_power_parts.py与reroute_final_audio_branch.py处理3个via及音频支线避让，均已回写。verify_final_bom.py核4个允许焊盘变化及原连通保留；calculate_final_power_parts.py仅计算显式假设下的电感/跳线，不作整板电气或热放行。见[现行记录](../../../docs/references/hat-simulation-tools-20261029/final-bom-20261031/research.md)。

audit_complete_bom.py通过--expected-fitted指定本检查点拟装数量，核原理图/PCB五字段一致、BOM/坐标/SMT子集、装配分类、源和输出指纹及新链接；只证明文件一致与字段覆盖，不把它当器件适用性/库存/制造放行测试。现行数量见Rev A入口，不沿用旧默认54。

连接器阶段：collect_connector_sources.py归档原厂文件；select_header_connectors.py/finish_header_connectors.py修J101实体和4个座的孔径/料号，定义H1/H2头部尺寸；verify_header_connectors.py核53个钻孔改变之外的焊盘/走线不变及连接保留，均已执行。

环宽阶段：improve_via_annular_rings.py、finish_via_annular_rings.py和stitch_ldo_ground_plane.py完成23通孔扩大及地恢复；verify_annular_rings.py严格核允许的铜变更、环宽及原连接。preserve_ldo_ground_neck.py/bridge_ldo_ground.py为未采用的失败尝试；前者已改正无配套项目加载导致的副本规则重置。上述脚本仅对应记录基线，不盲重跑。audit_annular_checkpoint.py核产物指纹与规则护栏，专题见[现行审查](../../../docs/references/hat-simulation-tools-20261029/annular-rings-20261031/research.md)。

pipeline现在先核.kicad_pro指纹，默认须与prepare源一致；有意修改工程设置时须先审阅差异，再把准确哈希记录到该run manifest的approved_project_settings_sha256。没有记录时直接拒绝跑不可比的DRC；不为绕过失败随意填写该字段。DRU的有意加严另随检查点保存。

后续物料：collect_bom_sources.py归档原厂资料、哈希与失败；select_passive_parts.py仅适用于d0e549e2基线，在副本同步电容/TVS的设计料号，已执行。audit_passive_checkpoint.py核现行源/输出指纹、所选属性和新导航。选型不代表DC bias/ESR/热/采购放行，见[物料专题](../../../docs/references/hat-simulation-tools-20261029/bom-passives-20261031/research.md)。

`add_i2c_pullups.py`仅用于d4fc46fa基线，已执行回写，不可对现行板盲重跑。`select_signal_resistors.py`在完整副本同步9个既有电阻MPN；`verify_i2c_pullups.py`检查新增焊盘和原连接保留；`checkpoint_i2c_review.py`输出同版审查包并调用kicad-happy；`render_i2c_review.py`生成原生PCB图和资料页。来源与执行记录见[专题](../../../docs/references/hat-simulation-tools-20261029/i2c-pullups-20261031/research.md)。

`repair_cap_vias.py`针对a9650831基线移动C305/C309通孔，已执行回写；`verify_cap_vias.py`核原焊盘/网络/连通保留、只改指定4个原铜对象，并读取实际Mask expansion。新审查包通过`checkpoint_i2c_review.py --evidence/--output/--previous-review`指定目录生成，详见[改孔专题](../../../docs/references/hat-simulation-tools-20261029/cap-vias-20261031/research.md)。这些一次性修复脚本不可在其他基线上盲跑。

TTL阶段：add_ttl_local_bypass.py建立原理图/PCB候选；finish_ttl_local_bypass.py和route_ttl_bottom_bypass.py是未采用方案，不能当现行回放脚本。最终route_ttl_plane_bypass.py采用C329/C330同面VCC线及各自地孔；verify_ttl_local_bypass.py核所有原铜/焊盘/连接保持、地孔与开窗间距。render_ttl_bypass.py生成已检查图像。add_board_identity.py随后只加板名/版本丝印，初次FID3冲突已改正；write_ttl_review_evidence.py生成增量Deep Review与手册证据。均有基线和重复执行护栏，不盲重跑，见[最终复审](../../../docs/references/hat-simulation-tools-20261029/board-marking-20261031/research.md)。

制造文字阶段（历史c6c09b33版）：collect_fabrication_constraints.py归档官方文档；enforce_manufacturing_text.py等修文字并建立C309图形变体，verify_manufacturing_text.py验证内置限制。自定义文字尝试受到无效DRU前置内容影响，不用于断言该功能失效。audit_fabrication_holes.py采用明确记录的保守项目筛查阈值，非完整DFM。render_assembly_views.py仅在显示副本移开TP803标签。replace_codec_microvia.py的局部改线未采用，不提升失败副本。

现行qualify_codec_pth.py/verify_codec_pth.py已用限定小机械孔工艺替代唯一微孔，并验证规则范围/尺寸反例。restore_npth_clearance.py与retire_prototype_drc_rules.py收敛孔铜距和zone作用范围。audit_hole_copper_clearance.py核163孔×4层异网铜，audit_codec_drills.py逐孔核PTH/NPTH与CAM坐标；工艺CSV保留板坐标并另列CAM名义列。checkpoint默认拆PTH/NPTH，所有构建保留基线护栏，现行见[最终规则复审](../../../docs/references/hat-simulation-tools-20261029/npth-clearance-20261031/research.md)。

电源核对阶段：analyze_buck_compensation.py以a65f2ad8…为读入基线，独立计算/仿真图27外部理想网络；calculate_hat_power_envelope.py生成带假设的阶跃与输入预算，均不输出真实环路或额定通过。plot_compensation_check.py用常规Python/matplotlib画模型图。label_hat_power_input.py与space_hat_power_labels.py只改J301两条文字，有基线护栏；现行电气适用性另由analysis-applicability.json核对，不能对其它源版盲重跑。详见[电源研究](../../../docs/references/hat-simulation-tools-20261029/power-acceptance-20261031/research.md)。
