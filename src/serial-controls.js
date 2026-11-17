import equipment from '../datos/equipos.json';
import { rangeState } from './sensor-model.js';
import { renderSensorReadings } from './sensor-readings.js';

export function setupSerial({ viewport }) {
  const $ = id => document.getElementById(id);
  const sensors = equipment.equipos.filter(item => item.id.startsWith('sensor_'));
  let connected = false, busy = false, lastSnapshot = null, lastResponseAt = 0, failure = null;
  let stopped = false;
  let revision = 0;
  viewport.readingSource = 'simulation';
  async function api(path, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    try {
      const response = await fetch(path, { signal: controller.signal, cache: 'no-store',
        ...(body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) });
      const value = await response.json();
      if (!response.ok) throw Error(typeof value.detail === 'string' ? value.detail : 'No se pudo completar la conexión.');
      return value;
    } finally { clearTimeout(timeout); }
  }
  function buttons() {
    $('serial-connect').disabled = busy || connected || !$('serial-port').value;
    $('serial-disconnect').disabled = busy || !connected;
    $('serial-refresh').disabled = busy;
    $('serial-port').disabled = busy || connected;
    $('serial-baud').disabled = busy || connected;
  }
  function display() {
    const elapsed = (performance.now() - lastResponseAt) / 1000;
    const readings = {};
    for (const sensor of sensors) for (const id of sensor.piezas_cad_asociadas) {
      const row = lastSnapshot?.lecturas.find(item => item.pieza === id + 1);
      const fresh = !failure && row?.estado === 'vigente' && row.edad_s + elapsed <= lastSnapshot.caducidad_s;
      const value = fresh ? row.valor : null;
      const reason = failure ? 'Sin comunicación con la aplicación' : !lastSnapshot?.conectado ? 'Arduino desconectado'
        : row?.estado === 'vencida' || row?.estado === 'vigente' && !fresh ? 'Lectura vencida' : 'Esperando datos del sensor';
      readings[id] = { value, unit: sensor.rango_declarado.unidad, state: rangeState(value, sensor.rango_declarado), reason, source: 'serial', receivedAt: row?.recibida_en };
    }
    viewport.receivedReadings = readings;
    renderSensorReadings(viewport);
    const freshCount = Object.values(readings).filter(row => row.value !== null).length;
    const message = failure || lastSnapshot?.error || (connected
      ? `${lastSnapshot.puerto} conectado · ${freshCount}/4 lecturas actuales · ${lastSnapshot.mensajes_invalidos} mensajes descartados`
      : 'Arduino sin conectar.');
    if ($('serial-status').textContent !== message) $('serial-status').textContent = message;
    buttons();
  }
  function switchSource() {
    viewport.readingSource = $('reading-source').value;
    const serial = viewport.readingSource === 'serial';
    $('sensor-readings-title').textContent = serial ? 'Sensores · datos del Arduino' : 'Sensores · lecturas simuladas';
    $('reading-source-help').textContent = serial
      ? 'Lecturas recibidas por serie. Sin actualización durante 5 s: lectura vencida. El agua, las agujas y los controles de bomba siguen siendo una simulación independiente.'
      : 'Enciende la bomba y abre la alimentación. Pulsa una pieza para localizarla.';
    display();
  }
  async function ports() {
    try {
      const previous = $('serial-port').value;
      const ports = await api('/api/serie/puertos');
      $('serial-port').replaceChildren(new Option(ports.length ? 'Selecciona un puerto' : 'Sin puertos disponibles', ''));
      for (const port of ports) $('serial-port').add(new Option(`${port.puerto} · ${port.descripcion}`, port.puerto));
      if (ports.some(port => port.puerto === previous)) $('serial-port').value = previous;
      buttons();
    } catch (error) { $('serial-status').textContent = `No se pudieron consultar los puertos. ${error.message}`; }
  }
  async function action(path, body) {
    revision++;
    busy = true; buttons();
    try {
      lastSnapshot = await api(path, body);
      lastResponseAt = performance.now(); failure = null; connected = lastSnapshot.conectado;
      $('reading-source').value = 'serial'; switchSource();
    } catch (error) { failure = error.message; display(); }
    finally { busy = false; buttons(); }
  }
  $('reading-source').onchange = switchSource;
  $('serial-port').onchange = buttons;
  $('serial-refresh').onclick = ports;
  $('serial-connect').onclick = () => action('/api/serie/conectar', { puerto: $('serial-port').value, baudios: Number($('serial-baud').value) });
  $('serial-disconnect').onclick = () => action('/api/serie/desconectar', {});
  async function poll() {
    if (stopped) return;
    if (!busy) {
      const requestRevision = revision;
      try {
        const snapshot = await api('/api/lecturas');
        if (requestRevision === revision) {
          lastSnapshot = snapshot;
          lastResponseAt = performance.now(); failure = null; connected = snapshot.conectado;
        }
      } catch { if (requestRevision === revision) failure = 'Sin comunicación con la aplicación. Reintentando…'; }
      if (!busy && requestRevision === revision) display();
    }
    setTimeout(poll, 1000);
  }
  let freshnessTimer = setInterval(display, 500);
  window.addEventListener('pagehide', () => { stopped = true; clearInterval(freshnessTimer); });
  window.addEventListener('pageshow', event => { if (event.persisted) { stopped = false; freshnessTimer = setInterval(display, 500); poll(); } });
  switchSource(); ports(); poll();
}
