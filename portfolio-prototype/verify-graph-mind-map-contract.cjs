const assert = require('assert');
const fs = require('fs');

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');

assert(html.includes('function drawMindMap(graph)'), 'graph page must render a mind-map chart');
assert(html.includes("type:'graph'"), 'mind map must use an ECharts graph series');
assert(html.includes("symbol:kind==='relation'?['none','arrow']:['none','none']"), 'published industry relationships must retain directed arrows while hierarchy links do not');
assert(html.includes('class="mind-map"'), 'graph page must reserve a visible chart area');

console.log('PASS: industry chain is rendered as an interactive directed mind map.');
