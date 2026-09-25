import { useEffect, useLayoutEffect, useRef, useState } from "react";
import Lenis from "lenis";
import { animate } from "animejs/animation";
import { createTimeline } from "animejs/timeline";
import { onScroll } from "animejs/events";
import { splitText } from "animejs/text";
import { stagger } from "animejs/utils";
import { cubicBezier } from "animejs/easings";

// Motion system for the console. Every animation goes through this module,
// so reduced-motion and viewport-size handling live in one place.
//   - Only transform + opacity are animated (compositor-friendly).
//   - Content already on screen animates immediately; content below the
//     fold animates as it scrolls into view (Anime.js onScroll).
//   - Inline styles are removed when an animation finishes, so elements
//     always end in their plain CSS state.
//   - prefers-reduced-motion: no JS motion, no smooth scroll, no parallax;
//     content renders in its final state immediately.

const REDUCED_QUERY = "(prefers-reduced-motion: reduce)";
const COMPACT_QUERY = "(max-width: 640px)";
const FINE_POINTER_QUERY = "(hover: hover) and (pointer: fine)";

export const EASE_OUT = "outExpo";
/** Slow, silky arrival curve: cubic-bezier(0.16, 1, 0.3, 1). */
export const EASE_SLOW = cubicBezier(0.16, 1, 0.3, 1);

function matches(query: string): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(query).matches;
}

export function prefersReducedMotion(): boolean {
  return matches(REDUCED_QUERY);
}

export function hasFinePointer(): boolean {
  return matches(FINE_POINTER_QUERY);
}

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(prefersReducedMotion);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia(REDUCED_QUERY);
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

// ------------------------------------------------------------ smooth scroll

let lenis: Lenis | null = null;

/** Inertial smooth scrolling for the whole window (skipped for reduced motion). */
export function initSmoothScroll(): () => void {
  if (lenis || prefersReducedMotion()) return () => {};
  lenis = new Lenis({ autoRaf: true, duration: 1.1, smoothWheel: true });
  return () => {
    lenis?.destroy();
    lenis = null;
  };
}

export function scrollToTop() {
  if (lenis) lenis.scrollTo(0, { immediate: true });
  else window.scrollTo(0, 0);
}

export function scrollToElement(el: HTMLElement, offset = -80) {
  if (lenis) lenis.scrollTo(el, { offset, duration: 1.2 });
  else el.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
}

export function lockScroll(locked: boolean) {
  if (lenis) {
    if (locked) lenis.stop();
    else lenis.start();
  }
  document.body.style.overflow = locked ? "hidden" : "";
}

/**
 * Scroll parallax: `[data-parallax="0.3"]` elements drift at 30% of scroll
 * speed; `data-parallax-fade` also fades them out over the first 320px.
 * Used on page headers so titles ease away as content scrolls over them.
 */
export function initParallax(): () => void {
  if (prefersReducedMotion()) return () => {};
  let frame = 0;
  const update = () => {
    frame = 0;
    const y = window.scrollY;
    document.querySelectorAll<HTMLElement>("[data-parallax]").forEach((el) => {
      if (y > 700) return;
      const f = Number(el.dataset.parallax) || 0.3;
      el.style.translate = y > 0 ? `0 ${(y * f).toFixed(1)}px` : "";
      if (el.hasAttribute("data-parallax-fade")) el.style.opacity = y > 0 ? String(Math.max(0, 1 - y / 320)) : "";
    });
  };
  const onScrollEvt = () => {
    if (!frame) frame = requestAnimationFrame(update);
  };
  window.addEventListener("scroll", onScrollEvt, { passive: true });
  return () => {
    window.removeEventListener("scroll", onScrollEvt);
    cancelAnimationFrame(frame);
  };
}

// ------------------------------------------------------------ reveals

type Targets = HTMLElement[];

function clearInline(targets: Targets) {
  for (const el of targets) {
    el.style.opacity = "";
    el.style.transform = "";
    el.style.filter = "";
  }
}

function inView(el: HTMLElement): boolean {
  const r = el.getBoundingClientRect();
  return r.top < window.innerHeight * 0.94 && r.bottom > 0;
}

/**
 * One-shot scroll trigger: runs `play` the first time `target` scrolls into
 * view, then detaches the Anime.js scroll observer. (Linking an animation
 * directly as `autoplay: onScroll(...)` also reverses it when the element
 * scrolls back out, which would hide content again.)
 */
function whenScrolledIntoView(target: HTMLElement, play: () => () => void): () => void {
  let stop: (() => void) | null = null;
  const observer = onScroll({
    target,
    repeat: false,
    onEnter: () => {
      if (stop) return;
      stop = play();
      queueMicrotask(() => observer.revert());
    },
  });
  return () => {
    observer.revert();
    stop?.();
  };
}

// "distance" is the starting blur radius in px: content arrives out of
// focus, very slightly enlarged, and settles sharp — like scent arriving.
function hide(targets: Targets, blur: number) {
  for (const el of targets) {
    el.style.opacity = "0";
    el.style.transform = "scale(1.04)";
    el.style.filter = `blur(${blur}px)`;
  }
}

function blurIn(blur: number) {
  return { opacity: [0, 1], scale: [1.04, 1], filter: [`blur(${blur}px)`, "blur(0px)"] };
}

export interface RevealOptions {
  /** ms between consecutive elements */
  step?: number;
  /** starting blur radius in px */
  distance?: number;
  delay?: number;
  duration?: number;
}

/**
 * Fade + rise a set of elements. Elements already on screen play in a
 * staggered sequence now; elements below the fold each play when they
 * scroll into view. Returns a cleanup that cancels everything and removes
 * every inline style it wrote.
 */
export function reveal(targets: Targets, opts: RevealOptions = {}): () => void {
  if (targets.length === 0 || prefersReducedMotion()) return () => {};
  const compact = matches(COMPACT_QUERY);
  const distance = opts.distance ?? (compact ? 10 : 16);
  const step = opts.step ?? (compact ? 80 : 120);
  const duration = opts.duration ?? 1600;

  const now = targets.filter(inView);
  const later = targets.filter((t) => !now.includes(t));
  // Set start state synchronously (we run in a layout effect, before paint)
  // so there is never a frame of fully visible content first.
  hide(targets, distance);

  const cleanups: (() => void)[] = [];
  if (now.length) {
    const a = animate(now, {
      ...blurIn(distance),
      duration,
      delay: stagger(step, { start: opts.delay ?? 0 }),
      ease: EASE_SLOW,
      onComplete: () => clearInline(now),
    });
    cleanups.push(() => a.cancel());
  }
  for (const el of later) {
    cleanups.push(
      whenScrolledIntoView(el, () => {
        const a = animate(el, {
          ...blurIn(distance),
          duration,
          ease: EASE_SLOW,
          onComplete: () => clearInline([el]),
        });
        return () => a.cancel();
      }),
    );
  }
  return () => {
    cleanups.forEach((c) => c());
    clearInline(targets);
  };
}

function collect(root: HTMLElement | null, selector: string): Targets {
  if (!root) return [];
  return Array.from(root.querySelectorAll<HTMLElement>(selector));
}

/**
 * Staggered entrance for every `[data-reveal]` descendant, fired when `key`
 * changes to a truthy value (typically "data has loaded" or an entity id).
 * Passing a stable key means background refetches don't replay the entrance.
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>(key: unknown, opts: RevealOptions = {}) {
  const ref = useRef<T>(null);
  const { step, distance, delay, duration } = opts;
  useLayoutEffect(() => {
    if (!key) return;
    return reveal(collect(ref.current, "[data-reveal]"), { step, distance, delay, duration });
  }, [key, step, distance, delay, duration]);
  return ref;
}

/**
 * Two-level choreography: sections enter in order, and inside each section
 * its `[data-reveal-item]` children follow slightly behind. Sections on
 * screen play as one timeline; sections further down play as they scroll
 * into view. Used on the Customer 360 page (identity -> behaviour ->
 * transactions -> segments -> intelligence).
 */
export function useStagedReveal<T extends HTMLElement = HTMLDivElement>(key: unknown) {
  const ref = useRef<T>(null);
  useLayoutEffect(() => {
    if (!key || prefersReducedMotion()) return;
    const root = ref.current;
    const sections = collect(root, "[data-stage]");
    if (sections.length === 0) return;
    const compact = matches(COMPACT_QUERY);
    const distance = compact ? 12 : 20;
    const sectionGap = compact ? 160 : 260;
    const items = sections.map((s) => collect(s, "[data-reveal-item]"));
    const visible = sections.map(inView);
    const all = [...sections, ...items.flat()];
    hide(sections, distance);
    hide(items.flat(), distance / 2);

    const cleanups: (() => void)[] = [];
    const tl = createTimeline({ defaults: { duration: 1600, ease: EASE_SLOW } });
    let slot = 0;
    sections.forEach((section, i) => {
      const sectionItems = items[i];
      if (visible[i]) {
        const at = slot++ * sectionGap;
        tl.add(section, blurIn(distance), at);
        if (sectionItems.length) {
          tl.add(sectionItems, { ...blurIn(distance / 2), duration: 1400, delay: stagger(compact ? 70 : 110) }, at + 200);
        }
        return;
      }
      cleanups.push(
        whenScrolledIntoView(section, () => {
          const a = animate(section, {
            ...blurIn(distance),
            duration: 1600,
            ease: EASE_SLOW,
            onComplete: () => clearInline([section]),
          });
          const b = sectionItems.length
            ? animate(sectionItems, {
                ...blurIn(distance / 2),
                duration: 1400,
                ease: EASE_SLOW,
                delay: stagger(compact ? 70 : 110, { start: 200 }),
                onComplete: () => clearInline(sectionItems),
              })
            : null;
          return () => {
            a.cancel();
            b?.cancel();
          };
        }),
      );
    });
    tl.call(() => clearInline(all.filter((el) => el.style.opacity === "1")), slot * sectionGap + 2200);
    return () => {
      tl.cancel();
      cleanups.forEach((c) => c());
      clearInline(all);
    };
  }, [key]);
  return ref;
}

/**
 * Headline reveal: splits the element's text into letters (Anime.js
 * splitText) and brings each one in from a soft blur, 40ms apart. The split
 * is reverted when the animation finishes, so the DOM React owns is
 * restored exactly.
 */
export function useSplitReveal<T extends HTMLElement = HTMLElement>(delay = 0) {
  const ref = useRef<T>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) return;
    const split = splitText(el, { chars: true });
    const chars = split.chars as HTMLElement[];
    if (chars.length === 0) {
      split.revert();
      return;
    }
    for (const c of chars) {
      c.style.opacity = "0";
      c.style.filter = "blur(12px)";
    }
    let reverted = false;
    const finish = () => {
      if (reverted) return;
      reverted = true;
      split.revert();
    };
    const anim = animate(chars, {
      opacity: [0, 1],
      filter: ["blur(12px)", "blur(0px)"],
      duration: 1400,
      delay: stagger(40, { start: delay }),
      ease: EASE_SLOW,
      onComplete: finish,
    });
    return () => {
      anim.cancel();
      finish();
    };
  }, [delay]);
  return ref;
}

/** A hairline divider that draws outward from its centre (scaleX 0 -> 1). */
export function useHairline<T extends HTMLElement = HTMLElement>(key: unknown, delay = 0) {
  const ref = useRef<T>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || !key || prefersReducedMotion()) return;
    el.style.transform = "scaleX(0)";
    const run = () => {
      const a = animate(el, {
        scaleX: [0, 1],
        duration: 1600,
        delay,
        ease: EASE_SLOW,
        onComplete: () => {
          el.style.transform = "";
        },
      });
      return () => a.cancel();
    };
    const stop = inView(el) ? run() : whenScrolledIntoView(el, run);
    return () => {
      stop();
      el.style.transform = "";
    };
  }, [key, delay]);
  return ref;
}

// ------------------------------------------------------------ numbers & bars

/**
 * Counts a number up from zero once, on first render with a value. The
 * final formatted value is rendered by React from the start (so screen
 * readers, copy/paste, and reduced-motion users always get the real number);
 * the animation only temporarily rewrites the visible text.
 */
export function useCountUp(value: number | null | undefined, format: (n: number) => string, duration = 1100) {
  const ref = useRef<HTMLSpanElement>(null);
  const played = useRef(false);
  useEffect(
    () => () => {
      played.current = false;
    },
    [],
  );
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || value === null || value === undefined || !Number.isFinite(value)) return;
    const write = (text: string) => {
      const node = el.firstChild;
      if (node && node.nodeType === Node.TEXT_NODE) node.nodeValue = text;
      else el.textContent = text;
    };
    const final = format(value);
    // Later value changes (e.g. a background refetch) snap to the new number
    // rather than replaying the count from zero.
    if (played.current || prefersReducedMotion()) {
      played.current = true;
      write(final);
      return;
    }
    played.current = true;
    const state = { n: 0 };
    write(format(0));
    const anim = animate(state, {
      n: value,
      duration,
      ease: "outExpo",
      onUpdate: () => write(format(state.n)),
      onComplete: () => write(final),
    });
    return () => {
      anim.cancel();
    };
  }, [value, format, duration]);
  return ref;
}

/** Grow a meter bar (scaleX, transform-only) from 0 to its CSS width. */
export function useMeter(key: unknown) {
  const ref = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || key === null || key === undefined || prefersReducedMotion()) return;
    el.style.transform = "scaleX(0)";
    const anim = animate(el, {
      scaleX: [0, 1],
      duration: 1800,
      delay: 300,
      ease: EASE_SLOW,
      onComplete: () => {
        el.style.transform = "";
      },
    });
    return () => {
      anim.cancel();
      el.style.transform = "";
    };
  }, [key]);
  return ref;
}

/** Slide a single indicator element to a y-offset (sidebar active marker). */
export function slideTo(el: HTMLElement, y: number, height: number, instant: boolean) {
  el.style.height = `${height}px`;
  if (instant || prefersReducedMotion()) {
    el.style.transform = `translateY(${y}px)`;
    el.style.opacity = "1";
    return;
  }
  animate(el, { translateY: y, opacity: 1, duration: 650, ease: "outElastic(1, .75)" });
}
