import { useRef, useState, useEffect } from "react";

type Point = { x: number; y: number; t: number };
type Stroke = Point[];

export default function CanvasBoard({ onSubmit }: any) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [drawing, setDrawing] = useState(false);
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const currentStroke = useRef<Stroke>([]);

  // Initialize white background so the base64 isn't transparent
  useEffect(() => {
    const ctx = getCtx();
    if (ctx) {
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, 500, 400);
    }
  }, []);

  const getCtx = () => canvasRef.current?.getContext("2d");

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
    const point = getPos(e);
    currentStroke.current = [point];
  };

  const draw = (e: React.PointerEvent) => {
    if (!drawing) return;

    const ctx = getCtx();
    const point = getPos(e);

    const last = currentStroke.current[currentStroke.current.length - 1];

    ctx?.beginPath();
    ctx?.moveTo(last.x, last.y);
    ctx?.lineTo(point.x, point.y);
    ctx!.lineWidth = 3;
    ctx!.lineCap = "round";
    ctx!.strokeStyle = "black";
    ctx!.stroke();

    currentStroke.current.push(point);
  };

  const end = () => {
    if (!drawing) return;

    setDrawing(false);
    if (currentStroke.current.length > 0) {
        setStrokes((prev) => [...prev, currentStroke.current]);
    }
  };

  const clear = () => {
    const ctx = getCtx();
    if (ctx) {
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, 500, 400);
    }
    setStrokes([]);
  };

  const handleSubmit = () => {
    const canvas = canvasRef.current!;
    const base64 = canvas.toDataURL("image/png");

    onSubmit({
      base64_image: base64.split(",")[1],
      strokes,
    });
  };

  return (
    <div className="space-y-4">
      <div className="border-4 border-dashed border-gray-300 rounded-xl overflow-hidden bg-white shadow-inner flex justify-center w-fit">
        <canvas
          ref={canvasRef}
          width={500}
          height={400}
          className="touch-none cursor-crosshair"
          onPointerDown={start}
          onPointerMove={draw}
          onPointerUp={end}
          onPointerLeave={end}
        />
      </div>

      <div className="flex gap-4">
        <button 
            onClick={clear} 
            className="px-6 py-2 font-semibold text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-full transition-colors shadow-sm"
        >
          Erase All
        </button>
        <button 
            onClick={handleSubmit} 
            className="px-6 py-2 font-semibold text-white bg-green-500 hover:bg-green-600 rounded-full transition-colors shadow-md"
        >
          I'm Done! ✨
        </button>
      </div>
    </div>
  );
}
