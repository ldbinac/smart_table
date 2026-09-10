const r = require('./.vitest-out.json');
console.log('suites:', r.numTotalTestSuites, 'total:', r.numTotalTests, 'passed:', r.numPassedTests, 'failed:', r.numFailedTests);
const fails = (r.testResults || []).flatMap(t => (t.assertionResults || []).filter(a => a.status !== 'passed'));
const byErr = {};
const others = [];
fails.forEach(a => {
  const m = (a.failureMessages || []).join(' ');
  let cat;
  if (m.includes('DocumentCopy')) cat = 'DocumentCopy';
  else if (m.includes('expected') && /to (be|contain|include)/.test(m)) cat = 'locale-or-assert';
  else cat = 'other';
  byErr[cat] = (byErr[cat] || 0) + 1;
  if (cat === 'other') others.push(a.fullName.slice(0, 80) + ' || ' + m.slice(0, 260));
});
console.log('by category:', JSON.stringify(byErr));
others.slice(0, 15).forEach(o => console.log('OTHER:', o));
