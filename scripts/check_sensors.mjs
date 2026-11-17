import assert from 'node:assert/strict';
import fs from 'node:fs';
import { solvePump, systemHead } from '../src/pump-model.js';
import { simulateSensors, pt100Resistance, waterTemperature, rangeState } from '../src/sensor-model.js';

const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const pump = read('datos/bomba-vsse1-23.json'), scenario = read('datos/simulacion-sensores.json'), equipment = read('datos/equipos.json');
const near = (a, b, tolerance = 1e-8) => assert.ok(Math.abs(a - b) < tolerance, `${a} != ${b}`);
const base = { running: true, connected: true, frequencyHz: 50, openingPercent: 100, staticHeadM: 1, lossAt1M3h: 40, bypassOpen: true, inletTemperatureC: 20, heatToWaterW: 0 };
const sensors = (settings, result = solvePump(pump, settings)) => simulateSensors(result, settings, pump, scenario, equipment);
let count = 0;
for (const frequencyHz of [10, 20, 30, 40, 50]) for (const openingPercent of [10, 25, 50, 75, 100]) for (const bypassOpen of [false, true]) {
  const settings = { ...base, frequencyHz, openingPercent, bypassOpen };
  const result = solvePump(pump, settings), readings = sensors(settings, result);
  if (result.state !== 'operating') { assert.equal(readings[102].value, null); continue; }
  count++;
  near(result.flowLMin, result.sprayFlowLMin + result.bypassFlowLMin);
  near(result.headM, systemHead(result.flowM3h, settings, pump));
  near(result.hydraulicPowerKw * 1000, result.pressureBar * 100000 * result.flowLMin / 60000);
  near(readings[135].value, result.flowLMin);
  near(readings[119].value, 20); // Flow alone must not invent warming.
  near(readings[119].resistanceOhm, 107.7935);
  assert.ok(readings[102].value > readings[105].value);
  assert.ok(readings[73].value > readings[71].value);
  // Elevation plus the distributed loss must explain the difference between taps.
  const dz = scenario.tomas[105].cotaM - scenario.tomas[102].cotaM;
  const length = scenario.colectorCotaM - scenario.subidaInicioCotaM + scenario.colectorLongitudM;
  const loss = .25 * settings.lossAt1M3h * result.flowM3h ** 2 * dz / length;
  near(readings[102].value - readings[105].value, 1000 * 9.81 * (dz + loss) / 100000);
}
assert.ok(count > 10);
for (const heatToWaterW of [-500, 0, 500]) {
  const settings = { ...base, heatToWaterW }, result = solvePump(pump, settings), readings = sensors(settings, result);
  near(1000 * result.flowLMin / 60000 * 4180 * (readings[119].value - 20), heatToWaterW);
}
near(waterTemperature(60, 20, 4180, 1000, 4180), 21);
near(waterTemperature(30, 20, 4180, 1000, 4180), 22);
for (const args of [[0,20,100],[10,20,1e9],[10,-1,0],[10,101,0],[10,NaN,0]]) assert.equal(waterTemperature(...args,1000,4180),null);
near(pt100Resistance(0), 100); near(pt100Resistance(100), 138.5055); near(pt100Resistance(-50), 80.306281875);
assert.equal(pt100Resistance(null), null);
for (const changes of [{ running: false }, { frequencyHz: 0 }, { openingPercent: 0 }]) {
  const readings = sensors({ ...base, ...changes });
  assert.equal(readings[102].value, null); assert.equal(readings[119].value, null);
  assert.equal(readings[135].value, 0); assert.equal(readings[135].state, 'below');
}
for (const changes of [{ connected: false }, { staticHeadM: NaN }, { openingPercent: 1 }]) {
  for (const reading of Object.values(sensors({ ...base, ...changes }))) assert.equal(reading.value, null);
}
for (const [value, state] of [[0,'below'],[9.9,'below'],[10,'within'],[100,'within'],[100.1,'above'],[null,'unknown']]) {
  assert.equal(rangeState(value, { min: 10, max: 100 }), state);
}
const below = sensors({ ...base, frequencyHz: 15 });
assert.ok(below[135].value < 10); assert.equal(below[135].state, 'below');
const demo = sensors(base);
console.log(JSON.stringify({ cases: count, example50Hz: demo }, null, 2));
console.log('OK: continuidad, energía, presiones locales, balance térmico, PT100, rangos y estados desconocidos.');
