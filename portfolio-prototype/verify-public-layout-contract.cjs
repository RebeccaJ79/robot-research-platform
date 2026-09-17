const assert = require('assert');
const fs = require('fs');

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');

assert(html.includes('.headline-card__main{text-align:left}'), 'core viewpoints must be explicitly left aligned');
assert(html.includes('function axisDate(value)'), 'date axes must use a dedicated MM-DD formatter');
assert(html.includes('axisLabel:{interval:0,hideOverlap:false,rotate:'), 'weekly line charts must show every trading date');
assert(html.includes('grid:{left:164,right:50,top:50,bottom:46}'), 'comparison charts need a wider node-label column');
assert(html.includes('edgeLabel:{show:true'), 'industry relations must be labelled on graph arrows');

console.log('PASS: public layout follows the requested report and graph display contract.');
