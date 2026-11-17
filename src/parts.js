import * as THREE from 'three';
import { TransformControls } from 'three/addons/controls/TransformControls.js';
import equipment from '../datos/equipos.json';
import { readingText, readingStatus } from './sensor-readings.js';

export function setupParts({ scene, camera, controls, viewport, meshes, meta, render, refit, toggleBypass }) {
  const $ = id => document.getElementById(id);
  const select = $('piece');
  const pump = equipment.equipos.find(item => item.id === 'bomba_principal');
  const gauge = equipment.equipos.find(item => item.id === 'manometro');
  const sensors = equipment.equipos.filter(item => item.id.startsWith('sensor_'));
  const info = $('pump-info');
  const sensorInfo = $('sensor-info');
  function updateSensorReading() {
    const reading = viewport.activeReadings?.[sensorInfo.dataset.partId];
    const serial = viewport.readingSource === 'serial';
    $('sensor-live-reading').textContent = `${serial ? 'Serie' : 'Simulado'}: ${readingText(reading)}`;
    $('sensor-source-note').textContent = serial ? 'Datos recibidos del Arduino por serie.' : 'Lectura simulada · escenario matemático.';
    const resistance = reading?.resistanceOhm;
    $('sensor-live-status').textContent = `${readingStatus(reading)}${Number.isFinite(resistance) ? ` · PT100 ideal: ${resistance.toLocaleString('es-CL', { maximumFractionDigits: 2 })} Ω` : ''}`;
  }
  viewport.addEventListener('sensor-readings', updateSensorReading);
  const valveButton = $('bypass-toggle');
  let valveHideTimer;
  const isValve = mesh => [166, 167, 168, 169].includes(mesh?.userData.partId);
  function showValveButton(show, immediate = false) {
    clearTimeout(valveHideTimer);
    if (show || immediate) viewport.dataset.valveHovered = String(show);
    else valveHideTimer = setTimeout(() => { viewport.dataset.valveHovered = 'false'; }, 220);
  }
  valveButton.addEventListener('pointerenter', () => showValveButton(true));
  valveButton.addEventListener('pointerleave', () => showValveButton(false));
  const number = value => value.toLocaleString('es-CL');
  for (const [label, value] of [
    ['Tipo', 'Vertical multietapa'],
    ['Cuerpo', pump.material_cuerpo],
    ['Conexiones', `${pump.conexiones_mm} mm`],
    ['Potencia nominal', `${number(pump.motor.potencia_declarada_kw)} kW · ${number(pump.motor.potencia_declarada_hp)} HP`],
    ['Alimentación nominal', `${pump.motor.tension_v} V · ${pump.motor.frecuencia_hz} Hz`],
  ]) {
    const row = document.createElement('div'), term = document.createElement('dt'), description = document.createElement('dd');
    term.textContent = label; description.textContent = value; row.append(term, description); $('pump-specifications').append(row);
  }
  function fillSensorInfo(sensor, mesh) {
    if (sensorInfo.dataset.partId === String(mesh.userData.partId)) return;
    sensorInfo.dataset.partId = mesh.userData.partId;
    $('sensor-info-title').textContent = [sensor.marca, sensor.modelo].filter(Boolean).join(' ') || sensor.nombre;
    const range = sensor.rango_declarado;
    const rows = [
      ['Equipo', sensor.clasificacion_usuario || sensor.nombre],
      ['Pieza', `${mesh.userData.partId + 1} · ${meta.inventory.find(item => item.id === mesh.userData.partId)?.name || mesh.name}`],
      ['Rango declarado', `${number(range.min)}–${number(range.max)} ${range.unidad}`],
    ];
    if (sensor.tipo === 'PT100') rows.push(
      ['Hilos', number(sensor.hilos)],
      ['Bulbo', sensor.material_bulbo],
      ['Diámetro del bulbo', `${number(sensor.diametro_bulbo_mm)} mm`],
    );
    if (!sensor.marca || !sensor.modelo) rows.push(['Marca y modelo', 'Pendientes de confirmar']);
    $('sensor-specifications').replaceChildren();
    for (const [label, value] of rows) {
      const row = document.createElement('div'), term = document.createElement('dt'), description = document.createElement('dd');
      term.textContent = label; description.textContent = value;
      if (label === 'Pieza') description.id = 'sensor-piece';
      row.append(term, description); $('sensor-specifications').append(row);
    }
  }
  function hideInfo() { info.hidden = sensorInfo.hidden = true; viewport.removeAttribute('aria-describedby'); }
  function showInfo(mesh, x, y) {
    hideInfo();
    const sensor = sensors.find(item => item.piezas_cad_asociadas.includes(mesh?.userData.partId));
    const panel = pump.piezas_cad_asociadas.includes(mesh?.userData.partId) ? info
      : sensor ? sensorInfo : null;
    if (!panel) return;
    if (panel === sensorInfo) { fillSensorInfo(sensor, mesh); updateSensorReading(); }
    panel.hidden = false; viewport.setAttribute('aria-describedby', panel.id);
    const box = panel.getBoundingClientRect();
    const left = x + 14 + box.width > innerWidth - 8 ? x - box.width - 14 : x + 14;
    panel.style.left = `${Math.max(8, Math.min(innerWidth - box.width - 8, left))}px`;
    panel.style.top = `${Math.max(8, Math.min(innerHeight - box.height - 8, y + 14))}px`;
  }
  const originals = new Map(meshes.map(mesh => [mesh, mesh.position.clone()]));
  const materials = new Map(meshes.map(mesh => [mesh, mesh.material]));
  const selectedMaterial = new THREE.MeshStandardMaterial({ color: 0xb48a44, roughness: .55, metalness: .18 });
  const transform = new TransformControls(camera, viewport.querySelector('canvas'));
  transform.setMode('translate'); transform.setSpace('world'); transform.setSize(.8);
  scene.add(transform.getHelper());
  let selected = null, focus = null, focusRadius = null, down = null;
  const originalWorld = new THREE.Vector3();
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  for (const mesh of meshes) {
    const option = document.createElement('option');
    option.value = mesh.userData.partId;
    option.textContent = `${mesh.userData.partId + 1} · ${meta.inventory.find(p => p.id === mesh.userData.partId)?.name || mesh.name}`;
    const instrument = equipment.equipos.find(item => item.nombre && item.piezas_cad_asociadas.includes(mesh.userData.partId));
    if (instrument) option.textContent += ` · ${instrument.nombre}`;
    select.append(option);
  }
  function updateFields() {
    if (!selected) return;
    selected.updateWorldMatrix(true, false);
    const offset = selected.getWorldPosition(new THREE.Vector3()).sub(originalWorld);
    for (const axis of ['x', 'y', 'z']) $(`piece-${axis}`).value = Number(offset[axis].toFixed(3));
    viewport.dataset.selectedPart = selected.userData.partId + 1;
    viewport.dataset.pieceOffset = offset.toArray().map(n => n.toFixed(3)).join(',');
  }
  function visibility() {
    for (const mesh of meshes) {
      mesh.visible = !selected || !$('isolate-piece').checked || mesh === selected;
      mesh.material = mesh === selected && !gauge.piezas_cad_asociadas.includes(mesh.userData.partId) ? selectedMaterial : materials.get(mesh);
    }
    render();
  }
  function choose(mesh) {
    showValveButton(false, true);
    selected = mesh;
    select.value = mesh ? mesh.userData.partId : '';
    $('piece-controls').disabled = !mesh;
    if (mesh) {
      mesh.parent.updateWorldMatrix(true, false);
      originalWorld.copy(originals.get(mesh)).applyMatrix4(mesh.parent.matrixWorld);
      const box = new THREE.Box3().setFromObject(mesh);
      focus = box.getCenter(new THREE.Vector3());
      focusRadius = Math.max(.005, box.getSize(new THREE.Vector3()).length() / 2);
      if (gauge.piezas_cad_asociadas.includes(mesh.userData.partId)) transform.detach();
      else transform.attach(mesh);
      updateFields();
    } else {
      transform.detach(); focus = focusRadius = null;
      for (const axis of ['x', 'y', 'z']) $(`piece-${axis}`).value = 0;
      delete viewport.dataset.selectedPart; delete viewport.dataset.pieceOffset;
    }
    visibility(); refit();
    const rect = viewport.getBoundingClientRect();
    showInfo(mesh, rect.left + rect.width / 2, rect.top + rect.height / 2);
  }
  select.onchange = () => choose(meshes.find(mesh => String(mesh.userData.partId) === select.value) || null);
  for (const button of document.querySelectorAll('[data-sensor-piece]')) button.onclick = () => {
    choose(meshes.find(mesh => mesh.userData.partId === Number(button.dataset.sensorPiece) - 1));
    viewport.scrollIntoView({ block: 'start' });
  };
  $('isolate-piece').onchange = () => { visibility(); refit(); };
  for (const axis of ['x', 'y', 'z']) $(`piece-${axis}`).onchange = () => {
    if (!selected) return;
    const values = ['x', 'y', 'z'].map(key => Number($(`piece-${key}`).value));
    if (values.some(value => !Number.isFinite(value))) return;
    const position = originalWorld.clone().add(new THREE.Vector3(...values));
    selected.position.copy(selected.parent.worldToLocal(position));
    updateFields(); render();
  };
  $('reset-piece').onclick = () => {
    if (!selected) return;
    selected.position.copy(originals.get(selected)); choose(selected);
  };
  $('reset-pieces').onclick = () => {
    for (const mesh of meshes) mesh.position.copy(originals.get(mesh));
    choose(null);
  };
  transform.addEventListener('dragging-changed', event => { controls.enabled = !event.value; });
  transform.addEventListener('objectChange', () => { updateFields(); render(); });
  transform.addEventListener('change', render);
  viewport.addEventListener('pointerdown', event => {
    if (info.contains(event.target) || sensorInfo.contains(event.target) || event.target.closest('button')) return;
    if (event.button === 0) down = { x: event.clientX, y: event.clientY, gizmo: Boolean(transform.axis) };
  });
  function hitAt(x, y) {
    const rect = viewport.getBoundingClientRect();
    pointer.set((x - rect.left) / rect.width * 2 - 1, -(y - rect.top) / rect.height * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    return raycaster.intersectObjects(meshes.filter(mesh => mesh.visible), false)[0]?.object;
  }
  let hoverFrame = 0;
  viewport.addEventListener('pointermove', event => {
    if (valveButton.contains(event.target)) { showValveButton(true); return; }
    if (info.contains(event.target) || sensorInfo.contains(event.target)) return;
    cancelAnimationFrame(hoverFrame);
    if (event.buttons || transform.dragging) { hideInfo(); showValveButton(false, true); return; }
    hoverFrame = requestAnimationFrame(() => {
      const hit = hitAt(event.clientX, event.clientY);
      showInfo(hit, event.clientX, event.clientY);
      showValveButton(isValve(hit));
    });
  });
  viewport.addEventListener('pointerleave', () => { cancelAnimationFrame(hoverFrame); hideInfo(); showValveButton(false, true); });
  viewport.addEventListener('wheel', hideInfo, { passive: true });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') { cancelAnimationFrame(hoverFrame); hideInfo(); showValveButton(false, true); } });
  viewport.addEventListener('pointerup', event => {
    if (!down) return;
    const start = down; down = null;
    if (start.gizmo || transform.dragging || Math.hypot(event.clientX - start.x, event.clientY - start.y) > 5) return;
    const hit = hitAt(event.clientX, event.clientY);
    if (isValve(hit)) { toggleBypass(); return; }
    if (hit) { choose(hit); showInfo(hit, event.clientX, event.clientY); }
  });
  viewport.addEventListener('pointercancel', () => { down = null; });
  $('pieces-panel').disabled = false;
  return {
    getFocus: () => $('isolate-piece').checked ? focus : null,
    getRadius: () => $('isolate-piece').checked ? focusRadius : null,
    getInspectionDirection: () => $('isolate-piece').checked && gauge.piezas_cad_asociadas.includes(selected?.userData.partId)
      ? new THREE.Vector3(-1, 0, 0).applyQuaternion(selected.getWorldQuaternion(new THREE.Quaternion())) : null,
  };
}
