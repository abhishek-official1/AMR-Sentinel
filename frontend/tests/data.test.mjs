import test from 'node:test';
import assert from 'node:assert/strict';
import { segments, metricsFor, trendSummary, toCsv, filterObservations, targetMatches, numericObservations } from '../src/data.mjs';

test('missing years create separate observed line segments', () => {
  assert.deepEqual(segments([{year:2018,resistance_pct:0},{year:2019,resistance_pct:10},{year:2021,resistance_pct:20}]).map(x=>x.length), [2,1]);
});
test('model comparisons use identical available cases', () => {
  const rows=[{actual:10,naive_pred:12,linear_pred:11,ridge_pred:null},{actual:20,naive_pred:22,linear_pred:19,ridge_pred:21}];
  assert.deepEqual(metricsFor(rows).map(x=>x.n), [1,1,1]);
  assert.equal(metricsFor(rows)[0].mae_pp,2);
});
test('trend uses latest consecutive run and never labels two points as a trend', () => {
  const rows=[{year:2016,resistance_pct:1},{year:2020,resistance_pct:30},{year:2021,resistance_pct:32}];
  assert.equal(trendSummary(rows).direction, 'Insufficient data');
  assert.equal(trendSummary([...rows,{year:2022,resistance_pct:34}]).slope,2);
});
test('CSV exports preserve nulls, labels and escaped source text',()=>{
  assert.equal(toCsv([{value:null,record_type:'observed',note:'a,"b"'}]),'value,record_type,note\r\n,observed,"a,""b"""');
});
test('definition, year and region filters remain consistent',()=>{
  const rows=[{year:2022,who_region:'AFR',indicator_code:'E',statistic_type:'median'}, {year:2022,who_region:'EUR',indicator_code:'E',statistic_type:'adjusted'}];
  assert.equal(filterObservations(rows,{indicator:'E',statistic:'median',regions:['AFR'],from:2022,to:2022}).length,1);
});
test('null values never count as observed',()=>{
  assert.deepEqual(numericObservations([{year:2021,resistance_pct:0},{year:2022,resistance_pct:null}]).map(r=>r.year),[2021]);
});
test('coverage and model metadata cannot cross targets',()=>{
  const row={indicator_code:'MRSA_BSI',statistic_type:'who_unadjusted_regional_median'};
  assert.equal(targetMatches(row,{indicator_code:'ECOLI_3GC_BSI',statistic_type:'derived_country_median'}),false);
  assert.equal(targetMatches(row,row),true);
});
