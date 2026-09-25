import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ElementType } from "react";
import { animate } from "animejs/animation";
import { createTimeline } from "animejs/timeline";
import { stagger } from "animejs/utils";
import { EASE_SLOW, hasFinePointer, lockScroll, prefersReducedMotion, useSplitReveal } from "../lib/motion";

/** A heading whose words slide up from behind a mask on mount. */
export function SplitHeading({
  text,
  as: Tag = "h1",
  className = "",
  delay = 0,
}: {
  text: string;
  as?: ElementType;
  className?: string;
  delay?: number;
}) {
  const ref = useSplitReveal<HTMLElement>(delay);
  return (
    <Tag ref={ref} className={className}>
      {text}
    </Tag>
  );
}

const INTRO_KEY = "c360_intro_seen";

/**
 * Branded opening sequence, shown once per browser session: the mark
 * scales in, the wordmark letters rise, a progress line draws, then the
 * curtain lifts to reveal the app. Click or any key skips it; reduced
 * motion never shows it.
 */
export function IntroSequence() {
  const [show, setShow] = useState(() => {
    if (prefersReducedMotion()) return false;
    try {
      return sessionStorage.getItem(INTRO_KEY) !== "1";
    } catch {
      return false;
    }
  });
  const rootRef = useRef<HTMLDivElement>(null);
  const skipRef = useRef<() => void>(() => {});

  useLayoutEffect(() => {
    if (!show) return;
    const root = rootRef.current;
    if (!root) return;
    try {
      sessionStorage.setItem(INTRO_KEY, "1");
    } catch {
      // storage unavailable: the intro just shows again next load
    }
    lockScroll(true);
    const q = (s: string) => Array.from(root.querySelectorAll<HTMLElement>(s));
    const mark = q("[data-intro-mark]");
    const chars = q("[data-intro-char]");
    const tagline = q("[data-intro-tagline]");
    const line = q("[data-intro-line]");
    const content = q("[data-intro-content]");

    const done = () => {
      lockScroll(false);
      setShow(false);
    };
    const tl = createTimeline({ defaults: { ease: EASE_SLOW }, onComplete: done });
    tl.add(mark, { opacity: [0, 1], filter: ["blur(20px)", "blur(0px)"], scale: [1.04, 1], duration: 1600 }, 0)
      .add(chars, { opacity: [0, 1], filter: ["blur(16px)", "blur(0px)"], duration: 1400, delay: stagger(40) }, 200)
      .add(line, { scaleX: [0, 1], duration: 1600 }, 700)
      .add(tagline, { opacity: [0, 1], filter: ["blur(10px)", "blur(0px)"], duration: 1400 }, 900)
      .add(content, { opacity: [1, 0], filter: ["blur(0px)", "blur(12px)"], duration: 900, ease: "inQuad" }, 2600)
      .add(root, { opacity: [1, 0], duration: 900, ease: "inOutQuad" }, 3000);

    skipRef.current = () => {
      tl.cancel();
      animate(root, { opacity: [1, 0], duration: 250, ease: "outQuad", onComplete: done });
    };
    const onKey = () => skipRef.current();
    window.addEventListener("keydown", onKey, { once: true });
    return () => {
      tl.cancel();
      window.removeEventListener("keydown", onKey);
      lockScroll(false);
    };
  }, [show]);

  if (!show) return null;
  const word = "Customer360";
  return (
    <div
      ref={rootRef}
      onClick={() => skipRef.current()}
      className="fixed inset-0 z-[100] bg-surface flex items-center justify-center cursor-pointer"
      aria-hidden="true"
    >
      <div className="light-leak -top-[200px] -left-[300px]" />
      <div data-intro-content className="relative flex flex-col items-center px-6 text-center">
        <div data-intro-mark className="h-12 w-12 rounded-full border border-accent/50 flex items-center justify-center" style={{ opacity: 0 }}>
          <div className="h-2.5 w-2.5 rounded-full bg-accent" />
        </div>
        <div className="mt-10 flex font-display uppercase text-ink text-[clamp(44px,9vw,120px)] leading-[0.9] tracking-[0.04em]" aria-hidden="true">
          {word.split("").map((c, i) => (
            <span key={i} data-intro-char className="inline-block" style={{ opacity: 0 }}>
              {c}
            </span>
          ))}
        </div>
        <div className="mt-8 h-px w-56">
          <div data-intro-line className="hairline" style={{ transform: "scaleX(0)" }} />
        </div>
        <div data-intro-tagline className="mt-6 font-serif italic font-light text-xl sm:text-2xl text-accent" style={{ opacity: 0 }}>
          One customer, assembled from many sources.
        </div>
        <div className="mt-10 text-[10.5px] uppercase tracking-[0.3em] text-ink-faint">Click to skip</div>
      </div>
    </div>
  );
}

const INTERACTIVE = 'a, button, [role="button"], tr.row-link, summary, label[for], select';
const TEXT_INPUT = 'input:not([type="checkbox"]):not([type="radio"]):not([type="submit"]), textarea, [contenteditable="true"]';
const MAGNETIC = ".btn-primary, .btn-accent-soft, [data-magnetic]";

/**
 * Pointer effects for mouse/trackpad users (never on touch, never with
 * reduced motion):
 *  - a trailing ring + dot that follow the pointer and swell over anything
 *    clickable (the native cursor stays visible, so nothing gets harder to use);
 *  - magnetic primary buttons that lean toward the pointer;
 *  - a soft accent spotlight that tracks the pointer across cards.
 */
export function CursorEffects() {
  const [enabled] = useState(() => hasFinePointer() && !prefersReducedMotion());
  const ringRef = useRef<HTMLDivElement>(null);
  const dotRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!enabled) return;
    const ring = ringRef.current!;
    const dot = dotRef.current!;
    const target = { x: -100, y: -100 };
    const ringPos = { x: -100, y: -100 };
    let frame = 0;
    let magnet: HTMLElement | null = null;

    const tick = () => {
      ringPos.x += (target.x - ringPos.x) * 0.18;
      ringPos.y += (target.y - ringPos.y) * 0.18;
      ring.style.translate = `${ringPos.x}px ${ringPos.y}px`;
      dot.style.translate = `${target.x}px ${target.y}px`;
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);

    const releaseMagnet = () => {
      if (magnet) magnet.style.translate = "";
      magnet = null;
    };

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      target.x = e.clientX;
      target.y = e.clientY;
      document.documentElement.dataset.cursor = "on";
      const el = e.target instanceof Element ? e.target : null;

      const card = el?.closest<HTMLElement>(".card, .card-interactive");
      if (card) {
        const r = card.getBoundingClientRect();
        card.style.setProperty("--mx", `${e.clientX - r.left}px`);
        card.style.setProperty("--my", `${e.clientY - r.top}px`);
      }

      const m = el?.closest<HTMLElement>(MAGNETIC) ?? null;
      if (m !== magnet) releaseMagnet();
      if (m && !(m as HTMLButtonElement).disabled) {
        magnet = m;
        const r = m.getBoundingClientRect();
        const dx = (e.clientX - (r.left + r.width / 2)) * 0.25;
        const dy = (e.clientY - (r.top + r.height / 2)) * 0.35;
        m.style.translate = `${Math.max(-8, Math.min(8, dx))}px ${Math.max(-6, Math.min(6, dy))}px`;
      }

      const state = el?.closest(TEXT_INPUT) ? "text" : el?.closest(INTERACTIVE) ? "hover" : "idle";
      ring.dataset.state = state;
      dot.dataset.state = state;
    };
    const onLeave = () => {
      document.documentElement.dataset.cursor = "off";
      releaseMagnet();
    };
    const onDown = () => ring.setAttribute("data-pressed", "");
    const onUp = () => ring.removeAttribute("data-pressed");

    document.addEventListener("pointermove", onMove, { passive: true });
    document.documentElement.addEventListener("pointerleave", onLeave);
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("pointerup", onUp);
    return () => {
      cancelAnimationFrame(frame);
      releaseMagnet();
      document.removeEventListener("pointermove", onMove);
      document.documentElement.removeEventListener("pointerleave", onLeave);
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("pointerup", onUp);
      delete document.documentElement.dataset.cursor;
    };
  }, [enabled]);

  if (!enabled) return null;
  return (
    <>
      <div ref={ringRef} className="cursor-ring" aria-hidden="true" />
      <div ref={dotRef} className="cursor-dot" aria-hidden="true" />
    </>
  );
}

/** Thin accent bar that sweeps across the top on every route change. */
export function RouteProgress({ routeKey }: { routeKey: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (first.current) {
      first.current = false;
      return;
    }
    if (prefersReducedMotion()) return;
    const tl = createTimeline({ defaults: { ease: EASE_SLOW } });
    tl.add(el, { opacity: [1, 1], scaleX: [0, 1], duration: 900 }, 0).add(el, { opacity: [1, 0], duration: 400, ease: "outQuad" }, 650);
    return () => {
      tl.cancel();
      el.style.opacity = "0";
    };
  }, [routeKey]);
  return <div ref={ref} className="fixed top-0 left-0 right-0 h-0.5 z-50 bg-accent/80 origin-left pointer-events-none" style={{ opacity: 0 }} aria-hidden="true" />;
}
