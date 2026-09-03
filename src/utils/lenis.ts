/* Lenis Smooth Scroll Engine - Self-Contained High-Performance Implementation */

interface LenisOptions {
  duration?: number;
  easing?: (t: number) => number;
  smoothWheel?: boolean;
  wheelMultiplier?: number;
}

export class LenisEngine {
  private isDestroyed = false;
  private targetScroll = window.scrollY;
  private animatedScroll = window.scrollY;
  private duration: number;
  private easing: (t: number) => number;
  private wheelMultiplier: number;
  private rafId: number | null = null;

  constructor(options: LenisOptions = {}) {
    this.duration = options.duration || 1.2;
    this.easing = options.easing || ((t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)));
    this.wheelMultiplier = options.wheelMultiplier || 0.85;

    // Respect prefers-reduced-motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    this.init();
  }

  private init() {
    this.onWheel = this.onWheel.bind(this);
    this.onRaf = this.onRaf.bind(this);

    window.addEventListener('wheel', this.onWheel, { passive: false });
    this.rafId = requestAnimationFrame(this.onRaf);
  }

  private onWheel(e: WheelEvent) {
    // Exclude inner scroll elements
    const targetEl = e.target as HTMLElement;
    if (targetEl?.closest('.chat-stream, .logs-console, .event-log-list')) return;

    e.preventDefault();

    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    this.targetScroll += e.deltaY * this.wheelMultiplier;
    this.targetScroll = Math.max(0, Math.min(this.targetScroll, maxScroll));
  }

  private onRaf() {
    if (this.isDestroyed) return;

    // Dampened Lerp toward targetScroll
    const lerpFactor = 0.09;
    this.animatedScroll += (this.targetScroll - this.animatedScroll) * lerpFactor;

    window.scrollTo(0, Math.round(this.animatedScroll * 100) / 100);

    if (Math.abs(this.targetScroll - this.animatedScroll) < 0.1) {
      this.animatedScroll = this.targetScroll;
    }

    this.rafId = requestAnimationFrame(this.onRaf);
  }

  public destroy() {
    this.isDestroyed = true;
    window.removeEventListener('wheel', this.onWheel);
    if (this.rafId) cancelAnimationFrame(this.rafId);
  }
}
