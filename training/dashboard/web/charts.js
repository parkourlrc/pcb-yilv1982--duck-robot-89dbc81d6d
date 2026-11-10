import { h } from 'preact';
import { useEffect, useRef } from 'preact/hooks';
import htm from 'htm';

const html = htm.bind(h);
// 与界面共用色板；ECharts canvas 需要解析后的颜色值。
function chartTheme(element) {
  const style = getComputedStyle(element);
  const color = name => style.getPropertyValue(name).trim();
  return {
    colors: [1, 2, 3, 4, 5, 6].map(index => color(`--chart-${index}`)),
    text: color('--text'), muted: color('--muted'),
    panel: color('--panel-raised'), line: color('--line'),
  };
}

export function smoothPoints(points, windowSize) {
  if (windowSize <= 1) return points;
  return points.map((point, index) => {
    if (point[1] == null) return point;
    const values = points.slice(Math.max(0, index - windowSize + 1), index + 1).map(value => value[1]).filter(Number.isFinite);
    return [point[0], values.reduce((sum, value) => sum + value, 0) / values.length, ...point.slice(2)];
  });
}

export function Chart({ title, subtitle, series = [], axis = 'iteration', smoothing = 1, height = 250, scatter = false, empty = '暂无真实采样数据', xy = false }) {
  const element = useRef();
  const chart = useRef();
  const hasData = series.some(item => item.points?.some(point => Number.isFinite(point.value) && (xy ? Number.isFinite(point.x) : point[axis] != null)));
  const missingAxis = !hasData && series.some(item => item.points?.some(point => Number.isFinite(point.value))) && !xy;
  useEffect(() => {
    if (!hasData) return;
    chart.current = window.echarts.init(element.current, null, { renderer: 'canvas' });
    const resize = new ResizeObserver(() => chart.current?.resize()); resize.observe(element.current);
    return () => { resize.disconnect(); chart.current?.dispose(); chart.current = null; };
  }, [hasData]);
  useEffect(() => {
    if (!chart.current) return;
    const theme = chartTheme(element.current);
    chart.current.setOption({
      animation: false, color: theme.colors,
      textStyle: { fontFamily: 'Inter, Segoe UI, Microsoft YaHei, sans-serif', color: theme.muted },
      tooltip: { trigger: 'axis', renderMode: 'richText', backgroundColor: theme.panel, borderColor: theme.line, textStyle: { color: theme.text }, formatter: parameters => (Array.isArray(parameters) ? parameters : [parameters]).map(parameter => {
        const values = parameter.value, value = values?.[1];
        const horizontal = axis === 'timestamp' ? new Date(values[0]).toLocaleTimeString() : values[0];
        const samples = values?.[2] == null ? '' : ` · 实际样本 ${Number(values[2]).toLocaleString()}`;
        return `${parameter.seriesName}\n${horizontal}：${value == null ? '缺测' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 5 })}${samples}`;
      }).join('\n') },
      legend: { top: 3, textStyle: { color: theme.muted, fontSize: 11 }, type: 'scroll', pageTextStyle: { color: theme.muted } },
      grid: { left: 57, right: 24, top: 40, bottom: 53 },
      xAxis: { type: 'value', name: xy ? 'X / m' : ({ iteration: '更新轮次', transitions: '全局转换数', elapsed_s: '耗时 / s', sim_time_s: '仿真 / s', timestamp: '时间' }[axis] || axis), nameLocation: 'middle', nameGap: 30, axisLine: { lineStyle: { color: theme.line } }, splitLine: { show: false }, nameTextStyle: { color: theme.muted }, axisLabel: { color: theme.muted, hideOverlap: true, formatter: axis === 'timestamp' ? value => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : undefined } },
      yAxis: { type: 'value', scale: true, name: xy ? 'Y / m' : (series[0]?.unit || ''), splitLine: { lineStyle: { color: theme.line, type: 'dashed' } }, nameTextStyle: { color: theme.muted }, axisLabel: { color: theme.muted, formatter: value => Math.abs(value) >= 1000000 ? `${(value / 1000000).toFixed(1)}M` : Math.abs(value) >= 1000 ? `${(value / 1000).toFixed(1)}k` : Number(value.toPrecision(4)) } },
      dataZoom: [{ type: 'inside', filterMode: 'none' }],
      series: series.map((item, index) => {
        const points = (item.points || []).filter(point => xy ? Number.isFinite(point.x) : point[axis] != null).map(point => [xy ? point.x : point[axis], Number.isFinite(point.value) ? point.value : null, point.sample_count ?? null]);
        return { name: `${item.label || item.key}${item.scope === 'rank0' ? ' · rank0' : ''}`, type: scatter || item.kind === 'sparse' ? 'scatter' : 'line', encode: { x: 0, y: 1 }, showSymbol: scatter, symbolSize: 6, connectNulls: false, lineStyle: { width: 1.8, type: ['solid', 'dashed', 'dotted'][index % 3] }, emphasis: { focus: 'series' }, data: xy || scatter || item.kind === 'sparse' ? points : smoothPoints(points, smoothing) };
      }),
    }, true);
  }, [series, axis, smoothing, scatter, xy, hasData]);
  return html`<section class="chart-card"><div class="card-heading"><h3>${title}</h3>${subtitle && html`<span>${subtitle}</span>`}</div><div class="chart" ref=${element} style=${{ height }}>${!hasData && html`<div class="empty-chart"><span class="empty-axis">⌁</span><p>${missingAxis ? `已有指标，但日志缺少${({ elapsed_s: '实际耗时', transitions: '累计转换数', iteration: '更新轮次', timestamp: '采样时间' })[axis] || axis}字段；请选择其他横轴` : empty}</p></div>`}</div></section>`;
}
