# Rev B.0 TTL方向控制候选

采用40P pin11/GPIO3_A1驱动`DXL_DIR`：高使能U801发射、关闭U802接收；低关闭发射、打开接收。R401下拉保证无软件时默认接收。此板不是kissqy的PNP自动方向方案。

`duck-hat-revb-ttl.dts`把DIR交给归档Radxa内核6.1.84-10-rk2410-nocsf的8250 em485方向控制：UART2、M0针组、`rs485-de-gpios`，默认启用半双工；应用仍读写UART，无需用户态逐包翻GPIO。此处“RS485”是内核方向控制接口名，板上电气仍为3.3V单线TTL，不是差分RS485。

**该厂商驱动极性特殊，不能照搬到其它内核。** 源码`e6d12a77c8bc0ea6decbd3e4604ec131d4032c30`的`serial8250_em485_start_tx`在RTS_ON_SEND清零时写GPIO=1；stop在RTS_AFTER_SEND置位时写GPIO=0。因此本overlay使用`rs485-rts-active-low`配GPIO_ACTIVE_HIGH，物理效果是发高收低。默认上游同名属性的解释不可替代该源码；运行前必须核实际内核与驱动一致。

驱动在移位寄存器仍忙时安排一个frame_time＋10µs的延后回切；它不是用户态`write()`返回即回切。目标设备DMA、回复延迟和实际波形尚未验收。若现有软件重新配置RS485标志，必须检查不覆盖该极性。

当前仅离线编译、合并两种ZERO 3W基础DTB并核针组/DE属性；未加载到运行中的Radxa，未发串口、未驱动舵机。部署还需核UART控制台占用、系统实际内核、GPIO3_A1无冲突和本板线束针序。

来源：`docs/references/扩展板乙版降本/sources/exact-drivers__tty__serial__8250__8250_dw.c`（599起）、`8250_port.c`（1456/1650及`__stop_tx`）、`serial_core.c`（3494起），均为上述固定提交；离线结果见`ttl-offline-audit.json`。
