import { useRef, useState, useEffect } from "react";
import GhostReplay from "./GhostReplay";
import { DIFFICULTY } from "../data/difficulty";

type Point = { x: number; y: number; t?: number };
type Stroke = Point[];

const W = 400;
const H = 400;
const GRID_SIZE = 20;

function distance(p1: Point, p2: Point) {
  return Math.hypot(p1.x - p2.x, p1.y - p2.y);
}

function getDirection(p1: Point, p2: Point) {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const len = Math.hypot(dx, dy) || 1;
  return { dx: dx / len, dy: dy / len };
}

function dotProduct(v1: {dx: number, dy: number}, v2: {dx: number, dy: number}) {
  return v1.dx * v2.dx + v1.dy * v2.dy;
}

export default function TracingCanvas({ letter, level = "beginner", onSubmit }: any) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const currentStroke = useRef<Stroke>([]);
  const [drawing, setDrawing] = useState(false);
  
  const cfg = DIFFICULTY[level] || DIFFICULTY["beginner"];
  
  // Real-time coaching state
  const prevDistRef = useRef(0);
  const prevColorRef = useRef("#22c55e");
  const hintRef = useRef("Follow the dotted path 👆");
  const [hint, setHint] = useState(hintRef.current);
  const [replayTrigger, setReplayTrigger] = useState(0);

  // Expected points un-bucketed for direction calculation
  const expectedPointsRef = useRef<Point[]>([]);

  // Spatial Bucketing Grid
  const grid = useRef(new Map<string, Point[]>());

  useEffect(() => {
    const ctx = canvasRef.current!.getContext("2d")!;
    ctx.fillStyle = "transparent";
    ctx.clearRect(0, 0, W, H);
    setStrokes([]);
    setHint("Follow the dotted path 👆");
    hintRef.current = "Follow the dotted path 👆";

    // Build spatial grid and ordered list for current letter
    const g = new Map<string, Point[]>();
    const scaledList: Point[] = [];

    letter.points.forEach((p: any) => {
      const scaledP = { x: p.x * W, y: p.y * H };
      scaledList.push(scaledP);

      const key = `${Math.floor(scaledP.x / GRID_SIZE)}-${Math.floor(scaledP.y / GRID_SIZE)}`;
      if (!g.has(key)) g.set(key, []);
      g.get(key)!.push(scaledP);
    });

    grid.current = g;
    expectedPointsRef.current = scaledList;
    setReplayTrigger(prev => prev + 1); // trigger ghost on letter switch
  }, [letter]);

  const getNearbyPoints = (point: Point) => {
    const gx = Math.floor(point.x / GRID_SIZE);
    const gy = Math.floor(point.y / GRID_SIZE);
    const candidates: Point[] = [];

    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        const key = `${gx + dx}-${gy + dy}`;
        if (grid.current.has(key)) {
          candidates.push(...grid.current.get(key)!);
        }
      }
    }
    return candidates;
  };

  const getPos = (e: React.PointerEvent) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      t: Date.now(),
    };
  };

  const start = (e: React.PointerEvent) => {
    setDrawing(true);
    currentStroke.current = [getPos(e)];
    prevDistRef.current = 0; 
  };

  const draw = (e: React.PointerEvent) => {
    if (!drawing) return;

    const ctx = canvasRef.current!.getContext("2d")!;
    const p = getPos(e);
    const last = currentStroke.current.at(-1)!;

    // Nearest neighbor via Spatial Bucketing
    const nearby = getNearbyPoints(p);
    let nearest = nearby[0];
    
    if (nearby.length > 0) {
      nearest = nearby.reduce((prev, curr) =>
        distance(curr, p) < distance(prev, p) ? curr : prev
      );
    }

    const rawDist = nearest ? distance(p, nearest) : 50;

    // Smoothing
    const dist = cfg.smoothing * prevDistRef.current + (1 - cfg.smoothing) * rawDist;
    prevDistRef.current = dist;

    // Stroke Direction Logic
    let isReversing = false;
    if (nearest && expectedPointsRef.current.length > 1 && distance(last, p) > 2) {
        const userDir = getDirection(last, p);
        const idx = expectedPointsRef.current.indexOf(nearest);
        // Look a few points ahead to get the expected path flow
        const next = expectedPointsRef.current[Math.min(idx + 3, expectedPointsRef.current.length - 1)];
        const expectedDir = getDirection(nearest, next);
        
        const alignment = dotProduct(userDir, expectedDir);
        if (alignment < cfg.directionTolerance) { 
            isReversing = true;
        }
    }

    // Hysteresis Color Logic
    let newColor = "#ef4444"; // red (too far)
    if (isReversing) newColor = "#f97316"; // orange (wrong way)
    else if (dist < cfg.green) newColor = "#22c55e"; // green
    else if (dist < cfg.yellow) newColor = "#facc15"; // yellow

    // Prevent rapid switching (only if not reversing)
    if (!isReversing) {
        if (prevColorRef.current === "#22c55e" && dist < cfg.green + 5) {
            newColor = "#22c55e";
        } else if (prevColorRef.current === "#facc15" && dist < cfg.yellow + 5 && dist >= cfg.green - 5) {
            newColor = "#facc15";
        }
    }

    prevColorRef.current = newColor;

    // Hint Logic (Throttled)
    let newHint = "Follow the dotted path 👆";
    if (isReversing) newHint = "Try going the other way 👉";
    else if (dist < cfg.green) newHint = "Perfect! ✨";
    else if (dist < cfg.yellow) newHint = "Stay on the line 👍";

    if (newHint !== hintRef.current) {
      hintRef.current = newHint;
      // Only show hints vigorously on lower levels
      if (level !== "advanced" || isReversing) {
          requestAnimationFrame(() => {
            setHint(newHint);
          });
      }
    }

    // Draw Line
    ctx.beginPath();
    ctx.moveTo(last.x, last.y);
    ctx.lineTo(p.x, p.y);
    ctx.lineWidth = cfg.lineWidth;
    ctx.lineCap = "round";
    ctx.strokeStyle = newColor;
    
    // Dynamic glow
    ctx.shadowBlur = level === "beginner" ? 12 : 5;
    ctx.shadowColor = newColor;

    ctx.stroke();
    
    ctx.shadowBlur = 0;

    currentStroke.current.push(p);
  };

  const end = () => {
    if (!drawing) return;
    setDrawing(false);
    if (currentStroke.current.length > 0) {
        setStrokes((prev) => [...prev, currentStroke.current]);
    }
  };

  const clear = () => {
    const ctx = canvasRef.current!.getContext("2d")!;
    ctx.clearRect(0, 0, W, H);
    setStrokes([]);
    setHint("Follow the dotted path 👆");
    hintRef.current = "Follow the dotted path 👆";
  };

  const triggerReplay = () => {
    setReplayTrigger(prev => prev + 1);
  };

  const submit = () => {
    const exportCanvas = document.createElement("canvas");
    exportCanvas.width = W;
    exportCanvas.height = H;
    const eCtx = exportCanvas.getContext("2d")!;
    eCtx.fillStyle = "white";
    eCtx.fillRect(0, 0, W, H);
    eCtx.drawImage(canvasRef.current!, 0, 0);

    const base64 = exportCanvas.toDataURL("image/png");

    onSubmit({
      base64_image: base64.split(",")[1],
      strokes,
      letter: letter.char,
    });
  };

  return (
    <div className="space-y-6 flex flex-col items-center">
      
      {/* Real-Time Hint Banner */}
      <div className="h-8 flex items-center justify-center transition-all duration-300">
        <p className={`text-lg font-bold animate-pulse ${
            hint.includes("other way") ? "text-orange-500" : "text-sky-600"
        }`}>
            {hint}
        </p>
      </div>

      <div className="relative w-[400px] h-[400px] bg-white rounded-xl shadow-inner border-4 border-dashed border-sky-300 overflow-hidden">
        
        {/* SVG Overlay */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20" viewBox="0 0 1 1">
          <path
            d={letter.path}
            stroke="black"
            strokeWidth="0.04"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            strokeDasharray="0.06, 0.06"
          />
        </svg>

        {/* Ghost Replay Animation Layer */}
        <GhostReplay points={expectedPointsRef.current} triggerIndex={replayTrigger} />

        {/* Drawing Canvas */}
        <canvas
          ref={canvasRef}
          width={W}
          height={H}
          className="absolute inset-0 w-full h-full touch-none cursor-crosshair z-20"
          onPointerDown={start}
          onPointerMove={draw}
          onPointerUp={end}
          onPointerLeave={end}
        />
      </div>

      <div className="flex gap-4">
        <button 
            onClick={triggerReplay} 
            className="px-6 py-2 font-bold text-sky-700 bg-sky-100 hover:bg-sky-200 border-2 border-sky-200 rounded-full transition-colors shadow-sm"
        >
          Show me how ✨
        </button>
        <button 
            onClick={clear} 
            className="px-6 py-2 font-semibold text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-full transition-colors shadow-sm"
        >
          Reset
        </button>
        <button 
            onClick={submit} 
            className="px-6 py-2 font-semibold text-white bg-green-500 hover:bg-green-600 rounded-full transition-colors shadow-md"
        >
          Done
        </button>
      </div>
    </div>
  );
}
