import assert from 'node:assert/strict';
import fs from 'node:fs';
import { pumpHead, solvePump } from '../src/pump-model.js';

const config = JSON.parse(fs.readFileSync('datos/bomba-vsse1-23.json', 'utf8'));
const base = { running: true, connected: true, frequencyHz: 50, openingPercent: 100, staticHeadM: 1, lossAt1M3h: (111 - 1) / 1.6 ** 2 };
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-7, `${a} != ${b}`);
for (const [q, h] of config.curve50Hz) near(pumpHead(config.curve50Hz, q), h);
assert.equal(pumpHead(config.curve50Hz, .1), null);
assert.equal(pumpHead(config.curve50Hz, 3), null);
const full = solvePump(config, base);
near(full.flowM3h, 1.6); near(full.headM, 111); near(full.pressureBar, 10.8891);
near(full.hydraulicPowerKw, .48396); near(full.shaftReferenceKw, 1.1);
const half = solvePump(config, { ...base, frequencyHz: 25, staticHeadM: .25 });
near(half.flowM3h, full.flowM3h / 2); near(half.headM, full.headM / 4);
near(half.hydraulicPowerKw, full.hydraulicPowerKw / 8); near(half.shaftReferenceKw, 1.1 / 8);
const throttled = solvePump(config, { ...base, openingPercent: 50 });
assert.equal(throttled.state, 'operating');
assert.ok(throttled.flowLMin < full.flowLMin);
assert.ok(throttled.headM > full.headM);
const closed = solvePump(config, { ...base, openingPercent: 0 });
assert.equal(closed.flowLMin, 0); assert.equal(closed.pressureBar, null);
assert.equal(closed.shaftReferenceKw, 1.1);
for (const changes of [{running: false}, {connected: false}, {frequencyHz: 0}]) assert.equal(solvePump(config, { ...base, ...changes }).flowLMin, 0);
for (const changes of [{staticHeadM: 200}, {lossAt1M3h: 0, staticHeadM: 0}, {openingPercent: 1}]) {
  const result = solvePump(config, { ...base, ...changes });
  assert.equal(result.state, 'outside_curve'); assert.equal(result.flowLMin, null);
}
for (const changes of [{frequencyHz: 60}, {staticHeadM: -1}, {lossAt1M3h: NaN}, {openingPercent: 101}]) assert.equal(solvePump(config, { ...base, ...changes }).state, 'invalid');
console.log('OK: tabla WDM, punto de trabajo, unidades, afinidad Q/H/P, válvula, parada, desconexión y límites sin extrapolación.');
for (const frequencyHz of [25, 50]) {
  const open = solvePump(config, { ...base, frequencyHz, bypassOpen: true });
  const shut = solvePump(config, { ...base, frequencyHz, bypassOpen: false });
  for (const result of [open, shut]) {
    assert.equal(result.state, 'operating');
    near(result.flowLMin, result.sprayFlowLMin + result.bypassFlowLMin);
    const nozzleHead = config.assumptions.sprayCircuit.nozzleResistanceMPerM3hSquared * (result.sprayFlowLMin * 60 / 1000) ** 2;
    near(result.sprayPressureBar, nozzleHead * 1000 * 9.81 / 100000);
    assert.ok(result.sprayPressureBar < result.pressureBar);
  }
  near(shut.bypassFlowLMin, 0);
  assert.ok(shut.sprayPressureBar > open.sprayPressureBar);
  assert.ok(shut.sprayFlowLMin > open.sprayFlowLMin);
  assert.ok(shut.flowLMin < open.flowLMin);
}
console.log('OK: llave 167, reparto de caudal, presión del aspersor y balance en ambos ramales.');
