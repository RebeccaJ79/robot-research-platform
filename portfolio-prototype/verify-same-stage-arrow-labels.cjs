const assert = require('assert');
const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
assert(html.includes('.vertical-flow-arrow{display:grid;grid-template-columns:minmax(0,1fr) 24px minmax(0,1fr)'), 'vertical arrow must reserve left and right text columns');
assert(html.includes('class="vertical-flow-arrow__relation"'), 'vertical arrow must render relation text on the left');
assert(html.includes('class="vertical-flow-arrow__status"'), 'vertical arrow must render status text on the right');
console.log('PASS: same-stage arrow labels flank the vertical direction marker.');
