import * as THREE from 'three';
import equipment from '../datos/equipos.json';

export function gaugeReading(result, min, max) {
  const pressure = result.pressureBar;
  const known = ['operating', 'off', 'zero_speed'].includes(result.state) && Number.isFinite(pressure);
  return {
    pressure: known ? pressure : null,
    angle: known ? -135 + 270 * (Math.max(min, Math.min(max, pressure)) - min) / (max - min) : null,
  };
}

// The same cubic-bezier(.32,.72,0,1) as --anatomy-ease, over 250 ms.
function ease(t) {
  const curve = (s, a, b) => 3 * (1 - s) ** 2 * s * a + 3 * (1 - s) * s ** 2 * b + s ** 3;
  let lo = 0, hi = 1;
  for (let i = 0; i < 16; i++) {
    const middle = (lo + hi) / 2;
    if (curve(middle, .32, 0) < t) lo = middle;
    else hi = middle;
  }
  return curve((lo + hi) / 2, .72, 1);
}

export function setupAnalogGauge({ meshes, viewport, reducedMotion }) {
  const instrument = equipment.equipos.find(item => item.id === 'manometro');
  const gaugeMeshes = meshes.filter(item => instrument.piezas_cad_asociadas.includes(item.userData.partId));
  const mesh = gaugeMeshes[0];
  const { min, max } = instrument.rango_declarado;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1024;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#f5f4ed'; ctx.fillRect(0, 0, 1024, 1024);
  ctx.strokeStyle = ctx.fillStyle = '#232629';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  for (let i = 0; i <= 70; i++) {
    const angle = (-135 + i / 70 * 270) * Math.PI / 180;
    const point = radius => [512 + Math.sin(angle) * radius, 512 - Math.cos(angle) * radius];
    const major = i % 10 === 0;
    ctx.lineWidth = major ? 6 : 3;
    ctx.beginPath(); ctx.moveTo(...point(major ? 370 : 397)); ctx.lineTo(...point(435)); ctx.stroke();
    if (major) {
      ctx.font = '48px sans-serif';
      ctx.fillText(String(min + (max - min) * i / 70), ...point(310));
    }
  }
  ctx.font = '44px sans-serif'; ctx.fillText('bar', 512, 695);
  ctx.font = '24px sans-serif'; ctx.fillText('SIMULADO', 512, 750);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const face = new THREE.Mesh(new THREE.CircleGeometry(.0438, 96), new THREE.MeshStandardMaterial({ map: texture, roughness: .8 }));
  const dial = new THREE.Group(); dial.name = 'Carátula del manómetro';
  // CAD front x=-.0315 m, normal -X, radius 44 mm; main.js centres the mesh pivot.
  dial.position.set(-.02165, 0, 0);
  dial.rotation.y = -Math.PI / 2;
  dial.add(face); mesh.add(dial);
  const shape = new THREE.Shape();
  shape.moveTo(-.0008, -.007); shape.lineTo(0, .033); shape.lineTo(.0008, -.007); shape.closePath();
  const dark = new THREE.MeshStandardMaterial({ color: 0x232629, roughness: .45, metalness: .35 });
  const needle = new THREE.Mesh(new THREE.ShapeGeometry(shape), dark);
  needle.name = 'Aguja';
  needle.position.z = .0004; dial.add(needle);
  const hub = new THREE.Mesh(new THREE.CircleGeometry(.0025, 32), dark);
  hub.position.z = .0006; dial.add(hub);
  const needles = [needle];
  for (const other of gaugeMeshes.slice(1)) {
    const copy = dial.clone(true);
    other.add(copy);
    needles.push(copy.getObjectByName('Aguja'));
  }
  const states = needles.map((item, i) => ({ needle: item, mesh: gaugeMeshes[i], target: 0, from: 0, elapsed: .25, key: undefined }));
  function refresh() {
    let changed = false;
    for (const state of states) {
      const id = state.mesh.userData.partId;
      const pressure = viewport.simulatedReadings?.[id]?.value ?? null;
      if (state.key === pressure) continue;
      changed = true; state.key = pressure;
      const reading = gaugeReading({ state: 'operating', pressureBar: pressure }, min, max);
      const wasVisible = state.needle.visible;
      state.needle.visible = reading.angle !== null;
      if (state.needle.visible) {
        state.from = state.needle.rotation.z;
        state.target = -reading.angle * Math.PI / 180;
        state.elapsed = 0;
        if (reducedMotion.matches || !wasVisible) { state.needle.rotation.z = state.target; state.elapsed = .25; }
      }
      viewport.dataset[`gauge${id + 1}PressureBar`] = pressure ?? '';
      viewport.dataset[`gauge${id + 1}NeedleVisible`] = String(state.needle.visible);
    }
    if (changed) document.getElementById('gauge-status').textContent = states.map(state => {
      const value = state.key === null ? 'sin estimación' : `${state.key.toLocaleString('es-CL', { maximumFractionDigits: 2 })} bar`;
      return `Manómetro ${state.mesh.userData.partId + 1}: ${value}`;
    }).join('. ') + '. Presiones locales simuladas con pérdidas supuestas.';
  }
  function tick(dt) {
    let moving = false;
    for (const state of states) {
      if (!state.needle.visible) continue;
      moving ||= state.elapsed < .25 && state.mesh.visible;
      state.elapsed = reducedMotion.matches ? .25 : Math.min(.25, state.elapsed + dt);
      state.needle.rotation.z = THREE.MathUtils.lerp(state.from, state.target, state.elapsed === .25 ? 1 : ease(state.elapsed / .25));
      viewport.dataset[`gauge${state.mesh.userData.partId + 1}NeedleAngle`] = (-state.needle.rotation.z * 180 / Math.PI).toFixed(4);
    }
    return moving;
  }
  return { refresh, tick };
}
