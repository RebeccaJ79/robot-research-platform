const assert = require('assert');
const fs = require('fs');

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');

assert(!html.includes('产业链判断'), 'public reports must not render the industry-chain inference section');
assert(!html.includes('function uniqueConclusionItems(report)'), 'the removed inference section must not retain a hidden deduplication helper');

console.log('PASS: public reports omit the industry-chain inference section.');
