import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { setupHydraulics } from './hydraulics.js';
import { setupParts } from './parts.js';
import { setupAnalogGauge } from './analog-gauge.js';
import { setupSerial } from './serial-controls.js';
import { connectDrumWithAdjustedSupport } from './connect-assembly.js';
import './style.css';

const viewport = document.getElementById('viewport');
const zoom = document.getElementById('zoom');
const rotateButton = document.getElementById('rotate-view');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
let renderer, scene, camera, controls, hydraulics, parts, gauge, radius = 1;
const overviewTarget = new THREE.Vector3();
const initialDirection = new THREE.Vector3(.015, .65, -1.2).normalize();
let previousZoom = 1;

function render() { hydraulics?.refresh(); gauge?.refresh(); gauge?.tick(0); hydraulics?.positionValveLabel(camera); renderer.render(scene, camera); }
function setRotation(active) {
  controls.autoRotate = active;
  rotateButton.textContent = active ? 'Detener giro' : 'Girar planta';
  rotateButton.setAttribute('aria-pressed', String(active));
  viewport.dataset.autoRotate = String(active);
  document.getElementById('pump-info').hidden = true;
  document.getElementById('sensor-info').hidden = true;
  viewport.removeAttribute('aria-describedby');
}
function focusCamera() {
  if (hydraulics) {
    const focus = parts?.getFocus() || overviewTarget.clone().lerp(hydraulics.origin, THREE.MathUtils.clamp(camera.zoom - 1, 0, 1));
    camera.position.add(focus.clone().sub(controls.target));
    controls.target.copy(focus);
  }
}
function syncZoom() {
  // Reframe only on zoom; rotating or panning must keep the user's target.
  if (camera.zoom !== previousZoom) focusCamera();
  previousZoom = camera.zoom;
  zoom.value = Math.round(camera.zoom * 100);
  document.getElementById('zoom-value').textContent = `${Math.round(camera.zoom * 100)} %`;
  viewport.dataset.zoom = camera.zoom;
  render();
}
function frameView() {
  setRotation(false);
  camera.zoom = 1; focusCamera();
  camera.position.copy(controls.target).addScaledVector(initialDirection, radius * 4);
  camera.updateProjectionMatrix(); controls.update(); syncZoom();
}
function setZoom(value) {
  camera.zoom = THREE.MathUtils.clamp(value, .5, 4);
  camera.updateProjectionMatrix(); syncZoom();
}
function resize() {
  const { width, height } = viewport.getBoundingClientRect();
  if (!width || !height) return;
  renderer.setSize(width, height);
  const aspect = width / height;
  const baseline = (parts?.getRadius() || radius) * 1.08 / Math.min(1, aspect);
  camera.left = -baseline * aspect; camera.right = baseline * aspect;
  camera.top = baseline; camera.bottom = -baseline;
  camera.updateProjectionMatrix(); render();
}
async function init() {
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  viewport.prepend(renderer.domElement);
  scene = new THREE.Scene(); scene.background = new THREE.Color(0xfbfbfa);
  camera = new THREE.OrthographicCamera(-1, 1, 1, -1, .001, 100);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x77808a, 1.8));
  const key = new THREE.DirectionalLight(0xffffff, 2); key.position.set(5, 8, 4); scene.add(key);
  key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.normalBias = .002;
  const fill = new THREE.DirectionalLight(0xc3d1e0, 1.2); fill.position.set(-4, 2, -2); scene.add(fill);
  const [gltf, meta] = await Promise.all([
    new GLTFLoader().loadAsync('/modelos/planta.glb'),
    fetch('/modelos/planta.meta.json').then(response => { if (!response.ok) throw Error('No se encontraron los datos del modelo.'); return response.json(); }),
  ]);
  document.getElementById('viewer-title').textContent = meta.source.replace(/\.stp$/i, '');
  const plant = gltf.scene;
  plant.rotation.x = Math.PI / 2;
  const meshes = [];
  plant.traverse(object => {
    if (!object.isMesh) return;
    // CAD meshes share a remote origin; centre each pivot without moving its geometry.
    object.geometry = object.geometry.clone();
    object.geometry.computeBoundingBox();
    const pivot = object.geometry.boundingBox.getCenter(new THREE.Vector3());
    object.geometry.translate(-pivot.x, -pivot.y, -pivot.z);
    object.position.add(pivot.multiply(object.scale).applyQuaternion(object.quaternion));
    object.castShadow = true; meshes.push(object);
  });
  const box = new THREE.Box3().setFromObject(plant);
  const center = box.getCenter(new THREE.Vector3());
  plant.position.set(-center.x, -box.min.y, -center.z); scene.add(plant);
  const assembly = connectDrumWithAdjustedSupport(meshes);
  viewport.dataset.supportGroundClearance = assembly.supportGroundClearanceM;
  viewport.dataset.supportAdjustmentMm = assembly.supportLegShorteningM * 1000;
  const connectedBox = new THREE.Box3().setFromObject(plant);
  radius = connectedBox.getSize(new THREE.Vector3()).length() / 2;
  const target = connectedBox.getCenter(new THREE.Vector3());
  overviewTarget.copy(target);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(radius * 12, radius * 12), new THREE.ShadowMaterial({ opacity: .25 }));
  ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
  key.target.position.copy(target); scene.add(key.target);
  const shadowCamera = key.shadow.camera;
  shadowCamera.left = shadowCamera.bottom = -radius * 2;
  shadowCamera.right = shadowCamera.top = radius * 2;
  shadowCamera.far = 30; shadowCamera.updateProjectionMatrix();
  // Initial angle from the side where the drum's outlet is visible.
  camera.position.copy(target).addScaledVector(initialDirection, radius * 4);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.autoRotateSpeed = .8;
  controls.enableRotate = true; controls.enablePan = true;
  controls.minZoom = .5; controls.maxZoom = 4;
  controls.target.copy(target); controls.update();
  controls.addEventListener('change', syncZoom);
  controls.addEventListener('start', () => setRotation(false));
  rotateButton.onclick = () => setRotation(!controls.autoRotate);
  rotateButton.disabled = false;
  setRotation(false);
  zoom.oninput = () => setZoom(Number(zoom.value) / 100);
  zoom.disabled = false;
  document.getElementById('frame-view').onclick = frameView;
  viewport.addEventListener('keydown', event => {
    if (event.target === viewport && ['+', '=', '-'].includes(event.key)) {
      event.preventDefault(); setZoom(camera.zoom * (event.key === '-' ? .9 : 1.1));
    }
  });
  gauge = setupAnalogGauge({ meshes, viewport, reducedMotion });
  hydraulics = setupHydraulics({ scene, meshes, viewport, render, reducedMotion });
  parts = setupParts({ scene, camera, controls, viewport, meshes, meta, render, toggleBypass: hydraulics.toggleBypass, refit: () => {
    camera.zoom = 1; resize(); focusCamera(); controls.update(); syncZoom();
    const direction = parts?.getInspectionDirection();
    if (direction) { camera.position.copy(controls.target).addScaledVector(direction, radius * 4); controls.update(); syncZoom(); }
  } });
  new ResizeObserver(resize).observe(viewport);
  setupSerial({ viewport });
  resize(); syncZoom();
  document.getElementById('loading').hidden = true;
  viewport.dataset.parts = meshes.length;
  viewport.dataset.ready = 'true';
  document.getElementById('frame-view').disabled = false;
  const requestedPiece = Number(new URLSearchParams(location.search).get('pieza'));
  const pieceSelect = document.getElementById('piece');
  if (Number.isInteger(requestedPiece) && requestedPiece > 0 && [...pieceSelect.options].some(option => option.value === String(requestedPiece - 1))) {
    pieceSelect.value = String(requestedPiece - 1);
    pieceSelect.dispatchEvent(new Event('change'));
  }
  let last = performance.now();
  renderer.setAnimationLoop(now => {
    const dt = Math.min((now - last) / 1000, .05); last = now;
    const rect = viewport.getBoundingClientRect();
    if (document.hidden || rect.bottom <= 0 || rect.top >= innerHeight) return;
    const flowing = hydraulics.tick(dt);
    const needleMoving = gauge.tick(dt);
    const rotated = controls.autoRotate && controls.enabled ? controls.update(dt) : false;
    if ((flowing || needleMoving) && !rotated) render();
  });
}
init().catch(error => {
  console.error(error);
  document.getElementById('loading').hidden = false;
  document.getElementById('loading').textContent = `No se pudo abrir la planta. ${error.message} Comprueba WebGL y recarga la página.`;
  zoom.disabled = true;
  rotateButton.disabled = true;
  document.getElementById('bypass-toggle').disabled = true;
});
