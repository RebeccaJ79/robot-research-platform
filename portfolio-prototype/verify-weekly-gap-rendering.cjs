const assert = require('assert');
const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
assert(html.includes('showSymbol:true'), 'weekly lines must show sampled-date points even when a gap prevents a segment');
assert(html.includes('connectNulls:false'), 'missing collection dates must break weekly line segments');
console.log('PASS: weekly chart preserves samples and gaps.');
