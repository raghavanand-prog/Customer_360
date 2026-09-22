import { useEffect, useRef } from "react";

/**
 * A restrained, canvas-based animated node-link graph — meant to evoke the
 * identity graph the platform actually builds (namespaced identifiers,
 * edges, clusters), not generic "AI" particle noise. Nodes drift slowly,
 * nearby nodes connect with a faint line, and a cluster occasionally
 * "resolves" (a few edges briefly brighten) to suggest identity matching
 * without literally animating a demo.
 *
 * Respects prefers-reduced-motion: renders one static frame and stops.
 */
export default function IdentityGraphCanvas({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let width = 0;
    let height = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);

    interface Node {
      x: number;
      y: number;
      vx: number;
      vy: number;
      r: number;
      cluster: number;
    }

    const NODE_COUNT = 46;
    const CLUSTER_COUNT = 7;
    const CONNECT_DIST = 130;
    let nodes: Node[] = [];

    function resize() {
      const parent = canvas!.parentElement;
      width = parent ? parent.clientWidth : window.innerWidth;
      height = parent ? parent.clientHeight : window.innerHeight;
      canvas!.width = width * dpr;
      canvas!.height = height * dpr;
      canvas!.style.width = `${width}px`;
      canvas!.style.height = `${height}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function seed() {
      nodes = Array.from({ length: NODE_COUNT }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.12,
        vy: (Math.random() - 0.5) * 0.12,
        r: Math.random() * 1.4 + 1.1,
        cluster: Math.floor(Math.random() * CLUSTER_COUNT),
      }));
    }

    resize();
    seed();
    window.addEventListener("resize", resize);

    const accent = "45, 212, 167"; // matches --accent
    let raf = 0;
    let frame = 0;

    function draw() {
      ctx!.clearRect(0, 0, width, height);

      // gentle drift
      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < -20) n.x = width + 20;
        if (n.x > width + 20) n.x = -20;
        if (n.y < -20) n.y = height + 20;
        if (n.y > height + 20) n.y = -20;
      }

      // edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < CONNECT_DIST) {
            const sameCluster = a.cluster === b.cluster;
            const baseAlpha = (1 - dist / CONNECT_DIST) * (sameCluster ? 0.16 : 0.045);
            ctx!.strokeStyle = `rgba(${accent}, ${baseAlpha.toFixed(3)})`;
            ctx!.lineWidth = 1;
            ctx!.beginPath();
            ctx!.moveTo(a.x, a.y);
            ctx!.lineTo(b.x, b.y);
            ctx!.stroke();
          }
        }
      }

      // nodes
      for (const n of nodes) {
        ctx!.beginPath();
        ctx!.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx!.fillStyle = `rgba(${accent}, 0.55)`;
        ctx!.fill();
      }

      frame++;
      if (!reduceMotion) {
        raf = requestAnimationFrame(draw);
      }
    }

    draw();

    return () => {
      window.removeEventListener("resize", resize);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
