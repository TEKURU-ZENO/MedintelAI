import { useEffect, useRef } from "react";

export default function GhostReplay({ points, triggerIndex }: any) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    if (!points || points.length === 0) return;

    const ctx = canvasRef.current!.getContext("2d")!;
    ctx.clearRect(0, 0, 400, 400);

    let i = 0;

    function animate() {
      if (i >= points.length - 1) return;

      const p1 = points[i];
      const p2 = points[i + 1];

      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.strokeStyle = "rgba(14, 165, 233, 0.4)"; // light sky blue ghost trail
      ctx.lineWidth = 14; // Matches the 12px user brush slightly larger
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      
      // Magic glow
      ctx.shadowBlur = 8;
      ctx.shadowColor = "rgba(14, 165, 233, 0.6)";

      ctx.stroke();

      i++;
      // Reset shadow
      ctx.shadowBlur = 0;
      
      animationRef.current = requestAnimationFrame(animate);
    }

    animate();

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [points, triggerIndex]); // triggerIndex is an arbitrary number to force replay

  return (
    <canvas
      ref={canvasRef}
      width={400}
      height={400}
      className="absolute inset-0 w-full h-full pointer-events-none z-10"
    />
  );
}
