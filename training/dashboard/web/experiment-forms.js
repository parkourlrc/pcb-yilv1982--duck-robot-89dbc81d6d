export function readPath(value, path) {
  return path.split('.').reduce((current, key) => current?.[key], value);
}

export function writePath(value, path, next) {
  const result = structuredClone(value || {});
  const keys = path.split('.');
  let target = result;
  for (const key of keys.slice(0, -1)) {
    target[key] ??= {};
    target = target[key];
  }
  target[keys.at(-1)] = next;
  return result;
}

export function mergeConfig(base, overrides) {
  const result = structuredClone(base || {});
  for (const [key, value] of Object.entries(overrides || {})) {
    result[key] = value && typeof value === 'object' && !Array.isArray(value)
      ? mergeConfig(result[key], value) : structuredClone(value);
  }
  return result;
}

export function configurationChanges(before, after, prefix = '') {
  const result = [];
  for (const key of new Set([...Object.keys(before || {}), ...Object.keys(after || {})])) {
    const path = prefix ? `${prefix}.${key}` : key;
    const previous = before?.[key], current = after?.[key];
    if (JSON.stringify(previous) === JSON.stringify(current)) continue;
    if (previous && current && typeof previous === 'object' && typeof current === 'object' && !Array.isArray(previous) && !Array.isArray(current)) {
      result.push(...configurationChanges(previous, current, path));
    } else result.push({ path, before: previous, after: current });
  }
  return result;
}

export function finiteConfiguration(value) {
  if (typeof value === 'number') return Number.isFinite(value);
  if (Array.isArray(value)) return value.every(finiteConfiguration);
  if (value && typeof value === 'object') return Object.values(value).every(finiteConfiguration);
  return true;
}

export function rewardFields(catalog) {
  const fields = (catalog?.fields || []).filter(field => field.key.startsWith('reward_config.') && !field.locked);
  return fields.filter(field => !/stage_overrides|schedule|schema/.test(field.key));
}

export function taskConfiguration(catalog, task, draft) {
  if (draft) return structuredClone(draft.parameters || {});
  const defaults = task?.default_execution?.parameters || task?.default_execution || {};
  return task?.runtime_version === catalog?.runtime_version ? mergeConfig(catalog.defaults, defaults) : structuredClone(defaults);
}

export function taskFields(catalog, task, parameters) {
  const fields = (catalog?.fields || []).filter(field => !field.locked);
  if (task?.runtime_version === catalog?.runtime_version && !task?.legacy_adapter) return fields;
  const editable = task?.editable_execution || [];
  return fields.filter(field => editable.includes(field.key) && readPath(parameters, field.key) !== undefined);
}
