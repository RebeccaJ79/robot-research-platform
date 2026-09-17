const assert = require('assert');
const fs = require('fs');

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');

assert(
  !html.includes("transmission(report.transmission_map)+(report.conclusions||[]).length?"),
  'reportView must group the optional conclusions section so the complete report markup is returned',
);

console.log('PASS: reportView keeps its complete report markup before optional conclusions.');
