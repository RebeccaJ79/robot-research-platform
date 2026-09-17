const assert = require('assert');
const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
assert(html.includes("['focus_rank','关注排名'],['company_name','公司'],['node_name','所属节点'],['current_return','本期涨跌幅']"), 'company columns must place 所属节点 third and 本期涨跌幅 fourth');
assert(html.includes('data-company-search'), 'company table must provide a keyword filter');
assert(html.includes('data-company-stream'), 'company table must provide an industry-stage filter');
assert(html.includes('function setupCompanyTable(tableId,rows)'), 'company table must initialize client-side filtering and sorting');
assert(html.includes('data-company-sort'), 'company table headers must support sorting');
console.log('PASS: public company table restores sorting, filters, and requested column order.');