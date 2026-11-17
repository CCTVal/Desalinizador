// Steady-state scenario. Instrument ranges describe validity, never clamp the process.
export function rangeState(value, range) {
  if (!Number.isFinite(value)) return 'unknown';
  if (value < range.min) return 'below';
  if (value > range.max) return 'above';
  return 'within';
}

// Nominal IEC platinum curve (NI / BIPM); lead-wire errors are not modelled.
export function pt100Resistance(temperatureC) {
  if (!Number.isFinite(temperatureC) || temperatureC < -200 || temperatureC > 850) return null;
  const t = temperatureC;
  return 100 * (1 + 3.9083e-3 * t - 5.775e-7 * t * t + (t < 0 ? -4.183e-12 * (t - 100) * t ** 3 : 0));
}

export function waterTemperature(flowLMin, inletC, heatW, density, cp) {
  if (![flowLMin, inletC, heatW, density, cp].every(Number.isFinite) || flowLMin <= 0 || density <= 0 || cp <= 0) return null;
  // No phase-change model: restrict this water scenario to 0–100 °C, not the RTD range.
  if (inletC <= 0 || inletC >= 100) return null;
  const temperature = inletC + heatW / (density * flowLMin / 60000 * cp);
  return temperature > 0 && temperature < 100 ? temperature : null;
}

export function simulateSensors(result, settings, pump, scenario, equipment) {
  const readings = {};
  const operating = result.state === 'operating';
  const stopped = ['off', 'zero_speed', 'closed'].includes(result.state);
  const { waterDensityKgM3: rho, gravityMS2: g, sprayCircuit } = pump.assumptions;
  const totalLength = scenario.colectorCotaM - scenario.subidaInicioCotaM + scenario.colectorLongitudM;
  for (const instrument of equipment.equipos) {
    if (!['manometro', 'sensor_presion', 'sensor_flujo', 'sensor_temperatura'].includes(instrument.id)) continue;
    for (const id of instrument.piezas_cad_asociadas) {
      let value = null, reason = 'Sin punto de trabajo válido';
      if (['manometro', 'sensor_presion'].includes(instrument.id)) {
        const tap = scenario.tomas[id];
        if (operating && tap && Number.isFinite(result.nodeHeadM) && Number.isFinite(result.flowM3h)) {
          // Bernoulli from the nozzle upstream; equal velocity heads are assumed to cancel.
          // Common K is distributed along the delivery pipe; valve loss stays upstream.
          const remaining = scenario.colectorCotaM - tap.cotaM + scenario.colectorLongitudM;
          const lossHead = sprayCircuit.commonLossFraction * settings.lossAt1M3h * result.flowM3h ** 2 * remaining / totalLength;
          value = rho * g * (result.nodeHeadM + scenario.salidaAspersorCotaM - tap.cotaM + lossHead) / 100000;
          reason = 'Presión local estimada · cota CAD y pérdidas supuestas';
        } else if (stopped) reason = 'Presión residual desconocida; sin modelo estático';
      } else if (instrument.id === 'sensor_flujo') {
        value = operating ? result.flowLMin : stopped ? 0 : null;
        reason = 'Caudal común antes de la bifurcación';
      } else if (instrument.id === 'sensor_temperatura') {
        value = operating ? waterTemperature(result.flowLMin, settings.inletTemperatureC, settings.heatToWaterW, rho, scenario.calorEspecificoJKgK) : null;
        reason = operating ? (value === null ? 'Revisa el escenario térmico: solo agua entre 0 y 100 °C' : 'Balance térmico estacionario · entrada y calor supuestos') : 'Sin flujo: temperatura no calculada';
      }
      if (result.state === 'disconnected') reason = 'Circuito desconectado';
      if (result.state === 'invalid') reason = 'Revisa los valores del circuito';
      const state = rangeState(value, instrument.rango_declarado);
      readings[id] = { value, unit: instrument.rango_declarado.unidad, state, reason };
      if (instrument.id === 'sensor_temperatura') readings[id].resistanceOhm = pt100Resistance(value);
    }
  }
  return readings;
}
