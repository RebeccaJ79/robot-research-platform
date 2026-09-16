const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/index.html','utf8');
const elements=new Map();
const element=()=>({innerHTML:'',textContent:'',hidden:false,style:{},dataset:{},setAttribute(){},removeAttribute(){},classList:{toggle(){}}});
const context={document:{getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},querySelectorAll(){return []}}};
vm.createContext(context);vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
const run=s=>vm.runInContext(s,context);
assert.equal(run('nodes.length'),23);
for(const tab of ['daily','weekly','monthly','graph']){
 run(`chooseTab('${tab}')`);assert.equal((elements.get('graph').innerHTML.match(/data-node=/g)||[]).length,23);
 assert.equal(elements.get('chartSection').hidden,tab==='graph');
}
run("chooseTab('graph')");
assert(elements.get('viewStyle').textContent.includes('.summary,.companies,#chartSection'));
run("chooseTab('daily')");const initial=elements.get('companies').innerHTML;const heading=elements.get('headline').textContent;
run('period=1;render()');assert.notEqual(elements.get('companies').innerHTML,initial);assert.notEqual(elements.get('headline').textContent,heading);
run("selected='减速器';render()");assert(elements.get('companies').innerHTML.includes('绿的谐波'));assert(!elements.get('companies').innerHTML.includes('汇川技术'));
run("selected='电池';render()");assert(elements.get('companies').innerHTML.includes('暂无关联'));assert(elements.get('trend').innerHTML.includes('暂无趋势'));
run("chooseTab('monthly')");assert(elements.get('bars').innerHTML.includes('比较期覆盖不足'));
run("edgeSelected=0;detail()");assert(elements.get('detail').innerHTML.includes('稀土磁材 → 伺服电机'));
run('zoomTo(9)');assert.equal(elements.get('zoom').textContent,'180%');
assert(!/fetch\(|XMLHttpRequest|https?:\/\//.test(html));
assert(!/Skill|审核记录|证据明细|生成按钮/.test(html));
console.log('PASS: 23 nodes in all four views; graph-only view; period updates; node/company/chart filtering; no-data state; relation details; zoom bounds; no remote requests.');
