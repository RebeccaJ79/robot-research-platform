const assert = require('assert');
const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
assert(html.includes("x={U:140,M:550,D:960}"), 'upstream, midstream, and downstream primary columns must have wider spacing');
assert(html.includes('.mind-map{width:1260px;min-width:1260px'), 'mind-map canvas must widen to accommodate the wider stage spacing');
assert(html.includes("symbol:kind==='relation'?['none','arrow']:['none','none']"), 'only published industry relations may have arrowheads');
assert(html.includes("type:kind==='relation'?'solid':'dashed'"), 'secondary hierarchy links must remain dashed');
console.log('PASS: graph hierarchy links are arrowless and stage columns are widened.');
