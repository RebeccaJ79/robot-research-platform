const fs = require('fs');
const assert = require('assert');

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');
const snapshot = JSON.parse(fs.readFileSync(`${__dirname}/data/publications.json`, 'utf8'));
for (const token of ['--paper:#f3f1eb', 'workbench-brandbar', '机器人产业研究台', '每日关注', '周报', '月报', '产业链图谱']) {
  assert(html.includes(token), `missing local-workbench contract: ${token}`);
}
assert(html.includes('echarts.init'), 'public charts must use ECharts');
assert(html.includes('vendor/echarts.min.js'), 'ECharts must be bundled with the static site');
assert(fs.statSync(`${__dirname}/vendor/echarts.min.js`).size > 1_000_000, 'bundled ECharts runtime is incomplete');
assert(html.includes('markLine'), 'comparison chart must retain the zero baseline');
assert(html.includes('深色为本期') && html.includes('浅色为上一期'), 'comparison legend is required');
assert(html.includes('transmission_map') && html.includes('conclusions') && html.includes('data_notes'), 'full report layout fields are required');
assert(html.includes('data/publications.json'), 'the site must render the published snapshot');
for (const report of snapshot.publications) {
  for (const field of ['conclusions', 'transmission_map', 'data_notes', 'generated_at']) {
    assert(Object.hasOwn(report, field), `published ${report.type} report missing ${field}`);
  }
}
assert(!/pdf_path|full_skill|api_key|credential|production_data|127\.0\.0\.1/.test(html), 'private workflow fields must not appear');
console.log('PASS: static public workbench reproduces the local layout contract with ECharts and public data only.');
