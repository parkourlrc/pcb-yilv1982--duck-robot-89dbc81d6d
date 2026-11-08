"""用物理离地检验批量接触隔离与首次落地历史，不训练策略。"""
import json
from pathlib import Path
import sys
import torch
from mjlab.envs import ManagerBasedRlEnv


def main():
    root=Path(sys.argv[1]); output=Path(sys.argv[2])
    sys.path.insert(0,str(root/"training"))
    from mjlab_duck.locomotion_cfg import locomotion_env_cfg
    torch.set_num_threads(1)
    env=ManagerBasedRlEnv(locomotion_env_cfg(4,evaluation=True,seed=42),device="cuda:0")
    records=[]
    try:
        with torch.inference_mode():
            env.reset(seed=42)
            env.command_manager.get_term("velocity").set_fixed_schedule([(23.,.06,0.)])
            state=env.locomotion
            zero=torch.zeros((4,14),device=env.device)
            env.step(zero)
            assert bool(state.gait_contact.all())
            # 第1环境抬高躯干；其他3环境仍站立。仅检查副本手动改状态。
            z=int(env.scene["robot"].indexing.free_joint_q_adr[0])+2
            env.sim.data.qpos[1,z]+=.15
            # 模拟从未接触过的空中初始化，首次落地不应计有效摆动。
            state.gait_seen[1]=False
            for i in range(40):
                env.step(zero)
                records.append({"step":i,"contact":state.gait_contact.cpu().tolist(),
                    "air":state.gait_air.cpu().tolist(),"swing_reward":state.gait_reward_terms[:,2].cpu().tolist()})
                if i==0:
                    assert not bool(state.gait_contact[1].any())
                    assert bool(state.gait_contact[[0,2,3]].all())
                if bool(state.gait_contact[1].any()):
                    assert float(state.gait_reward_terms[1,2])==0., "spurious first landing"
                    break
            else:
                raise AssertionError("No first landing observed")
    finally:
        env.close()
    output.write_text(json.dumps({"cross_world_contact_isolation":True,"first_spawn_landing_excluded":True,
                                  "ppo_updates":0,"records":records},indent=2)+"\n")
    print(json.dumps({"passed":True,"steps":len(records)}))


if __name__=="__main__":main()
