<template>
  <!-- How a passkey works, as one looping scene: added once (the key goes to the device's keychain), then used to sign in. -->
  <div class="pk">
    <div class="pk-stage" aria-hidden="true">
      <span class="pk-glow" />
      <div class="pk-phone">
        <span class="pk-island" />
        <div class="pk-screen">
          <div class="pk-scene pk-scene--setup">
            <span class="pk-avatar"><i class="pi pi-user" /></span>
            <span class="pk-line pk-line--60" />
            <span class="pk-line pk-line--40" />
            <span class="pk-btn pk-btn--add"><i class="pi pi-plus" /><span class="pk-btn__text" /></span>
          </div>
          <div class="pk-scene pk-scene--login">
            <span class="pk-logo"><i class="pi pi-shield" /></span>
            <span class="pk-field"><span class="pk-line pk-line--40" /></span>
            <span class="pk-btn pk-btn--key"><i class="pi pi-key" /><span class="pk-btn__text" /></span>
          </div>
          <div class="pk-scene pk-scene--home">
            <span class="pk-line pk-line--60" />
            <span class="pk-tiles"><span /><span /><span /></span>
            <span class="pk-bars"><span v-for="h in bars" :key="h" :style="{ height: `${h}%` }" /></span>
          </div>
          <div class="pk-sheet">
            <svg class="pk-face" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 14V9a5 5 0 0 1 5-5h5M34 4h5a5 5 0 0 1 5 5v5M44 34v5a5 5 0 0 1-5 5h-5M14 44H9a5 5 0 0 1-5-5v-5" />
              <path d="M17 17v4M31 17v4M24 17v9h-2M17 32c4 3 10 3 14 0" />
            </svg>
            <span class="pk-scan" />
            <svg class="pk-check" viewBox="0 0 48 48" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="24" cy="24" r="21" />
              <path d="M14.5 24.5l6.5 6.5 12.5-13" />
            </svg>
          </div>
        </div>
        <span class="pk-tap pk-tap--add" />
      </div>
      <span class="pk-key"><i class="pi pi-key" /></span>
      <span class="pk-vault">
        <i class="pi pi-lock" />
        <span class="pk-vault__ok"><i class="pi pi-check" /></span>
      </span>
    </div>
    <ol class="pk-steps">
      <li class="pk-step pk-step--1"><span class="pk-step__n">1</span>{{ t('account.passkeys.suggest.stepAdd') }}</li>
      <li class="pk-step pk-step--2"><span class="pk-step__n">2</span>{{ t('account.passkeys.suggest.stepSignIn') }}</li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const bars = [45, 70, 55, 90, 65]
</script>

<style scoped>
/* One 12 s loop: 0–48 % adding the passkey, 50–98 % signing in with it. Every keyframe below shares it. */
.pk {
  --pk-d: 12s;
  --pk-ease: cubic-bezier(0.32, 0.72, 0, 1);
  --pk-blue: #0a84ff;
  --pk-green: #30d158;
  --pk-screen: #f5f5f7;
  --pk-ink: #1d1d1f;
  --pk-soft: rgba(60, 60, 67, 0.14);
  --pk-sheet: rgba(255, 255, 255, 0.86);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
html.app-dark .pk {
  --pk-screen: #1c1c1e;
  --pk-ink: #f5f5f7;
  --pk-soft: rgba(235, 235, 245, 0.16);
  --pk-sheet: rgba(44, 44, 46, 0.88);
}

.pk-stage {
  position: relative;
  height: 15rem;
  border-radius: 24px;
  overflow: hidden;
  direction: ltr;
  background:
    radial-gradient(120% 90% at 15% 0%, color-mix(in srgb, var(--pk-blue) 20%, transparent), transparent 60%),
    radial-gradient(100% 90% at 100% 100%, rgba(191, 90, 242, 0.16), transparent 60%),
    color-mix(in srgb, var(--p-content-background) 92%, var(--pk-blue));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--p-text-color) 6%, transparent);
}
.pk-glow {
  position: absolute;
  left: calc(50% - 2.5rem);
  top: 50%;
  width: 11rem;
  height: 11rem;
  translate: -50% -50%;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--pk-blue) 30%, transparent), transparent 65%);
  filter: blur(8px);
  animation: pk-breathe 6s ease-in-out infinite;
}

/* the phone */
.pk-phone {
  position: absolute;
  left: calc(50% - 2.5rem);
  top: 50%;
  width: 7.25rem;
  height: 13.25rem;
  translate: -50% -50%;
  padding: 0.28rem;
  border-radius: 1.65rem;
  background: linear-gradient(145deg, #3a3a3c, #0b0b0c 45%, #2c2c2e);
  box-shadow:
    0 18px 36px -12px rgba(0, 0, 0, 0.45),
    0 0 0 1px rgba(255, 255, 255, 0.06) inset;
  animation: pk-float 6s ease-in-out infinite;
}
.pk-island {
  position: absolute;
  z-index: 3;
  top: 0.62rem;
  left: 50%;
  width: 1.9rem;
  height: 0.52rem;
  translate: -50% 0;
  border-radius: 999px;
  background: #000;
}
.pk-screen {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 1.4rem;
  overflow: hidden;
  background: var(--pk-screen);
  color: var(--pk-ink);
}
.pk-scene {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.45rem;
  padding: 1.8rem 0.7rem 0.8rem;
  opacity: 0;
}
.pk-scene--setup {
  opacity: 1;
  animation: pk-setup var(--pk-d) var(--pk-ease) infinite;
}
.pk-scene--login {
  animation: pk-login var(--pk-d) var(--pk-ease) infinite;
}
.pk-scene--home {
  align-items: stretch;
  animation: pk-home var(--pk-d) var(--pk-ease) infinite;
}
.pk-avatar,
.pk-logo {
  display: grid;
  place-items: center;
  width: 2.2rem;
  height: 2.2rem;
  margin: 0.4rem 0 0.2rem;
  border-radius: 50%;
  color: #fff;
  font-size: 0.95rem;
  background: linear-gradient(145deg, #64d2ff, var(--pk-blue));
}
.pk-logo {
  border-radius: 0.7rem;
  background: linear-gradient(145deg, #5e5ce6, var(--pk-blue));
}
.pk-line {
  display: block;
  height: 0.32rem;
  border-radius: 999px;
  background: var(--pk-soft);
}
.pk-line--60 {
  width: 60%;
}
.pk-line--40 {
  width: 40%;
}
.pk-field {
  display: flex;
  align-items: center;
  width: 100%;
  height: 1.35rem;
  padding: 0 0.45rem;
  border-radius: 0.45rem;
  background: color-mix(in srgb, var(--pk-soft) 60%, transparent);
}
.pk-field .pk-line {
  width: 55%;
}
.pk-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  width: 100%;
  height: 1.45rem;
  margin-top: auto;
  border-radius: 999px;
  background: var(--pk-blue);
  color: #fff;
  font-size: 0.55rem;
}
.pk-btn__text {
  width: 2.2rem;
  height: 0.26rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
}
.pk-btn--add {
  animation: pk-press-add var(--pk-d) ease-in-out infinite;
}
.pk-btn--key {
  animation: pk-press-key var(--pk-d) ease-in-out infinite;
}
.pk-tiles {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.3rem;
}
.pk-tiles span {
  height: 1.5rem;
  border-radius: 0.45rem;
  background: color-mix(in srgb, var(--pk-blue) 16%, transparent);
}
.pk-tiles span:nth-child(2) {
  background: color-mix(in srgb, var(--pk-green) 18%, transparent);
}
.pk-tiles span:nth-child(3) {
  background: rgba(191, 90, 242, 0.16);
}
.pk-bars {
  display: flex;
  align-items: flex-end;
  gap: 0.25rem;
  height: 3.4rem;
  margin-top: auto;
  padding: 0.4rem;
  border-radius: 0.55rem;
  background: color-mix(in srgb, var(--pk-soft) 45%, transparent);
}
.pk-bars span {
  flex: 1;
  border-radius: 0.2rem;
  background: linear-gradient(180deg, #64d2ff, var(--pk-blue));
  transform-origin: bottom;
  animation: pk-grow var(--pk-d) var(--pk-ease) infinite;
}

/* the system sheet that asks for the face, fingerprint or screen lock */
.pk-sheet {
  position: absolute;
  z-index: 2;
  left: 0.3rem;
  right: 0.3rem;
  bottom: 0.3rem;
  height: 52%;
  display: grid;
  place-items: center;
  border-radius: 1.15rem;
  background: var(--pk-sheet);
  backdrop-filter: blur(14px) saturate(180%);
  -webkit-backdrop-filter: blur(14px) saturate(180%);
  box-shadow: 0 -4px 18px rgba(0, 0, 0, 0.12);
  translate: 0 115%;
  animation: pk-sheet var(--pk-d) var(--pk-ease) infinite;
}
.pk-face,
.pk-check,
.pk-scan {
  grid-area: 1 / 1;
}
.pk-face {
  width: 2.6rem;
  height: 2.6rem;
  color: var(--pk-blue);
  opacity: 0;
  animation: pk-face var(--pk-d) ease-in-out infinite;
}
.pk-scan {
  width: 2.9rem;
  height: 0.18rem;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, var(--pk-blue), transparent);
  box-shadow: 0 0 10px var(--pk-blue);
  opacity: 0;
  animation: pk-scan var(--pk-d) linear infinite;
}
.pk-check {
  width: 2.7rem;
  height: 2.7rem;
  opacity: 0;
  animation: pk-check var(--pk-d) var(--pk-ease) infinite;
}
.pk-check circle {
  fill: var(--pk-green);
}
.pk-check path {
  stroke: #fff;
  stroke-width: 3.4;
  stroke-dasharray: 30;
  stroke-dashoffset: 30;
  animation: pk-draw var(--pk-d) ease-out infinite;
}

/* a finger's tap on the button (both buttons sit in the same place) */
.pk-tap {
  position: absolute;
  z-index: 4;
  left: 50%;
  bottom: 1.12rem;
  width: 1.7rem;
  height: 1.7rem;
  translate: -50% 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.55);
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.7);
  opacity: 0;
  animation: pk-tap var(--pk-d) ease-out infinite;
}

/* the passkey itself: into the keychain, later back out to sign in */
.pk-key {
  position: absolute;
  z-index: 5;
  left: calc(50% - 2.5rem);
  top: 50%;
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  margin: -1rem 0 0 -1rem;
  border-radius: 50%;
  color: #fff;
  font-size: 0.9rem;
  background: linear-gradient(145deg, #ffd60a, #ff9f0a);
  box-shadow: 0 6px 16px -4px rgba(255, 159, 10, 0.7);
  opacity: 0;
  animation: pk-key var(--pk-d) var(--pk-ease) infinite;
}
.pk-vault {
  position: absolute;
  left: calc(50% + 4.5rem);
  top: 50%;
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  margin: -1.5rem 0 0 -1.5rem;
  border-radius: 0.85rem;
  color: #fff;
  font-size: 1.15rem;
  background: linear-gradient(145deg, #64d2ff, var(--pk-blue) 55%, #5e5ce6);
  box-shadow:
    0 12px 24px -10px color-mix(in srgb, var(--pk-blue) 80%, transparent),
    inset 0 1px 0 rgba(255, 255, 255, 0.35);
  animation: pk-vault var(--pk-d) var(--pk-ease) infinite;
}
.pk-vault__ok {
  position: absolute;
  top: -0.35rem;
  right: -0.35rem;
  display: grid;
  place-items: center;
  width: 1.15rem;
  height: 1.15rem;
  border-radius: 50%;
  font-size: 0.55rem;
  background: var(--pk-green);
  box-shadow: 0 0 0 2px var(--p-content-background);
  opacity: 0;
  animation: pk-ok var(--pk-d) var(--pk-ease) infinite;
}

/* the two steps under the scene, each lit while its part plays */
.pk-steps {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.pk-step {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  padding: 0.5rem 0.6rem 0.6rem;
  border-radius: 14px;
  overflow: hidden;
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.25;
  color: var(--p-text-color);
  background: color-mix(in srgb, var(--p-text-color) 5%, transparent);
}
.pk-step::before {
  content: '';
  position: absolute;
  inset: 0;
  background: color-mix(in srgb, var(--pk-blue) 12%, transparent);
  opacity: 0;
}
.pk-step::after {
  content: '';
  position: absolute;
  left: 0.6rem;
  right: 0.6rem;
  bottom: 0.25rem;
  height: 0.16rem;
  border-radius: 999px;
  background: var(--pk-blue);
  transform: scaleX(0);
  transform-origin: left;
}
[dir='rtl'] .pk-step::after {
  transform-origin: right;
}
.pk-step__n {
  position: relative;
  flex: none;
  display: grid;
  place-items: center;
  width: 1.3rem;
  height: 1.3rem;
  border-radius: 50%;
  font-size: 0.72rem;
  color: #fff;
  background: color-mix(in srgb, var(--p-text-color) 30%, transparent);
}
.pk-step--1::before {
  animation: pk-on-1 var(--pk-d) ease infinite;
}
.pk-step--1 .pk-step__n {
  animation: pk-n-1 var(--pk-d) ease infinite;
}
.pk-step--1::after {
  animation: pk-bar-1 var(--pk-d) linear infinite;
}
.pk-step--2::before {
  animation: pk-on-2 var(--pk-d) ease infinite;
}
.pk-step--2 .pk-step__n {
  animation: pk-n-2 var(--pk-d) ease infinite;
}
.pk-step--2::after {
  animation: pk-bar-2 var(--pk-d) linear infinite;
}

@keyframes pk-breathe {
  50% {
    opacity: 0.6;
    scale: 0.9;
  }
}
@keyframes pk-float {
  50% {
    translate: -50% calc(-50% - 4px);
  }
}
@keyframes pk-setup {
  0% {
    opacity: 0;
    translate: 0 8px;
  }
  4%,
  45% {
    opacity: 1;
    translate: 0 0;
  }
  49%,
  100% {
    opacity: 0;
    translate: 0 -8px;
  }
}
@keyframes pk-login {
  0%,
  48% {
    opacity: 0;
    translate: 0 8px;
  }
  52%,
  84% {
    opacity: 1;
    translate: 0 0;
  }
  88%,
  100% {
    opacity: 0;
    translate: 0 -8px;
  }
}
@keyframes pk-home {
  0%,
  85% {
    opacity: 0;
    scale: 0.94;
  }
  89%,
  96% {
    opacity: 1;
    scale: 1;
  }
  100% {
    opacity: 0;
    scale: 1;
  }
}
@keyframes pk-grow {
  0%,
  86% {
    transform: scaleY(0.15);
  }
  93%,
  100% {
    transform: scaleY(1);
  }
}
@keyframes pk-press-add {
  0%,
  9.5%,
  13%,
  100% {
    scale: 1;
  }
  11% {
    scale: 0.93;
  }
}
@keyframes pk-press-key {
  0%,
  56.5%,
  60%,
  100% {
    scale: 1;
  }
  58% {
    scale: 0.93;
  }
}
@keyframes pk-tap {
  0%,
  9% {
    opacity: 0;
    scale: 0.3;
  }
  10.5% {
    opacity: 0.9;
    scale: 0.6;
  }
  15% {
    opacity: 0;
    scale: 1.7;
  }
  56% {
    opacity: 0;
    scale: 0.3;
  }
  57.5% {
    opacity: 0.9;
    scale: 0.6;
  }
  62%,
  100% {
    opacity: 0;
    scale: 1.7;
  }
}
@keyframes pk-sheet {
  0%,
  14% {
    translate: 0 115%;
  }
  18%,
  35% {
    translate: 0 0;
  }
  39%,
  61% {
    translate: 0 115%;
  }
  65%,
  83% {
    translate: 0 0;
  }
  87%,
  100% {
    translate: 0 115%;
  }
}
@keyframes pk-face {
  0%,
  16% {
    opacity: 0;
    scale: 0.8;
  }
  19% {
    opacity: 1;
    scale: 1;
  }
  22%,
  27% {
    scale: 0.9;
  }
  24.5% {
    scale: 1;
  }
  29% {
    opacity: 1;
    scale: 1;
  }
  31% {
    opacity: 0;
    scale: 1.12;
  }
  63% {
    opacity: 0;
    scale: 0.8;
  }
  66% {
    opacity: 1;
    scale: 1;
  }
  69%,
  74% {
    scale: 0.9;
  }
  71.5% {
    scale: 1;
  }
  76% {
    opacity: 1;
    scale: 1;
  }
  78%,
  100% {
    opacity: 0;
    scale: 1.12;
  }
}
@keyframes pk-scan {
  0%,
  19% {
    opacity: 0;
    translate: 0 -1.1rem;
  }
  20%,
  27% {
    opacity: 1;
  }
  28% {
    opacity: 0;
    translate: 0 1.1rem;
  }
  66% {
    opacity: 0;
    translate: 0 -1.1rem;
  }
  67%,
  74% {
    opacity: 1;
  }
  75%,
  100% {
    opacity: 0;
    translate: 0 1.1rem;
  }
}
@keyframes pk-check {
  0%,
  29% {
    opacity: 0;
    scale: 0.5;
  }
  32%,
  36% {
    opacity: 1;
    scale: 1;
  }
  38%,
  76% {
    opacity: 0;
    scale: 0.5;
  }
  79%,
  83% {
    opacity: 1;
    scale: 1;
  }
  85%,
  100% {
    opacity: 0;
    scale: 0.5;
  }
}
@keyframes pk-draw {
  0%,
  30% {
    stroke-dashoffset: 30;
  }
  34%,
  37% {
    stroke-dashoffset: 0;
  }
  38%,
  77% {
    stroke-dashoffset: 30;
  }
  81%,
  84% {
    stroke-dashoffset: 0;
  }
  85%,
  100% {
    stroke-dashoffset: 30;
  }
}
@keyframes pk-key {
  0%,
  33% {
    opacity: 0;
    scale: 0.4;
    translate: 0 1.6rem;
  }
  36% {
    opacity: 1;
    scale: 1.1;
    translate: 0 0.6rem;
  }
  40% {
    translate: 3.5rem -2.6rem;
  }
  44% {
    opacity: 1;
    scale: 0.8;
    translate: 7rem 0;
  }
  46%,
  76% {
    opacity: 0;
    scale: 0.4;
    translate: 7rem 0;
  }
  78% {
    opacity: 1;
    scale: 0.9;
  }
  81% {
    translate: 3.5rem -2.6rem;
    scale: 1.1;
  }
  84% {
    opacity: 1;
    scale: 0.9;
    translate: 0 1.6rem;
  }
  86%,
  100% {
    opacity: 0;
    scale: 0.4;
    translate: 0 1.6rem;
  }
}
@keyframes pk-vault {
  0%,
  43%,
  49%,
  74%,
  80%,
  100% {
    scale: 1;
  }
  45.5%,
  76.5% {
    scale: 1.14;
  }
}
@keyframes pk-ok {
  0%,
  44% {
    opacity: 0;
    scale: 0.3;
  }
  47%,
  96% {
    opacity: 1;
    scale: 1;
  }
  100% {
    opacity: 0;
    scale: 0.3;
  }
}
@keyframes pk-on-1 {
  0%,
  47%,
  100% {
    opacity: 1;
  }
  50%,
  97% {
    opacity: 0;
  }
}
@keyframes pk-on-2 {
  0%,
  47%,
  100% {
    opacity: 0;
  }
  50%,
  97% {
    opacity: 1;
  }
}
@keyframes pk-n-1 {
  0%,
  47%,
  100% {
    background-color: var(--pk-blue);
  }
  50%,
  97% {
    background-color: color-mix(in srgb, var(--p-text-color) 30%, transparent);
  }
}
@keyframes pk-n-2 {
  0%,
  47%,
  100% {
    background-color: color-mix(in srgb, var(--p-text-color) 30%, transparent);
  }
  50%,
  97% {
    background-color: var(--pk-blue);
  }
}
@keyframes pk-bar-1 {
  0% {
    opacity: 1;
    transform: scaleX(0);
  }
  47% {
    opacity: 1;
    transform: scaleX(1);
  }
  50%,
  100% {
    opacity: 0;
    transform: scaleX(1);
  }
}
@keyframes pk-bar-2 {
  0%,
  49% {
    opacity: 0;
    transform: scaleX(0);
  }
  50% {
    opacity: 1;
    transform: scaleX(0);
  }
  97% {
    opacity: 1;
    transform: scaleX(1);
  }
  100% {
    opacity: 0;
    transform: scaleX(1);
  }
}

/* still: the first step, the key already in the keychain */
@media (prefers-reduced-motion: reduce) {
  .pk *,
  .pk *::before,
  .pk *::after {
    animation: none !important;
  }
  .pk-vault__ok,
  .pk-step--1::before {
    opacity: 1;
  }
  .pk-step--1 .pk-step__n {
    background: var(--pk-blue);
  }
}
</style>
