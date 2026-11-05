# 保留In1的LRCK单网改线尝试（未采用）

2026-10-31，本机文件分析。源PCB为fda50c8019c3ab68c7c54228fc09fb36dd028e35b43afe26a7dc0f6c090b0771。在完整副本只移除4段In1 LRCK线，保持两端、过孔及所有其他铜；以0.15mm线宽、0.025mm网格，要求除via端0.6mm/排母端1.15mm范围外均有F.Cu地铜。

搜索3420个状态后没有路径，route-failure.json及search-failure-I2S_LRCK.json保留原始结果。候选已标rejected_unrouted_not_for_use，主工程不受影响。该结果不代表板面积不足或物理无解。

后续改为识别局部未填地铜及具体障碍，已通过[单段音频线绕行加地via](../i2s-reference-stitch-20261031/research.md)恢复部分参考地铜。此目录只作失败证据，勿将其未连通候选用于导出或制造。
