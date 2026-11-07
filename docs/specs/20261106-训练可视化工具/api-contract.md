# 训练工具 API 合同 v1

2026-11-06，用户已批准实施方案，编码中。所有单位采用 SI，缺测为 null，UTC 时间；服务不导入 torch。前端与后端按本文件联调。

- `GET /api/session` → `{csrf_token,schema_version:1}`；写请求带 `X-CSRF-Token`。同源 cookie 会话；WS 使用同一 cookie 并检查 Origin。
- `GET /api/tasks`、`/api/runs`、`/api/resources`、`/api/replays` → `{items:[...]}`。
- Task：`task_id,task_version,title,description,default_execution,editable_execution,constraints,availability,evaluation_suites,display_model_version`。
- `POST /api/runs/validate` 输入 `{task_id,task_version,execution:{mode:"local"|"single_spark"|"dual_spark",node_ids:[]},parameters:{num_envs,num_steps_per_env,max_updates,save_interval,eval_interval,seed}}`；返回 `{valid,validation_id,config_hash,resolved_config,execution,allocation,budget,errors,warnings}`。
- `POST /api/runs` 输入 `{request_id,validation_id,config_hash,name}`，返回 Run。`POST /api/runs/{id}/stop` 输入 `{request_id}`；`POST /api/runs/{id}/resume` 输入 `{request_id,checkpoint_id}`，返回新 Run。
- Run：`run_id,experiment_id,parent_run_id,parent_checkpoint_id,task_id,task_version,name,managed,read_only,state,connection,stage,model_iteration,budget:{consumed_transitions,remaining_transitions,max_transitions,transitions_per_update},execution,config,created_utc,elapsed_s,eta_s,latest_checkpoint_id,capabilities:{stop,resume},failure`。能力为 `{allowed,reasons:[]}`；状态与连接分开。
- `GET /api/runs/{id}/metrics?axis=iteration&max_points=1000` → `{series:[{key,label,unit,scope,availability,points:[{iteration,transitions,elapsed_s,time_utc,value,checkpoint_id?}]}],warnings:[]}`。axis支持iteration/transitions/elapsed_s；查询keys逗号分隔。不存在的时间轴保持null。稀疏评估不插值。
- `GET /api/runs/{id}/events?after=0&limit=200` → `{items:[{seq,time_utc,type,level,message,data}],next_cursor}`。
- `GET /api/runs/{id}/checkpoints` → `{items:[{checkpoint_id,run_id,model_iteration,stage,world_size,integrity,cache_state,replayable,resumable,reasons,evaluations,rank_files}]}`。
- Resource：`node_id,label,execution_kind,connection:{state,last_seen_utc},active_run_ids,active_replay_ids,samples:[{sample_utc,scope,metrics:{cpu_percent:{value,unit,status},...}}]`。指标含 memory_used_bytes/memory_available_bytes/gpu_util_percent/gpu_memory_used_bytes/temperature_c/power_w/disk_read_bytes_s/disk_write_bytes_s/network_rx_bytes_s/network_tx_bytes_s，值未取得明确unsupported/error/stale。
- 样本另含`received_utc`（控制服务主机接收时间）；远端sample_utc不用于跨主机时钟的新鲜度比较。local另含`wsl:{connection,sample,samples}`，scope为wsl_virtual_machine；每个samples最多900点并持久写独立JSONL。processes为`{pid,kind:"training"|"replay",memory_rss_bytes,gpu_memory_status}`，不与宿主总量累加。GPU查询超时/失败状态为error并含reason，字段N/A或工具缺失为unsupported。
- `POST /api/resources/{node_id}/probe` 返回资源最新状态。
- `POST /api/replays` 输入 `{request_id,checkpoint_id,scenario_id,seed}`；返回 `{replay_id,state,checkpoint_id,node_id,scenario_id,seed,speed,generation,actual_realtime_factor,error}`。
- `GET /api/replays/{id}` 返回会话；`POST /api/replays/{id}/control` 输入 `{action:"pause"|"play"|"reset"|"set_speed",speed?}`；`DELETE /api/replays/{id}` 幂等释放。
- `GET /api/replays/{id}/frames?after_seq=0&limit=2500` 返回`{items,generation}`；只取当前generation最近最多2500帧、seq严格大于after_seq。关闭会话也可读；后端以文件offset缓存增量读取，保留未写完行待下次读取。刷新、WS重连和reset后用于曲线补齐，不重启推理。
- `/ws` 收 `{type:"subscribe",subscriptions:[{topic:"run"|"resource"|"replay",id,after_cursor?}]}`；送 `{type:"snapshot"|"event"|"frame",topic,id,seq,cursor,time_utc,data}`。run snapshot为Run；resource snapshot为Resource；replay frame为worker原始帧，保证replay_id/seq/generation。前端通过REST拉初始曲线，run事件后增量刷新；事件游标可重接，帧只保留最新。
- Studio静态原件：`/studio-model/model/model.json`、`/studio-model/model/meshes.bin`、`/studio-model/duck3d.js`、`/studio-model/model-worker.js`；前端适配模块与vendor放`/web/`。
- 错误 `{error:{code,message,details}}`，HTTP 400/404/409/422/503。禁止客户端传任意命令或源文件路径。

旧首轮 `legacy-run-001` 只读导入，预算耗尽，100/1000 checkpoint仅rank0本地缓存可推理，缺rank1不能标完整恢复；运行中的配置、源码及模型冻结。停机不杀其他作业。控制服务停掉不结束训练。
