import * as THREE from 'three';
import { connectionRoute } from './water-model.js';

export const FLOW_SECTIONS = [
  [[86, 'minX'], [209, 'maxX'], [123, 'minX'], [123, 'maxX'], [207], [193, 'maxX'], [192, 'maxZ'], [195, 'minZ'], [194, 'minZ'], [175, 'minZ'], [122, 'minY'], [122, 'maxY']],
  [[155, 'minZ'], [155, 'maxZ'], [156, 'maxZ'], [125, 'minZ'], [125, 'maxZ'], [162, 'maxZ']],
  [[164, 'maxY'], [164, 'minY'], [171, 'maxY'], [171, 'minY']],
];

export const FLOW_CIRCUIT_IDS = [
  71, 73, 102, 105,
  82, 86, 95, 99, 209, 123, 79, 80, 207, 208, 200, 193, 199, 192, 195,
  180, 181, 182, 183, 194, 175, 122,
  118, 155, 156, 129, 130, 131, 132, 133, 134, 135, 78, 119, 125,
  140, 141, 160, 161, 162, 163, 164, 165, 166, 170, 171,
  59, 63, 158, 159,
];

function roundedPolyline(input) {
  const points = connectionRoute(input.map(point => point.toArray())).map(point => new THREE.Vector3(...point));
  const path = new THREE.CurvePath();
  let start = points[0];
  for (let i = 1; i < points.length - 1; i++) {
    const corner = points[i];
    const before = points[i - 1].clone().sub(corner);
    const after = points[i + 1].clone().sub(corner);
    const radius = Math.min(.01, before.length() * .25, after.length() * .25);
    const entry = corner.clone().add(before.normalize().multiplyScalar(radius));
    const exit = corner.clone().add(after.normalize().multiplyScalar(radius));
    path.add(new THREE.LineCurve3(start, entry));
    path.add(new THREE.QuadraticBezierCurve3(entry, corner, exit));
    start = exit;
  }
  path.add(new THREE.LineCurve3(start, points.at(-1)));
  return path;
}

function elbow(from, to, incoming, outgoing) {
  // Quarter-turn cubic: matches the directions of the existing CAD pipe ports.
  const factor = 4 / 3 * Math.tan(Math.PI / 8);
  const offset = to.clone().sub(from);
  const control1 = from.clone().addScaledVector(incoming, Math.abs(offset.dot(incoming)) * factor);
  const control2 = to.clone().addScaledVector(outgoing, -Math.abs(offset.dot(outgoing)) * factor);
  return new THREE.CubicBezierCurve3(from, control1, control2, to);
}

export function buildFlowCurve(points) {
  const firstLength = FLOW_SECTIONS[0].length;
  const secondEnd = firstLength + FLOW_SECTIONS[1].length;
  const lower = points.slice(0, firstLength);
  const upper = points.slice(firstLength, secondEnd);
  const down = points.slice(secondEnd);
  const path = new THREE.CurvePath();
  path.add(roundedPolyline(lower));
  path.add(elbow(lower.at(-1), upper[0], new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)));
  path.add(roundedPolyline(upper));
  path.add(elbow(upper.at(-1), down[0], new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, -1, 0)));
  path.add(roundedPolyline(down));
  return path;
}
