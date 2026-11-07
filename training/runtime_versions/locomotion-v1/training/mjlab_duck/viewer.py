"""mjlab 1.3 回放界面的本项目扩展，不修改安装包。"""

from __future__ import annotations

from collections import Counter, deque
from contextlib import nullcontext
from concurrent.futures import Future
import html
import math
import threading
import time

import mujoco
import numpy as np
from mjlab.viewer import NativeMujocoViewer, ViserPlayViewer
from mjlab.viewer.viser.viewer import UpdateReason


class PlaybackMetrics:
    """有界的后端计时；不把状态同步率称作浏览器 FPS。"""

    def __init__(self, metadata: dict):
        self.metadata = metadata
        self.lock = threading.Lock()
        self.counts = Counter()
        self.samples = {name: deque(maxlen=8192) for name in (
            "control_host_ms", "simulation_lock_wait_ms", "scene_update_ms",
            "scene_completion_interval_ms",
        )}
        self.started = self.finished = self.accounted = None
        self.paused = False
        self.active_seconds = self.paused_seconds = 0.0
        self.last_scene_completion = None
        self.scene_completion_times = deque(maxlen=1024)
        self.error = None

    def begin(self):
        self.started = self.accounted = time.perf_counter()

    def account(self, paused: bool):
        if self.started is None or self.finished is not None:
            return
        now = time.perf_counter()
        elapsed = now - self.accounted
        if self.paused:
            self.paused_seconds += elapsed
        else:
            self.active_seconds += elapsed
        self.accounted, self.paused = now, paused

    def increment(self, name: str, amount: int = 1):
        with self.lock:
            self.counts[name] += amount

    def scene_completed(self, elapsed_ms: float):
        now = time.perf_counter()
        with self.lock:
            self.counts["scene_completed"] += 1
            self.samples["scene_update_ms"].append(elapsed_ms)
            if self.last_scene_completion is not None:
                self.samples["scene_completion_interval_ms"].append(
                    1000.0 * (now - self.last_scene_completion)
                )
            self.last_scene_completion = now
            self.scene_completion_times.append(now)

    def scene_hz(self) -> float:
        cutoff = time.perf_counter() - 1.0
        with self.lock:
            recent = [stamp for stamp in self.scene_completion_times if stamp >= cutoff]
        return (len(recent) - 1) / (recent[-1] - recent[0]) if len(recent) > 1 else 0.0

    def finish(self, paused: bool):
        if self.finished is None:
            self.account(paused)
            self.finished = time.perf_counter()

    def report(self, step_dt: float) -> dict:
        now = self.finished or time.perf_counter()
        elapsed = max(0.0, now - self.started) if self.started is not None else 0.0
        with self.lock:
            counts = dict(self.counts)
            summaries = {}
            for name, values in self.samples.items():
                data = list(values)
                summaries[name] = {
                    "retained_samples": len(data),
                    "p50": float(np.percentile(data, 50)) if data else None,
                    "p95": float(np.percentile(data, 95)) if data else None,
                    "max": max(data) if data else None,
                }
        active = self.active_seconds
        steps = counts.get("running_control_steps", 0)
        return {
            "schema_version": 1,
            **self.metadata,
            "wall_seconds": elapsed,
            "active_wall_seconds": active,
            "paused_wall_seconds": self.paused_seconds,
            "control_step_seconds": step_dt,
            "running_simulation_seconds": steps * step_dt,
            "actual_realtime_ratio": steps * step_dt / active if active > 0 else None,
            "control_hz": steps / active if active > 0 else None,
            "scene_completed_hz_including_pauses": counts.get("scene_completed", 0) / elapsed if elapsed else None,
            "scene_task_limit": 1,
            "max_scene_tasks_in_flight": counts.get("scene_inflight_max", 0),
            "counts": counts,
            "timings": summaries,
            "browser_fps": None,
            "timing_note": "后端墙钟计时；control_host_ms 含推理/步进主机耗时，不是独立 GPU kernel 时间。分位数保留最近 8192 点。",
            "error": self.error,
        }


class _MeasuredViewer:
    def __init__(self, *args, metrics: PlaybackMetrics, duration=None, **kwargs):
        self.metrics = metrics
        self.duration = duration
        self._playback_closed = False
        super().__init__(*args, **kwargs)

    def _begin_playback(self):
        self.metrics.begin()

    def is_running(self):
        if self.duration is not None and self.metrics.started is not None:
            if time.perf_counter() - self.metrics.started >= self.duration:
                return False
        return super().is_running()

    def tick(self):
        self.metrics.account(self._is_paused)
        result = super().tick()
        self.metrics.account(self._is_paused)
        if self._was_capped:
            self.metrics.increment("budget_capped_ticks")
        return result

    def _execute_step(self):
        started = time.perf_counter()
        lock = getattr(self, "_sim_lock", None)
        with lock if lock is not None else nullcontext():
            acquired = time.perf_counter()
            result = super()._execute_step()
        finished = time.perf_counter()
        if not result:
            raise RuntimeError(self._last_error or "MuJoCo 控制步执行失败")
        with self.metrics.lock:
            self.metrics.counts["single_control_steps" if self._is_paused else "running_control_steps"] += 1
            self.metrics.samples["simulation_lock_wait_ms"].append((acquired - started) * 1000)
            self.metrics.samples["control_host_ms"].append((finished - acquired) * 1000)
        return result

    def reset_environment(self):
        # Viser 父类本身持锁；不要在这里再次获取非重入锁。
        super().reset_environment()
        self.metrics.increment("resets")
        self._time_until_next_render = 0.0

    def pause(self):
        self.metrics.account(self._is_paused)
        super().pause()
        self.metrics.account(True)
        self.metrics.increment("pauses")

    def resume(self):
        self.metrics.account(self._is_paused)
        super().resume()
        self._time_until_next_render = 0.0
        self._stats_last_time = time.perf_counter()
        self._stats_steps = self._stats_frames = 0
        self.metrics.account(False)
        self.metrics.increment("resumes")


class DuckNativeViewer(_MeasuredViewer, NativeMujocoViewer):
    def setup(self):
        super().setup()
        self._begin_playback()

    def sync_env_to_viewer(self):
        super().sync_env_to_viewer()
        self.metrics.increment("native_sync_calls")

    def _set_status_overlay(self, viewer):
        status = self.get_status()
        # MuJoCo 原生字体不可靠地支持中文；这里使用明确的英文技术标签。
        viewer.set_texts((
            mujoco.mjtFontScale.mjFONTSCALE_150.value,
            mujoco.mjtGridPos.mjGRID_TOPLEFT.value,
            "State\nTarget speed\nActual speed\nState sync\nRender FPS",
            f"{'PAUSED' if status.paused else 'RUNNING'}\n"
            f"{status.target_realtime:.2f}x\n"
            f"{0.0 if status.paused else status.actual_realtime:.2f}x\n"
            f"{status.smoothed_fps:.1f} Hz\nNot measured",
        ))

    def close(self):
        if self._playback_closed:
            return
        self._playback_closed = True
        self.metrics.finish(self._is_paused)
        super().close()


class DuckViserViewer(_MeasuredViewer, ViserPlayViewer):
    """一个显示任务在途，仿真读写共用同一把锁。"""

    def __init__(self, *args, simple=False, **kwargs):
        self.simple = simple
        self._scene_future: Future | None = None
        self._last_panel_time = 0.0
        self._camera_preset = "斜前"
        self._root_position = np.array([0.0, 0.0, 0.12])
        super().__init__(*args, **kwargs)

    def setup(self):
        gui = self._server.gui
        gui.configure_theme(dark_mode=True, show_logo=False, show_share_button=False,
                            brand_color=(65, 188, 175))
        gui.main_panel.dock_right()
        self._make_common_controls()
        with gui.add_folder("高级诊断 · mjlab", order=20, expand_by_default=False):
            super().setup()
        def initialize_visibility():
            self._scene.geom_groups_visible[:] = [True, False, not self.simple, self.simple, False, False]
            self._scene.site_groups_visible[:] = [False] * 6
            self._scene.debug_visualization_enabled = False
            # 与 mjviser 原生 group 回调一致：刷新缓存不会同步 mesh handle 的 visible。
            self._scene._sync_visibilities()

        with self._sim_lock, self._server.atomic():
            self._scene._apply_visualization_change(initialize_visibility)
        self._server.on_client_connect(
            lambda client: self.request_action("CUSTOM", {"type": "camera", "client": client.client_id})
        )
        self._begin_playback()
        self._update_panel(force=True)

    def _make_common_controls(self):
        gui = self._server.gui
        gui.add_html(
            '<div style="padding:4px 0 8px"><div style="color:#65d6c6;font-size:11px;letter-spacing:2px">DUCK / SIMULATION</div>'
            '<div style="font-size:23px;font-weight:650;margin-top:5px">MuJoCo 运动工作台</div>'
            '<div style="opacity:.65;font-size:12px;margin-top:5px">拖动旋转视角 · 滚轮缩放 · 仅仿真</div></div>', order=-20
        )
        with gui.add_folder("播放与速度", order=-10):
            self._quick_pause = gui.add_button("暂停", icon=None)
            self._quick_pause.on_click(lambda _: self.request_toggle_pause())
            buttons = gui.add_button_group("操作", ("单步", "重置", "退出"))

            @buttons.on_click
            def controls(event):
                if event.target.value == "单步":
                    self.request_action("CUSTOM", {"type": "single_step"})
                elif event.target.value == "重置":
                    self.request_reset()
                else:
                    self.request_action("CUSTOM", {"type": "exit"})

            speed = gui.add_button_group("播放倍率", ("0.5×", "1×", "2×"))
            speed.on_click(lambda event: self.request_action(
                "CUSTOM", {"type": "speed", "value": float(event.target.value[:-1])}
            ))
            term = self.env.unwrapped.command_manager.get_term("velocity")
            self._velocity = gui.add_slider("前后速度 (m/s)", min=-0.2, max=0.2,
                                            step=0.01, initial_value=term.manual_vx)
            self._velocity.on_update(lambda event: self.request_action(
                "CUSTOM", {"type": "velocity", "value": float(event.target.value)}
            ))
            zero = gui.add_button("速度归零")
            zero.on_click(lambda _: self.request_action("CUSTOM", {"type": "velocity", "value": 0.0}))
        with gui.add_folder("视角与模型", order=-5):
            views = gui.add_button_group("观察方向", ("斜前", "正面", "侧面", "俯视"))
            views.on_click(lambda event: self.request_action(
                "CUSTOM", {"type": "camera", "preset": event.target.value}
            ))
            self._follow = gui.add_checkbox("相机跟随机器人", initial_value=True)
            self._follow.on_update(lambda event: self.request_action(
                "CUSTOM", {"type": "follow", "value": bool(event.target.value)}
            ))
            self._collision = gui.add_checkbox("仅显示碰撞体", initial_value=self.simple,
                                               disabled=self.simple)
            self._collision.on_update(lambda event: self.request_action(
                "CUSTOM", {"type": "collision", "value": bool(event.target.value)}
            ))
        with gui.add_folder("实时状态", order=0):
            self._quick_status = gui.add_html("准备仿真…")
            self._pose_display = gui.add_html("")

    def _handle_custom_action(self, action, payload):
        if not isinstance(payload, dict):
            return super()._handle_custom_action(action, payload)
        kind = payload.get("type")
        if kind == "velocity":
            with self._sim_lock:
                self.env.unwrapped.command_manager.get_term("velocity").set_velocity(payload["value"])
            if self._velocity.value != payload["value"]:
                self._velocity.value = payload["value"]
            self.metrics.increment("velocity_changes")
        elif kind == "speed":
            self._speed_index = self.SPEED_MULTIPLIERS.index(payload["value"])
            self._time_multiplier = payload["value"]
            self._sim_budget = 0.0
            self._last_tick_time = time.perf_counter()
            self.metrics.increment("speed_changes")
        elif kind == "single_step":
            if not self._is_paused:
                self.pause()
            self._single_step()
        elif kind == "camera":
            self._camera_preset = payload.get("preset", self._camera_preset)
            self._apply_camera(payload.get("client"))
        elif kind == "follow":
            with self._sim_lock:
                self._scene.camera_tracking_enabled = payload["value"]
                self._scene.request_update()
            self._apply_camera()
        elif kind == "collision":
            def toggle_collision_visibility():
                self._scene.geom_groups_visible[2] = not payload["value"]
                self._scene.geom_groups_visible[3] = payload["value"]
                self._scene._sync_visibilities()

            with self._sim_lock, self._server.atomic():
                self._scene._apply_visualization_change(toggle_collision_visibility)
        elif kind == "exit":
            self._interrupted = True
        else:
            return super()._handle_custom_action(action, payload)
        self._pending_update_reasons.add(UpdateReason.ACTION)
        return True

    def _apply_camera(self, client_id=None):
        offsets = {"斜前": (0.43, -0.43, 0.30), "正面": (0.62, 0, 0.12),
                   "侧面": (0, -0.62, 0.12), "俯视": (0, 0.001, 0.68)}
        target = np.zeros(3) if self._scene.camera_tracking_enabled else self._root_position.copy()
        for cid, client in self._server.get_clients().items():
            if client_id is None or client_id == cid:
                client.camera.position = target + np.array(offsets[self._camera_preset])
                client.camera.look_at = target
                client.camera.up_direction = (0, 1, 0) if self._camera_preset == "俯视" else (0, 0, 1)
                client.camera.fov = math.radians(42)

    def _should_submit_scene_update(self, counter, paused, has_pending_updates):
        del counter
        ready = self._scene_future is None or self._scene_future.done()
        return ready and (not paused or has_pending_updates)

    def _submit_scene_update_if_needed(self, sim, has_pending_updates):
        if self._scene_future is not None:
            if not self._scene_future.done():
                if not self._is_paused or has_pending_updates:
                    self.metrics.increment("scene_skipped_busy")
                return
            self._scene_future.result()  # 传播后台异常，不留下失效但仍显示正常的页面。
            self._scene_future = None
        if self._is_paused and not has_pending_updates:
            return

        def update_scene():
            started = time.perf_counter()
            try:
                with self._sim_lock:
                    with self._server.atomic():
                        self._scene.update(sim.data)
                        self._server.flush()
                self.metrics.scene_completed((time.perf_counter() - started) * 1000)
            finally:
                with self.metrics.lock:
                    self.metrics.counts["scene_inflight_current"] -= 1

        with self.metrics.lock:
            self.metrics.counts["scene_inflight_current"] += 1
            self.metrics.counts["scene_inflight_max"] = max(
                self.metrics.counts["scene_inflight_max"],
                self.metrics.counts["scene_inflight_current"],
            )
        try:
            self._scene_future = self._threadpool.submit(update_scene)
        except BaseException:
            with self.metrics.lock:
                self.metrics.counts["scene_inflight_current"] -= 1
            raise
        self.metrics.increment("scene_submitted")
        self._pending_update_reasons.clear()
        self._scene.needs_update = False

    def sync_env_to_viewer(self):
        super().sync_env_to_viewer()
        self.metrics.increment("viewer_sync_ticks")
        self._update_panel()

    def _update_status_display(self):
        if hasattr(self, "_status_html"):
            self._status_html.content = (
                f"状态提交 {self.metrics.scene_hz():.1f} Hz · 界面调度 {self._fps:.1f} Hz · "
                f"实际 {0.0 if self._is_paused else self.actual_realtime:.2f}× / "
                f"目标 {self.target_realtime:g}× · 浏览器 FPS 未测量"
            )

    def _update_panel(self, force=False):
        now = time.perf_counter()
        if not force and now - self._last_panel_time < 0.25:
            return
        self._last_panel_time = now
        with self._sim_lock:
            robot = self.env.unwrapped.scene["robot"]
            pos = robot.data.root_link_pos_w[0].detach().cpu().numpy()
            quat = robot.data.root_link_quat_w[0].detach().cpu().numpy()
            vx = float(robot.data.root_link_lin_vel_b[0, 0].item())
        self._root_position = pos
        w, x, y, z = quat
        roll = math.atan2(2 * (w*x + y*z), 1 - 2 * (x*x + y*y))
        pitch = math.asin(float(np.clip(2 * (w*y - z*x), -1, 1)))
        yaw = math.atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))
        self._quick_pause.label = "继续播放" if self._is_paused else "暂停"
        state = "已暂停" if self._is_paused else "播放中"
        error = f'<div style="color:#ff8888">{html.escape(self._last_error)}</div>' if self._last_error else ""
        self._quick_status.content = (
            f'<div style="font-size:16px;font-weight:600">{state} · {self.target_realtime:g}×</div>'
            f'<div style="opacity:.75;margin-top:6px">实际 {0.0 if self._is_paused else self.actual_realtime:.2f}×'
            f' · 状态提交 {self.metrics.scene_hz():.1f} Hz<br>前向实速 {vx:+.3f} m/s</div>{error}'
        )
        self._pose_display.content = (
            '<div style="font-family:monospace;font-size:12px;line-height:1.8">'
            f'世界 XYZ / m　{pos[0]:+.3f}　{pos[1]:+.3f}　{pos[2]:+.3f}<br>'
            f'横滚 / 俯仰 / 偏航　{math.degrees(roll):+.1f}°　{math.degrees(pitch):+.1f}°　{math.degrees(yaw):+.1f}°'
            '</div>'
        )

    def close(self):
        if self._playback_closed:
            return
        self._playback_closed = True
        self.metrics.finish(self._is_paused)
        try:
            if self._scene_future is not None:
                self._scene_future.result()
        finally:
            if hasattr(self, "_threadpool"):
                super().close()
