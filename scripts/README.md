# scripts 目录索引

跨域维护、诊断和文档生成脚本。组件专属脚本后续随组件迁移；当前先按用途分组。

| 类别 | 代表脚本 | 说明 |
|---|---|---|
| 图片标注/渲染 | `annotate-*.py`、`render-*.py` | 硬件照片标注、HAT/总线图、市场 HTML |
| 舵机/IMU 诊断 | `feetech-ping.py`、`imu200-*.py`、`imu-*-exp-*.py` | 台架扫描、原始帧与协议诊断 |
| servo-web 补丁/监控 | `servo-web-*.py`、`servo-web-*.patch` | 板侧补丁、总线监控与映射 |
| 训练/回放 | `a-training.sh`、`b-training.sh`、`servo-mujoco-viewer.py` | 历史训练入口与查看器 |
| 服务单元 | `duck-*.service` | 板侧 systemd 单元 |
| 工程/编号 | `inspect-kissqy-hat-bypass-*.py`、`servo-id-*.py` | 工程解析、ID 对齐 |

## 使用边界

- 多数脚本绑定历史路径、串口或板侧环境；复用前核对参数和当前板型。
- 只读参考库不被脚本修改；需要写入时用工作副本。
- `__pycache__/` 为运行缓存，不作为源码。
