# 自主HAT Rev B.0：降本开发副本

**2026-11-05 自主HAT线路暂停：** [用户确认] Y10／SMT2611051346已付款，84362651版5片，等待收货。最后合并支付页金额891.79元（含运费5.50）；未另核支付回执或发货状态。停止继续降本、设计修改、订单操作及主动跟进，等待用户明确恢复；首板尚未验收，原750元目标未达成。

**B.0源已用于用户付款订单；软件检查通过不等于实物验收，整项计划未标完成。** 主原理图已移除BMI088及多余扩展，加入AP63205电源、本地12MHz时钟和板载/外接麦克风。当前源SHA256见`checkpoint.json`；原生ERC、DRC、未连接、原理图/PCB一致性均为0；两层、63个SMT在F面、6个THT、3个F面fiducial，所有via孔0.3mm，未发现过孔孔壁进入裸露SMD焊盘。40P全部40个焊盘位置与A.1一致。

`custom_hat_rev_b.kicad_sch`为唯一主图，只引用8个功能页；`review-output/`含同源Gerber、归并BOM、69个拟装件CPL及原理图PDF，均为审查件。`checkpoint.json`绑定当前源和检查；原复制清单`source-manifest.json`只说明A.1来源。旧A.1的audio/imu_tof页面退入`archive-from-a1/`，不在B版主图中。

**当前源与资料：** SHA256为`84362651a5dc57338a24f6b0d7a642267d32f4bc81888ccc2809bb129fc1bcf0`，[新报价包](quote-84362651/README.md)已导出；28个对象移动/旋转，69件/30组保持。CAD焊接面筛查低件最紧3.31mm、高件5.46mm，3/5mm要求及另留0.2mm的筛查均通过；VBATT/GND各1.6mm、5V主干1.0mm指定路径连续性已核。详见[布局和同源验证](../../../docs/references/扩展板乙版降本/layout-spacing/research.md)。

**订单与成本边界：** 重传新Gerber后平台生成Y10，PCB初步33元、待审核未付；SMT流程已打开，据解锁后页面记录，BOM/CPL已上传，待用户继续核对全焊设置和物料匹配，详见[当前询价状态](../../../docs/references/扩展板乙版降本/layout-spacing/y10-quotation-status.md)。旧Y9对应99ecc45d；11-04保存的五片全焊SMT草稿¥1107.71＋PCB初步33元＝¥1140.71、超750目标¥390.71，属于旧源快照。新布局未取得工厂完整报价，不先记作已免贴插费。未提交正式SMT、未付款。旧30组/69位号的订单材料¥266.44含备损/最低用量，目录净量¥238.1055仅作历史比较；仅顶层¥1057.11漏J101，不作全焊价。`quote-99ecc45d/`退为旧Y9追溯，`quote-8af23ba8/`仍因通孔阻焊遗漏停用。

**暂停保留的未验收项（当前不执行）：**全BOM产线/回流工艺准入、母座/线束机械互配、MLCC有效容量与2A级热预算、实机音频/TTL和工厂装配图确认。重新报价已取得，付款不构成首板验收。旧21个＜3mm焊盘的空间问题已通过本次重排处理；名义CAD空间不等于工厂治具/焊锡公差审核。Y701、A1251封装及52个THT阻焊开窗的既有修正保持。见[成本闸门](../../../docs/references/扩展板乙版降本/cost-gate.md)、[订单状态](../../../docs/references/扩展板乙版降本/order-status.json)及[复审](../../../docs/references/扩展板乙版降本/review.md)。

软件候选在`../software/codec/rev_b/`：codec以12MHz产生BCLK/LRCK，CPU从模式，右BTL播放、板载右声道/外接双麦输入；TTL补充归档Radxa厂商内核`rs485-de-gpios`方向控制overlay。音频与TTL两种ZERO 3W基DTB离线合并通过；未部署或实测。

开发脚本不得覆盖已布线主板：`build_rev_b_board.py`发现完整布线即拒绝重新生成；历史路由试验不作为制造入口。

`placement-plan.json`保留最初生成阶段的布局输入；现行坐标以PCB、CPL及已同步的`design-components.json`为准。

目标与授权见[实施Spec](../../../docs/specs/20261104-hat-revb-cost/spec.md)，准入/物料/设计进展见[研究记录](../../../docs/references/扩展板乙版降本/research.md)。不覆盖`rev_a/`或旧Y7/Y8资料。
