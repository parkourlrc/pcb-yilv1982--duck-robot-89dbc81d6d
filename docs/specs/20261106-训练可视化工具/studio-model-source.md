# 回放外观来源：当前主控 Studio

- 日期：2026-11-06（Asia/Shanghai）。
- 状态：已按部署固定提交恢复Studio模型与加载源码，见[本地快照](../../../software/studio/model-source-2026103101/README.md)。当前板侧未重新在线比对；不阻塞依据部署来源开展回放设计。
- 关联：[需求](spec.md)、[文档核对](document-confirmation.md)。

## 1. 当前决定

[用户确认] 用户明确“就用现在主核studio里用的那个模型”，本任务据上下文按“当前主控Studio的3D显示模型”执行。它是回放外观的指定来源，替代此前要求定位实际打印文件的条件；不再要求用户提供打印包，也不再继续以kissqy/microduck-replica的打印CAD选型作为本任务前置。

复用的是Studio显示几何、材质、装配层级及相关挂接信息，不是Studio中的ONNX策略。回放仍由所选checkpoint和任务物理产生运动；不接入主控实时姿态作为训练回放，不改训练碰撞、质量/惯量或策略接口。

## 2. 现有来源证据

### 后续查证与更正（2026-11-06）

用户指出部署必有工程来源。此前仅检查索引目录，把主控不在线当作无法继续取得模型的理由不充分，现已更正。

- [部署记录核验] [robotd-recovery来源](../../../software/robotd-recovery/SOURCE.md)和[source_inputs.py](../../../software/robotd-recovery/source_inputs.py)记录完整运行包为training/logs/b-feetech-walk-20261024/controller-preparation-20261031/studio-runtime.tar.gz，SHA-256为fd4753ba11619607d36852f35080c62dc845fdffd005ef37aac74f61157b55ef。当前工作区未找到该缓存包，不等于没有源码来源。
- [文件核验] 已从固定部署提交3952471a8394c8b720817d2160ffd95ce5a54456的software/studio/恢复六个原件。Git blob哈希均与GitHub树匹配，SHA-256见[清单](../../../software/studio/model-source-2026103101/source-manifest.json)。这是从固定源码恢复，不能称为当前主控新采集。
- [源码核验] duck3d.js明确模型与servo-web共源，load读取model.json和meshes.bin，setJoints按命名关节接收弧度，worker解码网格及法线。
- [文件核验] 本地servo-web的meshes.bin与部署版Studio完全一致，2,856,560字节；JSON语义仅Studio版多两个servo_joint标记：head_yaw与mouth。完整Studio版已归档，不直接使用另一应用JSON替代。
- 模型含16个body、28个mesh；没有将显示资产认定为本机打印CAD。原始NOTICE/LICENSE已保留，代码LICENSE不能替代模型自身许可。

后续以本地固定来源进行方案设计；无需等待主控在线才能取得外观模型。原访问失败记录保留如下。

| 来源 | 已知事实及限制 |
|---|---|
| [Studio部署适配spec](../20261031-studio-commissioning-display/spec.md)“现状” | 2026-10-31记录板侧Studio运行目录为`/home/radxa/studio-dev`；为历史部署事实，不是本次在线核验。 |
| [Studio来源记录](../../../software/robotd-v03/SOURCE.md) | 记录Studio源包`microduck-software-v2026.10.3101`，提交`3952471a8394c8b720817d2160ffd95ce5a54456`。需与当前板侧实际资源比对，不能假定仍逐字相同。 |
| [归档Studio README](../../references/飞特策略模型上机核对/controller-sources-20261031/studio-README.md)“目录”“许可证” | `web/`使用three.js显示3D鸭子；模型来源说明在`web/model/NOTICE.md`。该路径可作为定位入口，网格实际文件名、大小、哈希和加载路由待在线读取。 |
| [现有训练显示来源](../../../training/models/visual/SOURCE.md) | 现有训练精细外观是上游XL330版，尚未与当前Studio资产比对，不能擅自认定同源同版本而直接替代。 |
| [servo-web模型来源](../../../software/servo-web/model/NOTICE.md) | 已与部署版Studio核对：网格一致，JSON有两个新增显示标记；当前主控是否有后续额外修改未在线复核。 |

## 3. 本轮访问结果

- Windows `ssh -o BatchMode=yes -o ConnectTimeout=8 radxa-zero3 ...`：主机名无法解析，未建立连接。
- 依据历史Studio地址，以`radxa@192.168.1.35`只读查询服务工作目录及web资源：TCP 22连接超时，未执行远端命令。超时只说明本次无法连接，不足以判断主控关机、网络变化或SSH状态。
- WSL `ssh -G radxa-zero3`：输出`hostname radxa-zero3`、`user yilv`、`port 22`；未解析到可直接使用的板侧地址，也未建立连接。
- 初步检查时software/studio仅有索引、参考库没有Studio目录；后续沿部署记录找到完整源包定位，并已按固定提交恢复显示资源，见第2节更正。
- 此前GitHub打印模型查询因用户随后指定Studio来源而终止，未形成可用的打印文件/版本结论，也未下载模型。

## 4. 后续处理与验收

来源决定与部署版显示原件恢复已完成，可用于后续方案和适配。主控可访问时再只读比对有无额外模型修改，不以设备离线阻塞设计。原始来源与许可文件已归档，保留模型与代码许可各自的适用边界。

原件已落盘software/studio/model-source-2026103101/，回放接口在修改方案阶段确定。按部署版Studio外观、比例、材质、装配及关节映射适配，多窗口使用同一固定版本；加载失败明确提示，不静默替换MuJoCo简模。

本轮已保存部署固定版本的模型、加载源码与来源清单；未修改板侧文件、服务、机器人状态或训练源码。资产与文档保留工作区，未提交。
