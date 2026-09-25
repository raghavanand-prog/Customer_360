import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { animate } from "animejs/animation";
import { createTimeline } from "animejs/timeline";
import { stagger } from "animejs/utils";

// Motion rules for the console. Every animation goes through this module,
// so reduced-motion and viewport-size handling live in one place.
//   - Only transform + opacity are animated (compositor-friendly).
//   - Motion explains hierarchy/state (entrances, selection, results arriving);
//     nothing loops except explicit in-progress indicators (CSS).
//   - prefers-reduced-motion: no JS motion at all; content renders in its
//     final state immediately.
//   - Narrow viewports get shorter distances and tighter staggers.

const REDUCED_QUERY = "(prefers-reduced-motion: reduce)";
const COMPACT_QUERY = "(max-width: 640px)";

export const EASE_OUT = "outQuart";

function matches(query: string): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(query).matches;
}

export function prefersReducedMotion(): boolean {
  return matches(REDUCED_QUERY);
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

type Targets = HTMLElement[];

function clearInline(targets: Targets) {
  for (const el of targets) {
    el.style.opacity = "";
    el.style.transform = "";
  }
}

export interface RevealOptions {
  /** ms between consecutive elements */
  step?: number;
  /** px travelled upward */
  distance?: number;
  delay?: number;
  duration?: number;
}

/**
 * Fade + rise a set of elements in sequence. Returns a cleanup that cancels
 * the animation and removes every inline style it wrote, so elements always
 * end in their plain CSS state (no lingering transforms that would affect
 * stacking or fixed-position descendants).
 */
export function reveal(targets: Targets, opts: RevealOptions = {}): () => void {
  if (targets.length === 0 || prefersReducedMotion()) return () => {};
  const compact = matches(COMPACT_QUERY);
  const distance = opts.distance ?? (compact ? 6 : 10);
  const step = opts.step ?? (compact ? 30 : 45);

  // Set the start state synchronously (we run in a layout effect, before
  // paint) so there is never a frame of fully-visible content first.
  for (const el of targets) {
    el.style.opacity = "0";
    el.style.transform = `translateY(${distance}px)`;
  }
  const anim = animate(targets, {
    opacity: [0, 1],
    translateY: [distance, 0],
    duration: opts.duration ?? 460,
    delay: stagger(step, { start: opts.delay ?? 0 }),
    ease: EASE_OUT,
    onComplete: () => clearInline(targets),
  });
  return () => {
    anim.cancel();
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
 * its `[data-reveal-item]` children follow slightly behind. Used on the
 * Customer 360 page (identity -> behaviour -> transactions -> segments ->
 * intelligence) so hierarchy reads top-down without the page "flying in".
 */
export function useStagedReveal<T extends HTMLElement = HTMLDivElement>(key: unknown) {
  const ref = useRef<T>(null);
  useLayoutEffect(() => {
    if (!key || prefersReducedMotion()) return;
    const root = ref.current;
    const sections = collect(root, "[data-stage]");
    if (sections.length === 0) return;
    const compact = matches(COMPACT_QUERY);
    const distance = compact ? 6 : 12;
    const sectionGap = compact ? 60 : 90;
    const items = sections.map((s) => collect(s, "[data-reveal-item]"));
    const all = [...sections, ...items.flat()];

    for (const el of all) {
      el.style.opacity = "0";
      el.style.transform = `translateY(${distance}px)`;
    }
    const tl = createTimeline({
      defaults: { duration: 480, ease: EASE_OUT },
      onComplete: () => clearInline(all),
    });
    sections.forEach((section, i) => {
      const at = i * sectionGap;
      tl.add(section, { opacity: [0, 1], translateY: [distance, 0] }, at);
      if (items[i].length) {
        tl.add(
          items[i],
          { opacity: [0, 1], translateY: [distance / 2, 0], duration: 380, delay: stagger(compact ? 25 : 35) },
          at + 80,
        );
      }
    });
    return () => {
      tl.cancel();
      clearInline(all);
    };
  }, [key]);
  return ref;
}

/**
 * Counts a number up from zero once, on first render with a value. The
 * final formatted value is rendered by React from the start (so screen
 * readers, copy/paste, and reduced-motion users always get the real number);
 * the animation only temporarily rewrites the visible text.
 */
export function useCountUp(value: number | null | undefined, format: (n: number) => string, duration = 700) {
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
      duration: 900,
      delay: 120,
      ease: "outExpo",
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
  animate(el, { translateY: y, opacity: 1, duration: 380, ease: "outExpo" });
}
