const fs = require('fs');
const assert = require('assert');

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');
const app = fs.readFileSync(`${__dirname}/app.py`, 'utf8');

assert(html.includes('@stlite/browser'), 'pilot must use the browser Streamlit runtime');
assert(html.includes('../data/publications.json'), 'pilot must read the public snapshot only');
for (const text of ['每日关注', '产业链图谱', '深色为本期', '浅色为上一期']) assert(app.includes(text), `missing ${text}`);
assert(!/pdf_path|full_skill|api_key|credential|production_data|127\.0\.0\.1/.test(`${html}\n${app}`), 'pilot must not expose private source or local services');
console.log('PASS: stlite pilot carries only public daily and graph display code.');
