# Studio 部署版本的3D显示来源快照

日期：2026-11-06。用途：为第⑤步训练网页提供用户指定的Studio外观来源，尚未接入训练回放。

来源为fanhao375/microduck-replica固定提交3952471a8394c8b720817d2160ffd95ce5a54456的software/studio/，对应本项目[部署来源记录](../../robotd-v03/SOURCE.md)中的发布版。六个原始文件均从该提交重新获取，Git blob哈希与GitHub树匹配；SHA-256、大小和地址见[source-manifest.json](source-manifest.json)。当前板侧未重新在线比对。

- web/model/model.json：16个body、28个mesh的索引、装配层级、材质、局部位姿和关节映射。
- web/model/meshes.bin：2,856,560字节的量化网格。
- web/duck3d.js：原始显示代码，load读取模型，setJoints设置关节弧度。
- web/model-worker.js：原始网格解码及法线处理。
- web/model/NOTICE.md、LICENSE：原始来源及许可文件。代码LICENSE不能覆盖模型自身许可；模型上游许可口径另见[已有来源说明](../../../training/models/visual/SOURCE.md)。

[文件核验] 本地servo-web的meshes.bin与本快照完全同哈希：d2252354ee5a04367aaf82242e08e52491b02ebbf27d48dc2c20350e6714d1a8。JSON语义比较仅Studio版新增两个字段：bodies[8].geoms[1].servo_joint="head_yaw"、bodies[9].geoms[2].servo_joint="mouth"。使用Studio版完整文件，不直接以servo-web的JSON代替。

显示资产含上游外观与补充显示关节；它是用户指定的Studio外观，不等于本机打印CAD或动力学已对齐。按名称映射训练关节，根位姿来自仿真；嘴部额外显示关节不增加训练动作维度。JSON中的质量/重心、ID及默认根位置不覆盖训练物理定义。

这是显示来源存档，不是完整可运行Studio：没有复制其余网页、服务或three.js依赖。没有修改原文件、板侧服务、只读参考库或训练源码。
