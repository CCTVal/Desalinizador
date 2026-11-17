import config from '../datos/bomba-vsse1-23.json';
import { solvePump, systemHead } from './pump-model.js';
import equipment from '../datos/equipos.json';
import sensorScenario from '../datos/simulacion-sensores.json';
import { simulateSensors } from './sensor-model.js';
import { showSensorReadings } from './sensor-readings.js';

const $ = id => document.getElementById(id);
const fmt = (number, digits = 1) => number == null ? '—' : number.toLocaleString('es-CL', { minimumFractionDigits: digits, maximumFractionDigits: digits });

export function setupPump({ viewport, onChange }) {
  const settings = { running: false, connected: true, frequencyHz: 50, openingPercent: 0, staticHeadM: 1, lossAt1M3h: 40, bypassOpen: true,
    inletTemperatureC: sensorScenario.temperaturaEntradaC, heatToWaterW: sensorScenario.calorAlAguaW };
  $('water-temperature').value = settings.inletTemperatureC;
  $('water-heat').value = settings.heatToWaterW;
  let connected = true, previousKey = '', result;
  const point = (flowM3h, headM) => `${42 + flowM3h * 1000 / 60 / 40 * 350},${170 - Math.min(160, headM) / 160 * 145}`;
  function plot() {
    const ratio = settings.frequencyHz / config.nominalFrequencyHz;
    $('pump-curve').setAttribute('points', ratio > 0 ? config.curve50Hz.map(([q, h]) => point(q * ratio, h * ratio ** 2)).join(' ') : '');
    const system = [];
    if (settings.openingPercent > 0 && result.state !== 'invalid') for (let q = 0; q <= 2.4; q += .02) {
      const head = systemHead(q, settings, config);
      if (head > 160) break;
      system.push(point(q, head));
    }
    $('system-curve').setAttribute('points', system.join(' '));
    const marker = $('pump-duty-point');
    marker.style.display = result.state === 'operating' ? '' : 'none';
    if (result.state === 'operating') {
      const [cx, cy] = point(result.flowM3h, result.headM).split(',');
      marker.setAttribute('cx', cx); marker.setAttribute('cy', cy);
    }
  }
  function update() {
    settings.connected = connected;
    result = solvePump(config, settings);
    showSensorReadings(viewport, simulateSensors(result, settings, config, sensorScenario, equipment));
    $('frequency-value').textContent = `${settings.frequencyHz} Hz`;
    $('valve-value').textContent = `${settings.openingPercent} %`;
    $('pump-flow').textContent = `${fmt(result.flowLMin)} L/min`;
    $('pump-pressure').textContent = `${fmt(result.pressureBar, 2)} bar`;
    $('pump-hydraulic-power').textContent = `${fmt(result.hydraulicPowerKw, 3)} kW`;
    $('pump-shaft-reference').textContent = `${fmt(result.shaftReferenceKw, 3)} kW`;
    const knownZero = ['off', 'zero_speed', 'disconnected'].includes(result.state);
    const branchValue = key => result[key] ?? (knownZero || (result.state === 'closed' && key.endsWith('FlowLMin')) ? 0 : null);
    $('spray-pressure').textContent = `${fmt(branchValue('sprayPressureBar'), 2)} bar`;
    $('spray-flow').textContent = `${fmt(branchValue('sprayFlowLMin'))} L/min`;
    $('bypass-flow').textContent = `${fmt(settings.bypassOpen ? branchValue('bypassFlowLMin') : 0)} L/min`;
    $('bypass-state').textContent = settings.bypassOpen ? 'Abierta' : 'Cerrada';
    $('bypass-state-label').textContent = settings.bypassOpen ? 'Abierta' : 'Cerrada';
    $('bypass-toggle').setAttribute('aria-checked', String(settings.bypassOpen));
    $('bypass-toggle').title = `${settings.bypassOpen ? 'Cerrar' : 'Abrir'} llave 167 de descarga`;
    viewport.dataset.bypassOpen = String(settings.bypassOpen);
    viewport.dataset.sprayPressureBar = branchValue('sprayPressureBar') ?? '';
    viewport.dataset.sprayFlowLMin = branchValue('sprayFlowLMin') ?? '';
    viewport.dataset.bypassFlowLMin = settings.bypassOpen ? branchValue('bypassFlowLMin') ?? '' : 0;
    const status = {
      operating: `Punto de trabajo estimado · altura ${fmt(result.headM)} mca`,
      off: 'Bomba apagada', disconnected: 'Simulación bloqueada: circuito desconectado',
      zero_speed: 'Frecuencia cero · sin bombeo', closed: 'Llave cerrada · presión de cierre no tabulada',
      outside_curve: 'Fuera del tramo de curva publicado: no se estima caudal ni presión',
      invalid: 'Revisa los valores del circuito: deben ser números no negativos',
    }[result.state];
    $('pump-status').textContent = status;
    $('pump-info-status').textContent = status;
    $('pump-toggle').setAttribute('aria-pressed', String(settings.running));
    $('pump-toggle').textContent = settings.running ? 'Apagar bomba' : 'Encender bomba';
    $('valve-opening').value = settings.openingPercent;
    viewport.dataset.pumpState = result.state;
    viewport.dataset.pumpFlowLMin = result.flowLMin == null ? '' : result.flowLMin;
    viewport.dataset.pumpPressureBar = result.pressureBar == null ? '' : result.pressureBar;
    viewport.dataset.pumpHydraulicPowerKw = result.hydraulicPowerKw == null ? '' : result.hydraulicPowerKw;
    viewport.dataset.pumpShaftReferenceKw = result.shaftReferenceKw == null ? '' : result.shaftReferenceKw;
    plot();
    previousKey = JSON.stringify(settings);
  }
  function changed() { update(); onChange(); }
  function toggleBypass() { settings.bypassOpen = !settings.bypassOpen; changed(); }
  $('bypass-toggle').onclick = toggleBypass;
  $('bypass-toggle').disabled = false;
  $('pump-toggle').onclick = () => { settings.running = !settings.running; changed(); };
  $('pump-frequency').oninput = event => { settings.frequencyHz = Number(event.target.value); changed(); };
  $('valve-opening').oninput = event => { settings.openingPercent = Number(event.target.value); changed(); };
  for (const [id, key] of [['static-head', 'staticHeadM'], ['circuit-loss', 'lossAt1M3h'], ['water-temperature', 'inletTemperatureC'], ['water-heat', 'heatToWaterW']]) {
    $(id).onchange = event => { settings[key] = event.target.value === '' ? NaN : Number(event.target.value); changed(); };
  }
  $('pump-controls').disabled = false;
  update();
  return {
    toggleBypass,
    evaluate(isConnected) {
      connected = isConnected;
      const key = JSON.stringify({ ...settings, connected });
      if (key !== previousKey) update();
      return { ...result, bypassOpen: settings.bypassOpen };
    },
  };
}
