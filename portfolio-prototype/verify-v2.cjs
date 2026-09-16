const fs = require('fs');
const assert = require('assert');

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');
const embedded = html.match(/<script id="publication-data" type="application\/json">([\s\S]*?)<\/script>/);
assert(embedded, 'the publication snapshot must be embedded for an offline public site');
const snapshot = JSON.parse(embedded[1]);
assert.deepEqual(snapshot.publications.map(item => item.type), ['daily', 'weekly', 'monthly']);
assert.equal(snapshot.graph.nodes.length, 23);
for (const label of ['每日关注', '周报', '月报', '产业链图谱']) assert(html.includes(label), `missing ${label}`);
assert(html.includes('机器人产业研究台'), 'public shell must mirror the local research workbench');
assert(html.includes('深色为本期') && html.includes('浅色为上一期'), 'comparison legend is required');
assert(html.includes('stroke-dasharray'), 'comparison chart needs a dashed zero baseline');
assert(!/fetch\(|XMLHttpRequest|https?:\/\//.test(html), 'the public site must have no runtime remote dependency');
assert(!/Skill|审核记录|证据明细|生成按钮/.test(html), 'private workflow content must not be exposed');
console.log('PASS: embedded strict data, four public sections, local-style chart contract, and no remote dependency.');
