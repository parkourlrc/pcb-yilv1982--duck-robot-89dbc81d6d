"""必要核对：同动作物理一致、碰撞盒净空、部分reset隔离及奖励有限性。"""
import argparse
import json
import os
from pathlib import Path
import sys
os.environ.setdefault("MUJOCO_GL", "egl")


def main(a):
    import numpy as np
    import torch
    import mujoco
    from mjlab.envs import ManagerBasedRlEnv
    torch.set_num_threads(1)
    torch.manual_seed(42)
    sys.path.insert(0,str(a.root/"training"))
    from mjlab_duck.locomotion_cfg import locomotion_env_cfg
    cfg=locomotion_env_cfg(4,evaluation=True,seed=42)
    env=ManagerBasedRlEnv(cfg,device="cuda:0")
    traces=[]
    output={"root":str(a.root),"physics_steps":1200,"transitions":480,"ppo_updates":0}
    try:
        with torch.inference_mode():
            env.reset(seed=42)
            env.command_manager.get_term("velocity").set_fixed_schedule([(23.,.06,0.)])
            model=env.sim.mj_model
            data=mujoco.MjData(model)
            cpu_error=0.
            for i in range(120):
                action=.025*torch.sin(torch.arange(14,device="cuda:0")[None,:]+i*.07)
                obs,r,done,trunc,extras=env.step(action.expand(4,14))
                assert torch.isfinite(r).all() and torch.isfinite(obs["actor"]).all()
                traces.append(env.sim.data.qpos[:].cpu().numpy().copy())
                if a.gait and i%20==0:
                    feet=env._gait_geometry[0]
                    for world in range(4):
                        data.qpos[:]=traces[-1][world]
                        mujoco.mj_forward(model,data)
                        height=data.geom_xpos[feet,2]-(np.abs(data.geom_xmat[feet].reshape(2,3,3)[:,2])*model.geom_size[feet]).sum(-1)
                        cpu_error=max(cpu_error,float(np.abs(height-env.locomotion.gait_height[world].cpu().numpy()).max()))
                if i==60:
                    state=env.locomotion
                    fields=[k for k in vars(state) if k.startswith("gait_")] if a.gait else []
                    other={k:getattr(state,k)[1:].clone() for k in fields}
                    env.command_manager.get_term("velocity").set_fixed_schedule([(23.,.06,0.)],torch.tensor([0],device="cuda:0"))
                    for k in fields:
                        assert torch.equal(getattr(state,k)[1:],other[k]), k
                        assert not bool(getattr(state,k)[0].any()), k
            if a.gait:
                assert cpu_error < 2e-6, cpu_error
                from experiments.amplitude.gait import take_log
                output.update(geometry_cpu_max_error_m=cpu_error,partial_reset_isolated=True,gait=take_log(env))
    finally:
        env.close()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(a.output.with_suffix(".npz"),qpos=np.stack(traces))
    a.output.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps(output),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--gait",action="store_true")
    main(p.parse_args())
