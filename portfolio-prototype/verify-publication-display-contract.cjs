const assert = require('assert');
const fs = require('fs');

const snapshot = JSON.parse(fs.readFileSync(`${__dirname}/data/publications.json`, 'utf8'));
const reports = Object.fromEntries(snapshot.publications.map((report) => [report.type, report]));

assert.strictEqual(reports.daily.charts[1].title, '今日与前一交易日节点收益率对比');
assert.strictEqual(reports.daily.charts[1].metric.formula, '本期与前一有效交易日的节点收益率水平对比');
assert.strictEqual(reports.weekly.period_end, '20260719');
assert.strictEqual(reports.monthly.period_end, '20260731');
assert(snapshot.publications.every((report) => report.company_focus.every((company) => !Object.hasOwn(company, 'period_excess_return'))));

console.log('PASS: published reports show complete periods, accurate daily comparison wording, and no hidden anomalous company metric.');
