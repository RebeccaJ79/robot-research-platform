const assert = require('assert');
const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
assert(html.includes('function verticalDirection(item)'), 'same-stage relations must resolve a vertical direction');
assert(html.includes("'vertical-flow-arrow'"), 'same-stage relations must use a vertical arrow element');
assert(html.includes("verticalDirection(item)==='up'"), 'upward relations must reverse source and target cards');
assert(html.includes("arrow(item,verticalDirection(item))"), 'same-stage arrows must follow relation direction');
console.log('PASS: same-stage relationships use direction-aware vertical arrows.');
