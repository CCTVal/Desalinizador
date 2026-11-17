const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

async function main() {
  const occt = await require('occt-import-js')();
  const source = path.resolve('modelos/P23.00-00-A008v2.stp');
  const result = occt.ReadStepFile(fs.readFileSync(source), {
    linearUnit: 'meter', linearDeflectionType: 'absolute_value',
    linearDeflection: 0.0005, angularDeflection: 0.3,
  });
  assert.ok(result.success && result.meshes.length, 'El STEP no contiene mallas convertibles.');
  const THREE = await import('three');
  const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');
  global.FileReader = class {
    readAsArrayBuffer(blob) { blob.arrayBuffer().then(value => { this.result = value; this.onloadend?.(); }); }
    readAsDataURL(blob) { blob.arrayBuffer().then(value => { this.result = `data:${blob.type};base64,${Buffer.from(value).toString('base64')}`; this.onloadend?.(); }); }
  };
  const group = new THREE.Group();
  group.name = path.parse(source).name;
  const names = new Map();
  function collectNames(node, parent = '') {
    const name = node.name || parent;
    for (const index of node.meshes || []) names.set(index, name);
    for (const child of node.children || []) collectNames(child, name);
  }
  collectNames(result.root);
  let triangles = 0;
  for (const [i, mesh] of result.meshes.entries()) {
    const geometry = new THREE.BufferGeometry();
    assert.equal(mesh.attributes.position.array.length % 3, 0);
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(mesh.attributes.position.array, 3));
    geometry.setIndex(mesh.index.array);
    if (mesh.attributes.normal) geometry.setAttribute('normal', new THREE.Float32BufferAttribute(mesh.attributes.normal.array, 3));
    else geometry.computeVertexNormals();
    const material = new THREE.MeshStandardMaterial({ color: new THREE.Color(...(mesh.color || [0.65, 0.68, 0.68])), metalness: 0.18, roughness: 0.6 });
    const part = new THREE.Mesh(geometry, material);
    part.name = mesh.name || names.get(i) || `Pieza ${i + 1}`;
    part.userData.partId = i;
    // Preserve face colours from the source CAD instead of inventing equipment classes.
    for (const face of mesh.brep_faces || []) {
      if (!face.color) continue;
      if (!Array.isArray(part.material)) part.material = [material];
      part.material.push(new THREE.MeshStandardMaterial({ color: new THREE.Color(...face.color), metalness: 0.18, roughness: 0.6 }));
      geometry.addGroup(face.first * 3, (face.last - face.first + 1) * 3, part.material.length - 1);
    }
    if (Array.isArray(part.material) && geometry.groups.length) {
      const covered = new Set();
      for (const face of mesh.brep_faces || []) if (face.color) for (let t = face.first; t <= face.last; t++) covered.add(t);
      let start = -1;
      for (let t = 0; t <= mesh.index.array.length / 3; t++) {
        if (t < mesh.index.array.length / 3 && !covered.has(t)) { if (start < 0) start = t; }
        else if (start >= 0) { geometry.addGroup(start * 3, (t - start) * 3, 0); start = -1; }
      }
    }
    triangles += mesh.index.array.length / 3;
    group.add(part);
  }
  group.rotation.x = -Math.PI / 2; // STEP Z-up to glTF Y-up.
  group.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(group);
  const size = box.getSize(new THREE.Vector3());
  const metadata = {
    source: path.basename(source), units: 'm', parts: result.meshes.length, triangles,
    dimensions: { x: size.x, y: size.y, z: size.z },
    hierarchy: result.root,
    inventory: group.children.map(p => ({ id: p.userData.partId, name: p.name })),
    conversion: { linearDeflectionMeters: 0.0005, angularDeflection: 0.3, tool: 'occt-import-js 0.0.23' },
  };
  const glb = await new GLTFExporter().parseAsync(group, { binary: true });
  assert.ok(glb.byteLength > 100);
  const output = path.resolve('public/modelos');
  fs.mkdirSync(output, { recursive: true });
  fs.writeFileSync(path.join(output, 'planta.glb'), Buffer.from(glb));
  fs.writeFileSync(path.join(output, 'planta.meta.json'), JSON.stringify(metadata, null, 2));
  console.log(JSON.stringify({ ...metadata, inventory: undefined, hierarchy: undefined, glbBytes: glb.byteLength }, null, 2));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
