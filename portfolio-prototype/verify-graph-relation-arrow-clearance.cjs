const assert = require('assert');
const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
assert(html.includes('function relationPort(node,other)'), 'graph must calculate external ports for relation arrows');
assert(html.includes("sourcePort.id='relation-port-'"), 'graph must create invisible external relation-port nodes');
assert(html.includes("addLink(sourcePort.id,targetPort.id,relation.name||relation.relation_group,'relation')"), 'relation arrows must connect external ports rather than card centers');
assert(html.includes('symbolSize:1'), 'relation-port nodes must be visually hidden');
console.log('PASS: relation arrows are routed through external card ports.');
