export function normalizeFrame(raw) {
  return {
    ...raw,
    command: Array.isArray(raw.command) ? { vx_m_s: raw.command[0], vy_m_s: raw.command[1], yaw_rad_s: raw.command[2] } : raw.command,
    actual: { ...raw.actual, vx_m_s: raw.actual?.vx_m_s ?? raw.actual?.velocity_m_s?.[0], vy_m_s: raw.actual?.vy_m_s ?? raw.actual?.velocity_m_s?.[1], yaw_rad_s: raw.actual?.yaw_rad_s ?? raw.actual?.yaw_rate_rad_s },
    attitude_rad: raw.attitude_rad || { roll: raw.attitude?.roll_rad, pitch: raw.attitude?.pitch_rad, yaw: raw.attitude?.yaw_rad },
  };
}

export function mergeReplayFrames(existing, incoming, replayId, currentGeneration = -1, incomingGeneration = -1) {
  const valid = incoming.filter(frame => (!frame.replay_id || frame.replay_id === replayId) && Number.isFinite(frame.seq));
  const generation = Math.max(currentGeneration, incomingGeneration, ...valid.map(frame => frame.generation ?? 0));
  const frames = new Map();
  for (const frame of [...existing, ...valid]) {
    if ((frame.generation ?? 0) === generation) frames.set(frame.seq, frame);
  }
  return { generation, frames: [...frames.values()].sort((left, right) => left.seq - right.seq).slice(-2500) };
}
