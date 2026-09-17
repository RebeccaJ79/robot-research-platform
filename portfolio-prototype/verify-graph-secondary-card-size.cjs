const assert = require('assert');
const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
assert(html.includes("function nodeSize(node){return node&&node.parent_id?[104,28]:[Math.max(108,String(node&&node.name||'').length*16),44]}"), 'secondary graph cards must use the compact 104×28 size while primary cards keep their current size');
console.log('PASS: secondary graph cards use the compact size.');
