export function samplePath(path: string, samples = 120) {
  const svgNS = "http://www.w3.org/2000/svg";
  const pathEl = document.createElementNS(svgNS, "path");
  pathEl.setAttribute("d", path);

  const length = (pathEl as any).getTotalLength();
  const pts = [];

  for (let i = 0; i < samples; i++) {
    const p = (pathEl as any).getPointAtLength((i / (samples - 1)) * length);
    pts.push({ x: p.x, y: p.y }); // still normalized
  }
  return pts;
}
