const assert = require('assert');
const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
assert(html.includes("childColors={U:'#b7c4e7',M:'#f7c9a9',D:'#b5ddcf'}"), 'secondary graph nodes must use a lighter stage palette');
assert(html.includes("color:isChild?(childColors[node.stream]||childColors.M):(colors[node.stream]||colors.M)"), 'secondary graph cards must use the lighter palette while primary cards remain saturated');
assert(html.includes("borderColor:isChild?'#d7dee8':'#fff'"), 'secondary graph cards must use a subdued border');
console.log('PASS: secondary graph nodes are visually distinct light cards.');
