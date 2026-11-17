export const PORT_TOLERANCE_M = .001;

export function connectionRoute(points) {
  // Mated ports coincide: discard duplicate points, never bridge their gap.
  return points.filter((point, index) => index === 0 || Math.hypot(...point.map((value, axis) => value - points[index - 1][axis])) > 1e-8);
}

export function portGap(source, destination) {
  return Math.hypot(...source.map((value, axis) => value - destination[axis]));
}
