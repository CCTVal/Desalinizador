// Q is m³/h and H is m of water. Never extrapolate the manufacturer's table.
export function pumpHead(curve, flow, speedRatio = 1) {
  if (!(speedRatio > 0)) return null;
  const nominalFlow = flow / speedRatio;
  if (nominalFlow < curve[0][0] - 1e-10 || nominalFlow > curve.at(-1)[0] + 1e-10) return null;
  for (let i = 1; i < curve.length; i++) {
    if (nominalFlow <= curve[i][0] + 1e-10) {
      const [q0, h0] = curve[i - 1], [q1, h1] = curve[i];
      return (h0 + (h1 - h0) * (nominalFlow - q0) / (q1 - q0)) * speedRatio ** 2;
    }
  }
  return curve.at(-1)[1] * speedRatio ** 2;
}

export function branchFlows(nodeHeadM, bypassOpen, network) {
  return {
    sprayM3h: Math.sqrt(Math.max(0, nodeHeadM) / network.nozzleResistanceMPerM3hSquared),
    bypassM3h: bypassOpen ? Math.sqrt(Math.max(0, nodeHeadM + network.bypassOutletDropM) / network.bypassResistanceMPerM3hSquared) : 0,
  };
}

export function systemHead(flow, { staticHeadM, lossAt1M3h, openingPercent, bypassOpen }, config) {
  const aperture = openingPercent / 100;
  if (!(aperture > 0)) return null;
  const valveLoss = config.assumptions.valveLossCoefficient * (1 / aperture ** 2 - 1);
  if (typeof bypassOpen === 'boolean') {
    const network = config.assumptions.sprayCircuit;
    let lower = bypassOpen ? -network.bypassOutletDropM : 0;
    let upper = network.nozzleResistanceMPerM3hSquared * flow ** 2;
    // Both outlets share one junction pressure; their flows sum to the pump flow.
    for (let i = 0; i < 48; i++) {
      const middle = (lower + upper) / 2;
      const branches = branchFlows(middle, bypassOpen, network);
      if (branches.sprayM3h + branches.bypassM3h < flow) lower = middle;
      else upper = middle;
    }
    return staticHeadM + (network.commonLossFraction * lossAt1M3h + valveLoss) * flow ** 2 + (lower + upper) / 2;
  }
  return staticHeadM + (lossAt1M3h + valveLoss) * flow ** 2;
}

export function solvePump(config, settings) {
  const { running, connected, frequencyHz, openingPercent, staticHeadM, lossAt1M3h } = settings;
  if (![frequencyHz, openingPercent, staticHeadM, lossAt1M3h].every(Number.isFinite) || frequencyHz < 0 || frequencyHz > config.nominalFrequencyHz || openingPercent < 0 || openingPercent > 100 || staticHeadM < 0 || lossAt1M3h < 0) {
    return { state: 'invalid', flowLMin: null, headM: null, pressureBar: null, hydraulicPowerKw: null, shaftReferenceKw: null };
  }
  const ratio = frequencyHz / config.nominalFrequencyHz;
  const shaftReferenceKw = config.nominalMotorPowerKw * ratio ** 3;
  if (!connected || !running || ratio === 0) {
    return { state: !connected ? 'disconnected' : !running ? 'off' : 'zero_speed', flowLMin: 0, flowM3h: 0, headM: 0, pressureBar: 0, hydraulicPowerKw: 0, shaftReferenceKw: 0 };
  }
  if (openingPercent === 0) {
    return { state: 'closed', flowLMin: 0, flowM3h: 0, headM: null, pressureBar: null, hydraulicPowerKw: 0, shaftReferenceKw };
  }
  let lower = config.curve50Hz[0][0] * ratio;
  let upper = config.curve50Hz.at(-1)[0] * ratio;
  const difference = q => pumpHead(config.curve50Hz, q, ratio) - systemHead(q, settings, config);
  // A non-bracketed duty point is unknown, not zero flow or a guessed shutoff head.
  if (difference(lower) < 0 || difference(upper) > 0) {
    return { state: 'outside_curve', flowLMin: null, flowM3h: null, headM: null, pressureBar: null, hydraulicPowerKw: null, shaftReferenceKw };
  }
  for (let i = 0; i < 60; i++) {
    const middle = (lower + upper) / 2;
    if (difference(middle) > 0) lower = middle;
    else upper = middle;
  }
  const flowM3h = (lower + upper) / 2;
  const headM = pumpHead(config.curve50Hz, flowM3h, ratio);
  const pressurePa = config.assumptions.waterDensityKgM3 * config.assumptions.gravityMS2 * headM;
  let branchResult = {};
  if (typeof settings.bypassOpen === 'boolean') {
    const network = config.assumptions.sprayCircuit;
    const valveLoss = config.assumptions.valveLossCoefficient * (1 / (openingPercent / 100) ** 2 - 1);
    const nodeHeadM = headM - staticHeadM - (network.commonLossFraction * lossAt1M3h + valveLoss) * flowM3h ** 2;
    const branches = branchFlows(nodeHeadM, settings.bypassOpen, network);
    branchResult = {
      nodeHeadM,
      sprayFlowLMin: branches.sprayM3h * 1000 / 60,
      bypassFlowLMin: branches.bypassM3h * 1000 / 60,
      sprayPressureBar: Math.max(0, nodeHeadM) * config.assumptions.waterDensityKgM3 * config.assumptions.gravityMS2 / 100000,
    };
  }
  return {
    ...branchResult,
    state: 'operating', flowM3h, flowLMin: flowM3h * 1000 / 60, headM,
    pressureBar: pressurePa / 100000,
    hydraulicPowerKw: pressurePa * (flowM3h / 3600) / 1000,
    shaftReferenceKw,
  };
}
