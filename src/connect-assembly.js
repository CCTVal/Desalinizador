import * as THREE from 'three';

export const DRUM_ASSEMBLY_IDS = [82, 83, 84, 85, 86, 94, 95, 96, 97, 98, 99, 146, 209];

function port(mesh, side) {
  mesh.updateWorldMatrix(true, false);
  const box = new THREE.Box3().setFromObject(mesh);
  const point = box.getCenter(new THREE.Vector3());
  point.x = side === 'min' ? box.min.x : box.max.x;
  return point;
}

// Proposed assembly: real CAD solids are repositioned, not stretched into a hose.
// Support adjustment chosen by the user; the source STEP/GLB stays unchanged.
export function connectDrumWithAdjustedSupport(meshes) {
  const byId = new Map(meshes.map(mesh => [mesh.userData.partId, mesh]));
  const drum = DRUM_ASSEMBLY_IDS.map(id => byId.get(id));
  if (drum.some(mesh => !mesh) || !byId.get(123)) throw Error('Faltan piezas del montaje del tambor.');
  const source = port(byId.get(209), 'min');
  const destination = port(byId.get(123), 'min');
  const rotation = new THREE.Matrix4().makeRotationY(Math.PI);
  const translation = destination.clone().sub(source.clone().applyMatrix4(rotation));
  const placement = new THREE.Matrix4().makeTranslation(...translation.toArray()).multiply(rotation);
  for (const mesh of drum) {
    mesh.updateWorldMatrix(true, false);
    const local = mesh.parent.matrixWorld.clone().invert().multiply(placement).multiply(mesh.matrixWorld);
    local.decompose(mesh.position, mesh.quaternion, mesh.scale);
    mesh.updateMatrix(); mesh.updateWorldMatrix(false, false);
  }
  const support = byId.get(94);
  const supportBox = new THREE.Box3().setFromObject(support);
  const shortenedBy = Math.max(0, -supportBox.min.y);
  if (shortenedBy > 0) {
    // Keep the upper frame's 25 mm vertical section unchanged; shorten only legs.
    const frameBottom = supportBox.max.y - .025;
    if (frameBottom <= 0) throw Error('El soporte no admite esta altura de montaje.');
    const inverse = support.matrixWorld.clone().invert();
    const positions = support.geometry.getAttribute('position');
    const vertex = new THREE.Vector3();
    const footTop = supportBox.min.y + .005;
    for (let i = 0; i < positions.count; i++) {
      vertex.fromBufferAttribute(positions, i).applyMatrix4(support.matrixWorld);
      // Preserve the existing 5 mm foot pads and the upper frame cross-section.
      if (vertex.y <= footTop + 1e-8) vertex.y += shortenedBy;
      else if (vertex.y < frameBottom) vertex.y = .005 + (vertex.y - footTop) * (frameBottom - .005) / (frameBottom - footTop);
      vertex.applyMatrix4(inverse);
      positions.setXYZ(i, vertex.x, vertex.y, vertex.z);
    }
    positions.needsUpdate = true;
    support.geometry.computeVertexNormals();
    support.geometry.computeBoundingBox(); support.geometry.computeBoundingSphere();
  }
  const outlet = port(byId.get(209), 'max');
  const inlet = port(byId.get(123), 'min');
  return {
    assemblyIds: DRUM_ASSEMBLY_IDS,
    rotationYDegrees: 180,
    translationM: translation.toArray(),
    supportLegShorteningM: shortenedBy,
    portGapM: outlet.distanceTo(inlet),
    sourcePortM: outlet.toArray(),
    destinationPortM: inlet.toArray(),
    supportGroundClearanceM: new THREE.Box3().setFromObject(support).min.y,
  };
}
