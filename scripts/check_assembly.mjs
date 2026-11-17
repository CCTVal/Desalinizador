import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { connectDrumWithAdjustedSupport, DRUM_ASSEMBLY_IDS } from '../src/connect-assembly.js';
import { FLOW_SECTIONS, FLOW_CIRCUIT_IDS, buildFlowCurve } from '../src/flow-route.js';
import { setupSprinkler } from '../src/sprinkler.js';

const bytes = fs.readFileSync('public/modelos/planta.glb');
const { scene } = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
scene.rotation.x = Math.PI / 2;
const meshes = [];
scene.traverse(mesh => {
  if (!mesh.isMesh) return;
  mesh.geometry = mesh.geometry.clone(); mesh.geometry.computeBoundingBox();
  const pivot = mesh.geometry.boundingBox.getCenter(new THREE.Vector3());
  mesh.geometry.translate(-pivot.x, -pivot.y, -pivot.z);
  mesh.position.add(pivot.multiply(mesh.scale).applyQuaternion(mesh.quaternion)); meshes.push(mesh);
});
const originalBox = new THREE.Box3().setFromObject(scene);
const centre = originalBox.getCenter(new THREE.Vector3());
scene.position.set(-centre.x, -originalBox.min.y, -centre.z); scene.updateMatrixWorld(true);
const byId = new Map(meshes.map(mesh => [mesh.userData.partId, mesh]));
const moved = new Set(DRUM_ASSEMBLY_IDS);
const originalMatrices = new Map(meshes.filter(mesh => !moved.has(mesh.userData.partId)).map(mesh => [mesh, mesh.matrixWorld.clone()]));
const report = connectDrumWithAdjustedSupport(meshes);
assert.ok(report.portGapM < 1e-6);
assert.ok(Math.abs(report.supportGroundClearanceM) < 1e-6);
assert.ok(report.supportLegShorteningM > .022 && report.supportLegShorteningM < .024);
for (const [mesh, matrix] of originalMatrices) assert.ok(mesh.matrixWorld.equals(matrix), `La pieza fija ${mesh.userData.partId + 1} cambió`);
const bounds = id => new THREE.Box3().setFromObject(byId.get(id));
assert.ok(Math.abs(bounds(94).max.y - bounds(146).min.y) < 1e-6, 'La placa debe descansar sobre el soporte');
assert.ok(Math.abs(bounds(146).max.y - bounds(82).min.y) < 1e-6, 'El tambor debe descansar sobre la placa');
const sourceNormal = new THREE.Vector3(-1, 0, 0).transformDirection(byId.get(209).matrixWorld);
const targetNormal = new THREE.Vector3(-1, 0, 0).transformDirection(byId.get(123).matrixWorld);
assert.ok(sourceNormal.dot(targetNormal) < -.999999, 'Las bocas deben enfrentarse');
const collisions = [];
for (const id of moved) {
  const a = bounds(id);
  for (const mesh of meshes) {
    if (moved.has(mesh.userData.partId)) continue;
    const b = bounds(mesh.userData.partId);
    if (!a.intersectsBox(b)) continue;
    const overlap = a.clone().intersect(b).getSize(new THREE.Vector3());
    if ([overlap.x, overlap.y, overlap.z].every(size => size > 1e-5)) collisions.push([id + 1, mesh.userData.partId + 1]);
  }
}
assert.deepEqual(collisions, [], 'Hay interferencias entre conjuntos');
report.audit = {
  method: 'Cajas envolventes contra piezas fijas; no es una validación de fabricación',
  interferences: collisions,
  opposedPortNormalsDot: sourceNormal.dot(targetNormal),
  sourceTubeOuterDiameterMm: (bounds(209).max.y - bounds(209).min.y) * 1000,
  targetTubeOuterDiameterMm: (bounds(123).max.y - bounds(123).min.y) * 1000,
  supports: 'Apoyo en suelo, contacto soporte-placa y placa-tambor verificados',
};
report.note = 'Montaje propuesto autorizado por el usuario: ajustar soporte. Uniones, materiales y sellado pendientes de validar con el montaje real.';
for (const id of FLOW_CIRCUIT_IDS) assert.ok(byId.has(id), `Falta la pieza de recorrido ${id + 1}`);
const flowPoints = FLOW_SECTIONS.flat().map(([id, face]) => {
  const box = bounds(id), point = box.getCenter(new THREE.Vector3());
  if (face) point[face.at(-1).toLowerCase()] = box[face.slice(0, 3)][face.at(-1).toLowerCase()];
  return point;
});
const flowCurve = buildFlowCurve(flowPoints);
const terminal = flowCurve.getPointAt(1);
assert.ok(terminal.distanceTo(flowPoints.at(-1)) < 1e-8);
assert.ok(bounds(145).containsPoint(terminal), 'La descarga debe terminar dentro del recipiente existente');
assert.ok(flowCurve.getLength() > 5, 'El recorrido debe continuar después de la columna de subida');
for (let i = 1; i < flowCurve.curves.length; i++) {
  assert.ok(flowCurve.curves[i - 1].getPoint(1).distanceTo(flowCurve.curves[i].getPoint(0)) < 1e-8, 'Hay un salto entre tramos');
  assert.ok(flowCurve.curves[i - 1].getTangent(1).dot(flowCurve.curves[i].getTangent(0)) > .99, 'El codo no sigue la dirección de la cañería');
}
for (let t = 0; t <= 1; t += .01) assert.ok(flowCurve.getPointAt(t).toArray().every(Number.isFinite));
const water = new THREE.Group(), viewport = { dataset: {} };
const sprinkler = setupSprinkler({ water, meshes, viewport });
sprinkler.configure(flowCurve);
const arrival = Number(viewport.dataset.sprayArrivalM);
assert.ok(arrival > 2 && arrival < flowCurve.getLength());
sprinkler.tick(.1, { active: true, travelled: arrival - .01, flowLMin: 27.5, reduced: false });
assert.equal(viewport.dataset.sprayActive, 'false', 'No pulverizar antes de llegar el agua');
sprinkler.tick(0, { active: true, travelled: 0, flowLMin: 27.5, reduced: true });
assert.equal(viewport.dataset.sprayActive, 'true');
assert.ok(Number(viewport.dataset.sprayDropCount) > 24);
const instances = water.children[0].children.find(mesh => mesh.isInstancedMesh);
for (let i = 0; i < instances.count; i++) {
  const matrix = new THREE.Matrix4(); instances.getMatrixAt(i, matrix);
  const position = new THREE.Vector3().setFromMatrixPosition(matrix);
  assert.ok(position.y >= bounds(63).max.y - 1e-6 && position.y <= bounds(159).min.y + 1e-6, 'Gotas entre boca y bandeja');
  assert.ok(bounds(59).containsPoint(position), 'Gotas dentro de la columna');
}
sprinkler.tick(0, { active: false });
assert.equal(viewport.dataset.sprayActive, 'false');
report.flow = { lengthM: flowCurve.getLength(), finalOutletM: terminal.toArray(), finalPipeVisibleId: 172, recipientVisibleId: 146, continuousAtElbows: true, endsInsideRecipientBounds: true };
fs.writeFileSync('datos/montaje-conectado.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
