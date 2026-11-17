import assert from 'node:assert/strict';
import { connectionRoute, portGap, PORT_TOLERANCE_M } from '../src/water-model.js';

const source = [-.55, .335, -.085];
const a = [-.368, .335, -.085];
const b = [...a];
const valve = [-.197, .335, -.085];
const end = [.064, .335, -.254];
const route = connectionRoute([source, a, b, valve, end]);
assert.deepEqual(route, [source, a, valve, end]);
assert.equal(portGap(a, b), 0);
assert.ok(portGap(a, [b[0] + .01, b[1], b[2]]) > PORT_TOLERANCE_M);
assert.ok(route.every(point => point[1] > 0));
console.log('OK: unión directa, puntos coincidentes y detección de separación; sin manguera añadida.');
