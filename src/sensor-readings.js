export function readingText(reading) {
  if (!reading || reading.value === null) return reading?.source === 'serial' ? 'Sin datos actuales' : 'Sin estimación';
  return `${reading.value.toLocaleString('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${reading.unit}`;
}

export function readingStatus(reading) {
  if (!reading) return 'Sin estimación';
  const status = { below: 'Por debajo del rango declarado', above: 'Por encima del rango declarado', within: 'Dentro del rango declarado', unknown: reading.reason }[reading.state];
  return reading.source === 'serial' && reading.receivedAt ? `${status} · recepción ${new Date(reading.receivedAt).toLocaleTimeString('es-CL')}` : status;
}

export function showSensorReadings(viewport, readings) {
  viewport.simulatedReadings = readings;
  renderSensorReadings(viewport);
}

export function renderSensorReadings(viewport) {
  const readings = viewport.readingSource === 'serial' ? viewport.receivedReadings || {} : viewport.simulatedReadings || {};
  viewport.activeReadings = readings;
  for (const [id, reading] of Object.entries(readings)) {
    const cell = document.getElementById(`sensor-reading-${id}`);
    if (cell) cell.textContent = readingText(reading);
    const status = document.getElementById(`sensor-range-${id}`);
    if (status) status.textContent = readingStatus(reading);
  }
  viewport.dispatchEvent(new Event('sensor-readings'));
}
