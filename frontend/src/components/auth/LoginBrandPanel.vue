<template>
  <aside class="brand-panel" aria-label="Sistema de Salud IPRESS">
    <div class="brand-panel__content">
      <div class="brand-panel__mark" aria-hidden="true">
        <svg class="brand-panel__mark-icon" viewBox="0 0 48 48" fill="none">
          <path
            d="M24 11v26M11 24h26"
            stroke="currentColor"
            stroke-width="5"
            stroke-linecap="round"
          />
          <circle cx="24" cy="24" r="19" stroke="currentColor" stroke-width="2" opacity=".38" />
        </svg>
      </div>

      <p class="brand-panel__title">Sistema de Salud IPRESS</p>
    </div>

    <svg class="brand-panel__signal" viewBox="0 0 560 120" fill="none" aria-hidden="true">
      <path
        d="M0 68h126l25-29 28 58 35-78 30 49h276"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>

    <div class="brand-panel__orbit brand-panel__orbit--large" aria-hidden="true"></div>
    <div class="brand-panel__orbit brand-panel__orbit--small" aria-hidden="true"></div>
  </aside>
</template>

<style scoped>
.brand-panel {
  position: relative;
  display: flex;
  min-width: 0;
  overflow: hidden;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(2.5rem, 6vw, 6rem);
  color: #eef7ff;
  background:
    radial-gradient(circle at 78% 18%, rgb(101 220 214 / 25%), transparent 25rem),
    linear-gradient(145deg, #173db1 0%, #126094 55%, #0a796f 100%);
  isolation: isolate;
}

.brand-panel__content,
.brand-panel__signal {
  position: relative;
  z-index: 1;
}

.brand-panel__content {
  display: grid;
  max-width: 28rem;
  gap: 2rem;
}

.brand-panel__mark {
  display: grid;
  width: 4rem;
  height: 4rem;
  place-items: center;
  border-radius: 1rem;
  color: #fff;
  background: rgb(255 255 255 / 16%);
}

.brand-panel__mark-icon {
  width: 2.5rem;
  height: 2.5rem;
}

.brand-panel__title {
  max-width: 8ch;
  margin: 0;
  font-size: clamp(2.35rem, 4.8vw, 4.5rem);
  font-weight: 720;
  letter-spacing: -0.04em;
  line-height: 0.98;
  text-wrap: balance;
}

.brand-panel__signal {
  width: min(100%, 35rem);
  margin-top: auto;
  color: rgb(229 248 255 / 56%);
}

.brand-panel__orbit {
  position: absolute;
  z-index: 0;
  border: 1px solid rgb(218 250 255 / 20%);
  border-radius: 50%;
  pointer-events: none;
}

.brand-panel__orbit--large {
  right: clamp(-10rem, -10vw, -5rem);
  bottom: clamp(-13rem, -11vw, -7rem);
  width: clamp(25rem, 38vw, 40rem);
  height: clamp(25rem, 38vw, 40rem);
  animation: orbit-drift 18s cubic-bezier(0.22, 1, 0.36, 1) infinite alternate;
}

.brand-panel__orbit--small {
  top: 25%;
  right: clamp(-4rem, -4vw, -1rem);
  width: clamp(8rem, 12vw, 12rem);
  height: clamp(8rem, 12vw, 12rem);
}

@keyframes orbit-drift {
  to {
    transform: translate3d(-1.5rem, -1.25rem, 0) scale(1.04);
  }
}

@media (max-width: 919px) {
  .brand-panel {
    display: none;
  }
}

@media (max-height: 640px) and (min-width: 920px) {
  .brand-panel {
    padding-block: 2rem;
  }

  .brand-panel__content {
    gap: 1.25rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .brand-panel__orbit--large {
    animation: none;
  }
}
</style>
