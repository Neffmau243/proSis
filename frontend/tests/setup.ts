import { vi } from 'vitest'

// happy-dom implements neither `matchMedia` nor the observer APIs that
// Element Plus components subscribe to when they mount.  Stubbing them here
// keeps component tests focused on behaviour instead of environment shims.
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia
}

class NoopObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): [] {
    return []
  }
}

if (!window.ResizeObserver) {
  window.ResizeObserver = NoopObserver as unknown as typeof window.ResizeObserver
}

if (!window.IntersectionObserver) {
  window.IntersectionObserver = NoopObserver as unknown as typeof window.IntersectionObserver
}

if (!window.scrollTo) {
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo
}
