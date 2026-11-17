import * as THREE from 'three';

// shortcut: illustrative cone and enlarged drops; calibrate with the nozzle datasheet.
export function setupSprinkler({ water, meshes, viewport }) {
  const spray = new THREE.Group(); spray.name = 'Aspersor 159: gotas dentro de la columna'; water.add(spray);
  const geometry = new THREE.SphereGeometry(.0025, 6, 4);
  const material = new THREE.MeshBasicMaterial({ color: 0x36b7eb });
  const drops = new THREE.InstancedMesh(geometry, material, 120);
  drops.instanceMatrix.setUsage(THREE.DynamicDrawUsage); drops.frustumCulled = false; spray.add(drops);
  const dummy = new THREE.Object3D(); dummy.scale.set(1, 1.7, 1);
  const bounds = id => new THREE.Box3().setFromObject(meshes.find(mesh => mesh.userData.partId === id));
  let source, branch, arrival = Infinity, mainDistance = Infinity, height, radius, time = 0;
  function configure(curve) {
    const nozzle = bounds(159), column = bounds(59), tray = bounds(63);
    source = nozzle.getCenter(new THREE.Vector3()); source.y = nozzle.min.y;
    const inlet = source.clone(); inlet.y = bounds(125).getCenter(new THREE.Vector3()).y;
    height = source.y - tray.max.y - .00425;
    radius = Math.min(column.max.x - source.x, source.x - column.min.x, column.max.z - source.z, source.z - column.min.z) * .8;
    let nearest = Infinity, fraction = 0;
    for (let i = 0; i <= 1024; i++) {
      const distance = curve.getPointAt(i / 1024).distanceToSquared(inlet);
      if (distance < nearest) { nearest = distance; fraction = i / 1024; }
    }
    mainDistance = fraction * curve.getLength();
    arrival = mainDistance + inlet.distanceTo(source);
    if (branch) { spray.remove(branch); branch.geometry.dispose(); }
    branch = new THREE.Mesh(new THREE.TubeGeometry(new THREE.LineCurve3(inlet, source), 1, .003, 8, false), material);
    spray.add(branch);
    viewport.dataset.sprayOrigin = source.toArray().map(n => n.toFixed(4)).join(',');
    viewport.dataset.sprayStopY = tray.max.y.toFixed(4);
    viewport.dataset.sprayArrivalM = arrival.toFixed(4);
  }
  function tick(dt, { active, travelled, flowLMin, sprayFlowLMin = flowLMin / 3, pressureBar = 8, reduced }) {
    spray.visible = active && Boolean(source) && (reduced || travelled >= arrival);
    viewport.dataset.sprayActive = String(spray.visible);
    if (!spray.visible) { time = 0; viewport.dataset.sprayDropCount = '0'; return; }
    if (!reduced) time += dt;
    const launchSpeed = .7 * Math.sqrt(Math.max(0, pressureBar) / 8);
    const lifetime = (Math.sqrt(launchSpeed ** 2 + 2 * 9.81 * height) - launchSpeed) / 9.81;
    const elapsed = reduced ? lifetime : Math.max(0, (travelled - arrival) / (.35 * flowLMin / 27.5));
    // Tracer count and launch speed are visual scales, not measured droplet properties.
    const count = Math.min(120, Math.max(24, Math.round(sprayFlowLMin * 8)));
    let visible = 0;
    for (let i = 0; i < count; i++) {
      const phase = (i * .61803398875) % 1;
      const age = reduced ? phase * lifetime : (time + phase * lifetime) % lifetime;
      if (age > elapsed) continue;
      const angle = i * 2.3999632297;
      const spread = radius * Math.sqrt(((i * .754877666) % 1));
      dummy.position.set(source.x + Math.cos(angle) * spread * age / lifetime,
        source.y - launchSpeed * age - .5 * 9.81 * age * age,
        source.z + Math.sin(angle) * spread * age / lifetime);
      dummy.updateMatrix(); drops.setMatrixAt(visible++, dummy.matrix);
    }
    drops.count = visible; drops.instanceMatrix.needsUpdate = true;
    viewport.dataset.sprayDropCount = String(visible);
  }
  return { configure, tick, get mainDistance() { return mainDistance; } };
}
