import * as THREE from 'three';
import { portGap, PORT_TOLERANCE_M } from './water-model.js';
import { setupPump } from './pump-controls.js';
import { FLOW_SECTIONS, FLOW_CIRCUIT_IDS, buildFlowCurve } from './flow-route.js';
import { setupSprinkler } from './sprinkler.js';

export function setupHydraulics({ scene, meshes, viewport, render, reducedMotion }) {
  const ids = FLOW_CIRCUIT_IDS;
  const pieces = new Map(ids.map(id => [id, meshes.find(mesh => mesh.userData.partId === id)]));
  if ([...pieces.values()].some(piece => !piece)) throw Error('Faltan piezas del montaje conectado.');
  const initialPositions = new Map([...pieces].map(([id, mesh]) => [id, mesh.getWorldPosition(new THREE.Vector3())]));
  function anchor(id, face) {
    const mesh = pieces.get(id);
    mesh.updateWorldMatrix(true, false);
    const box = new THREE.Box3().setFromObject(mesh);
    const position = box.getCenter(new THREE.Vector3());
    if (face === 'minX') position.x = box.min.x;
    if (face === 'maxX') position.x = box.max.x;
    if (face === 'minZ') position.z = box.min.z;
    if (face === 'maxZ') position.z = box.max.z;
    if (face === 'minY') position.y = box.min.y;
    if (face === 'maxY') position.y = box.max.y;
    return { mesh, local: mesh.worldToLocal(position) };
  }
  const anchors = FLOW_SECTIONS.flat().map(([id, face]) => anchor(id, face));
  const water = new THREE.Group(); water.name = 'Agua en cañería conectada'; scene.add(water);
  const sprinkler = setupSprinkler({ water, meshes, viewport });
  const material = new THREE.MeshBasicMaterial({ color: 0x258db8, transparent: true, opacity: .85, depthWrite: false });
  const dropMaterial = new THREE.MeshBasicMaterial({ color: 0x74e2ff });
  const recipient = meshes.find(mesh => mesh.userData.partId === 145);
  if (!recipient) throw Error('No se encontró el recipiente de la descarga final.');
  const translucentParts = [...pieces].filter(([id]) => ![82, 183, 63, 71, 73, 102, 105, 119, 135].includes(id)).map(([, mesh]) => mesh);
  translucentParts.push(recipient);
  const pipeMaterials = translucentParts.map(mesh => {
    const original = mesh.material;
    const translucent = (Array.isArray(original) ? original : [original]).map(material => {
      const copy = material.clone(); copy.transparent = true; copy.opacity = .3; copy.depthWrite = false; return copy;
    });
    return { mesh, original, translucent: Array.isArray(original) ? translucent : translucent[0] };
  });
  const dropGeometry = new THREE.SphereGeometry(.006, 8, 6);
  const drops = Array.from({ length: 28 }, () => {
    const mesh = new THREE.Mesh(dropGeometry, dropMaterial);
    mesh.renderOrder = 5; water.add(mesh); return mesh;
  });
  let trace, curve, length = 1, valveFraction = 1, signature = '', travelled = 0, pump, operatingPoint;
  const valve = meshes.find(mesh => mesh.userData.partId === 166);
  const valveLabel = document.getElementById('bypass-toggle');
  function positionValveLabel(camera) {
    camera.updateMatrixWorld();
    const point = valve.getWorldPosition(new THREE.Vector3());
    point.y += .08; point.project(camera);
    const { width, height } = viewport.getBoundingClientRect();
    valveLabel.hidden = !valve.visible || Math.abs(point.x) > 1 || Math.abs(point.y) > 1 || Math.abs(point.z) > 1;
    valveLabel.style.left = `${Math.max(4, Math.min(width - valveLabel.offsetWidth - 4, (point.x + 1) * width / 2 + 8))}px`;
    valveLabel.style.top = `${Math.max(4, Math.min(height - valveLabel.offsetHeight - 4, (1 - point.y) * height / 2))}px`;
  }
  const origin = new THREE.Vector3();
  const segments = 480, sides = 8;
  function rebuild(points) {
    curve = buildFlowCurve(points);
    sprinkler.configure(curve);
    length = curve.getLength();
    let nearest = Infinity;
    const valvePoint = valve.getWorldPosition(new THREE.Vector3());
    for (let i = 0; i <= 1024; i++) {
      const distance = curve.getPointAt(i / 1024).distanceToSquared(valvePoint);
      if (distance < nearest) { nearest = distance; valveFraction = i / 1024; }
    }
    if (trace) { water.remove(trace); trace.geometry.dispose(); }
    trace = new THREE.Mesh(new THREE.TubeGeometry(curve, segments, .0035, sides, false), material);
    trace.renderOrder = 4; water.add(trace);
    viewport.dataset.waterSource = points[0].toArray().map(n => n.toFixed(3)).join(',');
    viewport.dataset.waterOutlet = points[1].toArray().map(n => n.toFixed(3)).join(',');
    viewport.dataset.waterDestination = points[2].toArray().map(n => n.toFixed(3)).join(',');
    viewport.dataset.waterValve = points[4].toArray().map(n => n.toFixed(3)).join(',');
    viewport.dataset.waterPathLength = length.toFixed(3);
    viewport.dataset.waterFinalOutlet = points.at(-1).toArray().map(n => n.toFixed(3)).join(',');
  }
  function refresh() {
    const points = anchors.map(({ mesh, local }) => {
      mesh.updateWorldMatrix(true, false);
      return mesh.localToWorld(local.clone());
    });
    origin.copy(points[1]);
    const gap = portGap(points[1].toArray(), points[2].toArray());
    const referenceDelta = pieces.get(209).getWorldPosition(new THREE.Vector3()).sub(initialPositions.get(209));
    const displaced = [...pieces].find(([id, mesh]) => mesh.getWorldPosition(new THREE.Vector3()).sub(initialPositions.get(id)).distanceTo(referenceDelta) > PORT_TOLERANCE_M);
    const connected = gap <= PORT_TOLERANCE_M && !displaced;
    operatingPoint = pump.evaluate(connected);
    if (operatingPoint.state !== 'operating') travelled = 0;
    viewport.dataset.connectionGapMm = (gap * 1000).toFixed(3);
    viewport.dataset.connectionState = connected ? 'connected' : 'disconnected';
    const nextSignature = points.flatMap(point => point.toArray()).join(',');
    if (connected && nextSignature !== signature) { rebuild(points); signature = nextSignature; }
    // Keep diagnostic ports current even when an edited part disconnects the circuit.
    viewport.dataset.waterOutlet = points[1].toArray().map(n => n.toFixed(3)).join(',');
    viewport.dataset.waterDestination = points[2].toArray().map(n => n.toFixed(3)).join(',');
    viewport.dataset.waterValve = points[4].toArray().map(n => n.toFixed(3)).join(',');
    const allVisible = [...pieces.values()].every(piece => piece.visible);
    water.visible = operatingPoint.state === 'operating' && connected && allVisible && points.every(point => point.y > 0);
    for (const { mesh, original, translucent } of pipeMaterials) {
      if (mesh.material === original || mesh.material === translucent) mesh.material = water.visible ? translucent : original;
    }
    viewport.dataset.waterOpen = String(water.visible);
    const arrived = reducedMotion.matches || travelled >= length;
    const status = !connected ? `Circuito desconectado · ${gap > PORT_TOLERANCE_M ? `separación ${Math.round(gap * 1000)} mm` : `pieza ${displaced[0] + 1} desplazada`}` : !allVisible ? 'Pieza aislada · recorrido oculto' : operatingPoint.state === 'operating' ? !operatingPoint.bypassOpen ? 'Llave 167 cerrada · agua hacia el aspersor · sin descarga por la bajante' : arrived ? 'Flujo continuo hasta la descarga final' : 'Agua avanzando hacia la descarga final' : document.getElementById('pump-status').textContent;
    const element = document.getElementById('water-status');
    if (element.textContent !== status) element.textContent = status;
    tick(0);
  }
  function tick(dt) {
    if (!water.visible || !curve) { sprinkler.tick(0, { active: false }); viewport.dataset.waterDischargeReached = 'false'; }
    if (!water.visible || !curve) return false;
    // Tracer speed is a visual scale proportional to Q, not physical pipe velocity.
    const speed = .35 * operatingPoint.flowLMin / 27.5;
    if (!reducedMotion.matches) travelled += dt * speed;
    sprinkler.tick(dt, { active: water.visible && operatingPoint.sprayFlowLMin > 0, travelled, flowLMin: operatingPoint.flowLMin, sprayFlowLMin: operatingPoint.sprayFlowLMin, pressureBar: operatingPoint.sprayPressureBar, reduced: reducedMotion.matches });
    const progress = reducedMotion.matches ? 1 : Math.min(1, travelled / length);
    const drawnProgress = Math.min(progress, operatingPoint.bypassOpen ? 1 : valveFraction);
    trace.geometry.setDrawRange(0, Math.floor(drawnProgress * segments) * sides * 6);
    const movingLength = operatingPoint.bypassOpen ? length : sprinkler.mainDistance;
    for (const [i, drop] of drops.entries()) {
      const distance = travelled - length * i / drops.length;
      drop.visible = !reducedMotion.matches && distance >= 0;
      if (drop.visible) drop.position.copy(curve.getPointAt((distance % movingLength) / length));
    }
    viewport.dataset.waterProgress = progress.toFixed(3);
    viewport.dataset.waterTravelledM = travelled.toFixed(4);
    viewport.dataset.waterDischargeReached = String(operatingPoint.bypassOpen && progress >= 1);
    viewport.dataset.waterDrawnProgress = drawnProgress.toFixed(3);
    return !reducedMotion.matches;
  }
  viewport.dataset.waterRoute = 'tambor > llave > unión directa > llave verde > bomba > subida > colector superior > llave derecha > bajante > descarga final';
  pump = setupPump({ viewport, onChange: () => { refresh(); render(); } });
  reducedMotion.addEventListener('change', () => {
    if (!reducedMotion.matches && water.visible) travelled = Math.max(travelled, length);
    tick(0); render();
  });
  refresh();
  return { tick, origin, refresh, positionValveLabel, toggleBypass: pump.toggleBypass };
}
