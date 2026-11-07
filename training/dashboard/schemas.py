from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Execution(StrictModel):
    mode: Literal['local', 'single_spark', 'dual_spark'] = 'local'
    node_ids: list[str] = Field(default_factory=list)


class ValidationRequest(StrictModel):
    task_id: str
    task_version: str
    execution: Execution = Field(default_factory=Execution)
    parameters: dict[str, StrictInt] = Field(default_factory=dict)


class StartRequest(StrictModel):
    request_id: str = Field(min_length=8, max_length=128)
    validation_id: str
    config_hash: str
    name: str = Field(default='新运行', max_length=120)


class StopRequest(StrictModel):
    request_id: str = Field(min_length=8, max_length=128)


class ResumeRequest(StopRequest):
    checkpoint_id: str


class ReplayRequest(StrictModel):
    request_id: str = Field(min_length=8, max_length=128)
    checkpoint_id: str
    scenario_id: str = 'straight_0.06_101'
    seed: int = 101


class ReplayControl(StrictModel):
    request_id: str | None = None
    action: Literal['pause', 'play', 'reset', 'set_speed']
    speed: float | None = None
