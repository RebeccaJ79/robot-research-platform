const assert = require('assert');
const fs = require('fs');

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');

assert(html.includes('function weeklyCalendarDates(report,dates)'), 'weekly line charts must derive seven calendar-day categories');
assert(html.includes('title:{left:0,'), 'every chart title must explicitly align left');
assert(html.includes('chain-stage-head'), 'transmission must render the upstream/midstream/downstream header row');
assert(html.includes('chain-stage-grid'), 'transmission cards must be classified into three stage columns');
assert(html.includes('function companyNodeDisplay(row)'), 'company table must preserve grouped node labels');
assert(html.includes('function amountDisplay(value)'), 'company table must render amount direction semantics');
assert(html.includes('function rankDisplay(value)'), 'company table must render rank direction semantics');
assert(html.includes('本期涨跌幅 = 最新有效交易日收盘价'), 'company table must retain the local calculation note');
assert(html.includes('function graphPositions(nodes,height)'), 'secondary graph cards must position relative to their primary parent');
assert(html.includes("symbol:'roundRect'"), 'primary and secondary graph nodes must be card-shaped');
assert(html.includes('class="mind-map-wrap"'), 'graph canvas must retain a horizontal scroll wrapper on narrow screens');
assert(html.includes('.mind-map{width:1080px;min-width:1080px'), 'graph canvas must preserve the local minimum width');

console.log('PASS: public reports and graph meet the local-layout parity contract.');
