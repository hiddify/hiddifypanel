<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { detectPwaPlatform, desktopOsName, type PwaPlatform } from '@/shared/composables/usePwaInstall'

/**
 * How to install the panel as an app, as a looping animation of the browser's own controls: Safari on iPhone / iPad,
 * Chrome on Android, Chrome on a computer. The detected platform is shown first; the others are one tap away.
 */
const { t } = useI18n()
const detected = detectPwaPlatform()
const platform = ref<PwaPlatform>(detected)

const PLATFORMS: PwaPlatform[] = ['ios', 'android', 'desktop']
const steps = computed(() => {
  if (platform.value === 'ios') return [t('pwa.guide.ios1'), t('pwa.guide.ios2'), t('pwa.guide.ios3'), t('pwa.guide.ios4')]
  if (platform.value === 'android') return [t('pwa.guide.android1'), t('pwa.guide.android2'), t('pwa.guide.android3')]
  return [t('pwa.guide.desktop1'), t('pwa.guide.desktop2'), t('pwa.guide.desktop3')]
})
function tabLabel(p: PwaPlatform): string {
  if (p === 'ios') return t('pwa.guide.tabIos')
  if (p === 'android') return t('pwa.guide.tabAndroid')
  // On a phone the computer's system is unknown (an iPhone even says "Mac OS X"): just "Computer"
  return t('pwa.guide.tabDesktop', { os: detected === 'desktop' ? desktopOsName() : t('pwa.guide.computer') })
}
</script>

<template>
  <div class="guide">
    <div class="guide__tabs" role="tablist" :aria-label="t('pwa.guide.platform')">
      <button
        v-for="p in PLATFORMS"
        :key="p"
        type="button"
        role="tab"
        class="guide__tab"
        :class="{ 'guide__tab--on': platform === p }"
        :aria-selected="platform === p"
        @click="platform = p"
      >
        <i :class="['pi', p === 'ios' ? 'pi-apple' : p === 'android' ? 'pi-android' : 'pi-desktop']" />{{ tabLabel(p) }}
      </button>
    </div>

    <!-- The scene: a fixed drawing (left to right in every language), restarted when the platform changes -->
    <div :key="platform" class="stage" :class="`stage--${platform}`" dir="ltr" aria-hidden="true">
      <!-- iPhone · Safari (iOS 27): ••• → Share → Add to Home Screen → Add -->
      <div v-if="platform === 'ios'" class="phone">
        <div class="phone__notch" />
        <div class="page"><span class="page__bar page__bar--wide" /><span class="page__bar" /><span class="page__card" /><span class="page__bar" /></div>
        <div class="ios-bar"><i class="pi pi-chevron-left" /><span class="ios-bar__url">panel</span><span class="ios-bar__more tap-1">•••</span></div>
        <div class="sheet ios-menu">
          <div class="sheet__row"><i class="pi pi-bookmark" /><span /></div>
          <div class="sheet__row sheet__row--hit hit-2"><i class="pi pi-upload" /><b>Share</b></div>
          <div class="sheet__row"><i class="pi pi-copy" /><span /></div>
        </div>
        <div class="sheet ios-share">
          <div class="sheet__apps"><span /><span /><span /><span /></div>
          <div class="sheet__row"><i class="pi pi-copy" /><span /></div>
          <div class="sheet__row sheet__row--hit hit-3"><i class="pi pi-plus-circle" /><b>Add to Home Screen</b></div>
        </div>
        <div class="sheet ios-add">
          <div class="ios-add__head"><span>Cancel</span><b>Add to Home Screen</b><span class="ios-add__btn hit-4">Add</span></div>
          <div class="ios-add__app"><span class="app-icon" /><span class="page__bar" /></div>
        </div>
        <i class="pi pi-circle-fill finger finger--ios" />
      </div>

      <!-- Android 16 · Chrome: ⋮ → Add to home screen → Install -->
      <div v-else-if="platform === 'android'" class="phone">
        <div class="and-bar"><i class="pi pi-home" /><span class="and-bar__url">panel</span><span class="and-bar__more tap-1"><i class="pi pi-ellipsis-v" /></span></div>
        <div class="page"><span class="page__bar page__bar--wide" /><span class="page__bar" /><span class="page__card" /><span class="page__bar" /></div>
        <div class="and-menu">
          <div class="and-menu__row"><span /></div>
          <div class="and-menu__row"><span /></div>
          <div class="and-menu__row and-menu__row--hit hit-2"><i class="pi pi-mobile" /><b>Add to home screen</b></div>
          <div class="and-menu__row"><span /></div>
        </div>
        <div class="and-dialog">
          <b>Install app</b>
          <div class="and-dialog__app"><span class="app-icon" /><span class="page__bar" /></div>
          <div class="and-dialog__btns"><span>Cancel</span><span class="and-dialog__ok hit-3">Install</span></div>
        </div>
        <i class="pi pi-circle-fill finger finger--android" />
      </div>

      <!-- Chrome on a computer: the install icon in the address bar → Install → its own window -->
      <div v-else class="window">
        <div class="window__tabs"><span class="window__dot" /><span class="window__dot" /><span class="window__dot" /><span class="window__tab" /></div>
        <div class="window__bar">
          <i class="pi pi-refresh" />
          <span class="window__url">panel<span class="window__install tap-1"><i class="pi pi-download" /></span></span>
          <i class="pi pi-ellipsis-v" />
        </div>
        <div class="page page--wide"><span class="page__bar page__bar--wide" /><span class="page__card" /><span class="page__bar" /></div>
        <div class="win-pop">
          <b>Install app?</b>
          <div class="win-pop__app"><span class="app-icon" /><span class="page__bar" /></div>
          <div class="win-pop__btns"><span class="win-pop__ok hit-2">Install</span><span>Cancel</span></div>
        </div>
        <div class="win-app">
          <div class="win-app__title"><span class="app-icon app-icon--tiny" /><span class="page__bar" /></div>
          <div class="page"><span class="page__bar page__bar--wide" /><span class="page__card" /></div>
        </div>
        <i class="pi pi-arrow-up-left cursor" />
      </div>
    </div>

    <ol :key="`s-${platform}`" class="guide__steps" :class="`guide__steps--${steps.length}`">
      <li v-for="(s, i) in steps" :key="i" class="guide__step" :style="{ '--i': i }"><span class="guide__n">{{ i + 1 }}</span>{{ s }}</li>
    </ol>
  </div>
</template>

<style scoped>
.guide {
  --dur: 10s;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.guide__tabs {
  display: flex;
  gap: 0.3rem;
  padding: 0.25rem;
  border-radius: 12px;
  background: var(--p-content-hover-background);
}
.guide__tab {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 0.4rem 0.3rem;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}
.guide__tab--on {
  background: var(--p-content-background);
  color: var(--p-primary-color);
  box-shadow: 0 1px 3px rgb(0 0 0 / 12%);
}

/* --- the stage --- */
.stage {
  --ink: color-mix(in srgb, var(--p-text-color) 16%, transparent);
  --hit: var(--p-primary-color);
  position: relative;
  height: 13rem;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 16px;
  background: radial-gradient(120% 100% at 50% 0%, color-mix(in srgb, var(--p-primary-color) 16%, transparent), transparent 70%), var(--p-content-hover-background);
}
.phone {
  position: relative;
  width: 7.6rem;
  height: 12rem;
  overflow: hidden;
  border: 0.35rem solid #1f2937;
  border-radius: 1.4rem;
  background: var(--p-content-background);
  box-shadow: 0 14px 30px -14px rgb(0 0 0 / 55%);
}
.phone__notch {
  position: absolute;
  top: 0.25rem;
  left: 50%;
  width: 2.2rem;
  height: 0.5rem;
  border-radius: 999px;
  background: #1f2937;
  transform: translateX(-50%);
}
.page {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 1.2rem 0.5rem 0;
}
.stage--android .page {
  padding-top: 0.5rem;
}
.page--wide {
  padding: 0.6rem 0.8rem 0;
}
.page__bar {
  display: block;
  height: 0.35rem;
  width: 60%;
  border-radius: 999px;
  background: var(--ink);
}
.page__bar--wide {
  width: 85%;
}
.page__card {
  display: block;
  height: 2.4rem;
  border-radius: 8px;
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.app-icon {
  flex: none;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.4rem;
  background: linear-gradient(135deg, var(--p-primary-400, #60a5fa), var(--p-primary-700, #1d4ed8));
}
.app-icon--tiny {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 0.2rem;
}
.finger {
  position: absolute;
  z-index: 9;
  font-size: 0.9rem;
  color: color-mix(in srgb, #111827 55%, transparent);
  filter: drop-shadow(0 0 0 3px #fff);
  pointer-events: none;
}
/* The thing tapped / clicked lights up while it is the step */
.tap-1,
.hit-2,
.hit-3,
.hit-4 {
  border-radius: 6px;
}

/* --- iOS Safari --- */
.ios-bar {
  position: absolute;
  inset-inline: 0.3rem;
  bottom: 0.35rem;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.4rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-content-background) 75%, #e5e7eb);
  box-shadow: 0 2px 8px rgb(0 0 0 / 15%);
  font-size: 0.5rem;
}
.ios-bar__url {
  flex: 1;
  text-align: center;
  color: var(--p-text-muted-color);
}
.ios-bar__more {
  padding: 0 0.2rem;
  font-weight: 700;
  animation: lit-1 var(--dur) infinite;
}
.sheet {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  z-index: 3;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.45rem 0.4rem 0.6rem;
  border-radius: 0.8rem 0.8rem 0 0;
  background: var(--p-content-background);
  box-shadow: 0 -6px 18px -8px rgb(0 0 0 / 35%);
  font-size: 0.48rem;
  transform: translateY(110%);
}
.ios-menu {
  animation: sheet-2 var(--dur) infinite;
}
.ios-share {
  animation: sheet-3 var(--dur) infinite;
}
.ios-add {
  top: 0.9rem;
  border-radius: 0.8rem 0.8rem 0 0;
  animation: sheet-4 var(--dur) infinite;
}
.sheet__row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.3rem;
  border-radius: 6px;
  background: var(--p-content-hover-background);
}
.sheet__row span {
  flex: 1;
  height: 0.3rem;
  border-radius: 999px;
  background: var(--ink);
}
.sheet__row i {
  font-size: 0.5rem;
  color: var(--hit);
}
.sheet__apps {
  display: flex;
  gap: 0.3rem;
  padding-bottom: 0.15rem;
}
.sheet__apps span {
  width: 1rem;
  height: 1rem;
  border-radius: 0.3rem;
  background: var(--ink);
}
.hit-2 {
  animation: lit-2 var(--dur) infinite;
}
.hit-3 {
  animation: lit-3 var(--dur) infinite;
}
.hit-4 {
  animation: lit-4 var(--dur) infinite;
}
.ios-add__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.2rem;
  font-size: 0.45rem;
  color: var(--p-text-muted-color);
}
.ios-add__head b {
  color: var(--p-text-color);
}
.ios-add__btn {
  padding: 0.05rem 0.2rem;
  font-weight: 700;
  color: var(--hit);
}
.ios-add__app {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding-top: 0.4rem;
}
.finger--ios {
  animation: finger-ios var(--dur) infinite ease-in-out;
}
@keyframes finger-ios {
  0%, 4% { left: 70%; top: 60%; transform: scale(1); }
  14% { left: 82%; top: 88%; transform: scale(1); }
  18% { transform: scale(0.7); }
  22% { left: 82%; top: 88%; transform: scale(1); }
  38% { left: 45%; top: 80%; transform: scale(1); }
  42% { transform: scale(0.7); }
  47% { left: 45%; top: 80%; transform: scale(1); }
  63% { left: 55%; top: 87%; transform: scale(1); }
  67% { transform: scale(0.7); }
  72% { left: 55%; top: 87%; transform: scale(1); }
  88% { left: 84%; top: 13%; transform: scale(1); }
  92% { transform: scale(0.7); }
  96%, 100% { left: 84%; top: 13%; transform: scale(1); }
}

/* --- Android Chrome --- */
.and-bar {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.35rem 0.35rem 0.3rem;
  font-size: 0.5rem;
  border-bottom: 1px solid var(--p-content-border-color);
}
.and-bar i {
  font-size: 0.5rem;
}
.and-bar__url {
  flex: 1;
  padding: 0.15rem 0.35rem;
  border-radius: 999px;
  background: var(--p-content-hover-background);
  color: var(--p-text-muted-color);
}
.and-bar__more {
  display: grid;
  place-items: center;
  width: 0.9rem;
  height: 0.9rem;
  animation: lit-1 var(--dur) infinite;
}
.and-menu {
  position: absolute;
  top: 1.3rem;
  right: 0.25rem;
  z-index: 3;
  width: 5.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding: 0.25rem;
  border-radius: 0.5rem;
  background: var(--p-content-background);
  box-shadow: 0 8px 20px -6px rgb(0 0 0 / 40%);
  font-size: 0.45rem;
  opacity: 0;
  transform: scale(0.85);
  transform-origin: top right;
  animation: pop-2 var(--dur) infinite;
}
.and-menu__row {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.22rem 0.25rem;
}
.and-menu__row span {
  flex: 1;
  height: 0.28rem;
  border-radius: 999px;
  background: var(--ink);
}
.and-menu__row i {
  font-size: 0.5rem;
}
.and-dialog {
  position: absolute;
  inset-inline: 0.4rem;
  top: 3.4rem;
  z-index: 4;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.5rem;
  border-radius: 0.8rem;
  background: var(--p-content-background);
  box-shadow: 0 12px 26px -8px rgb(0 0 0 / 45%);
  font-size: 0.5rem;
  opacity: 0;
  transform: scale(0.9);
  animation: pop-3 var(--dur) infinite;
}
.and-dialog__app {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.and-dialog__btns {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  font-weight: 700;
  color: var(--p-text-muted-color);
}
.and-dialog__ok {
  padding: 0.08rem 0.3rem;
  color: var(--hit);
}
.finger--android {
  animation: finger-android var(--dur) infinite ease-in-out;
}
@keyframes finger-android {
  0%, 5% { left: 50%; top: 70%; transform: scale(1); }
  20% { left: 86%; top: 6%; transform: scale(1); }
  25% { transform: scale(0.7); }
  30% { left: 86%; top: 6%; transform: scale(1); }
  50% { left: 62%; top: 31%; transform: scale(1); }
  56% { transform: scale(0.7); }
  62% { left: 62%; top: 31%; transform: scale(1); }
  82% { left: 76%; top: 66%; transform: scale(1); }
  88% { transform: scale(0.7); }
  93%, 100% { left: 76%; top: 66%; transform: scale(1); }
}

/* --- Chrome on a computer --- */
.window {
  position: relative;
  width: 15rem;
  height: 10rem;
  overflow: hidden;
  border-radius: 0.6rem;
  background: var(--p-content-background);
  box-shadow: 0 14px 30px -14px rgb(0 0 0 / 55%), 0 0 0 1px var(--p-content-border-color);
}
.window__tabs {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.3rem 0.4rem 0;
  background: color-mix(in srgb, var(--p-text-color) 7%, var(--p-content-background));
}
.window__dot {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 50%;
  background: var(--ink);
}
.window__tab {
  width: 4rem;
  height: 0.9rem;
  margin-inline-start: 0.4rem;
  border-radius: 0.35rem 0.35rem 0 0;
  background: var(--p-content-background);
}
.window__bar {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.5rem;
  font-size: 0.5rem;
  border-bottom: 1px solid var(--p-content-border-color);
}
.window__bar > i {
  font-size: 0.5rem;
  color: var(--p-text-muted-color);
}
.window__url {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.18rem 0.2rem 0.18rem 0.5rem;
  border-radius: 999px;
  background: var(--p-content-hover-background);
  color: var(--p-text-muted-color);
}
.window__install {
  display: grid;
  place-items: center;
  width: 0.9rem;
  height: 0.9rem;
  color: var(--p-text-color);
  animation: lit-1 var(--dur) infinite;
}
.window__install i {
  font-size: 0.45rem;
}
.win-pop {
  position: absolute;
  top: 2.2rem;
  right: 1rem;
  z-index: 3;
  width: 7rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.45rem;
  border-radius: 0.5rem;
  background: var(--p-content-background);
  box-shadow: 0 10px 24px -8px rgb(0 0 0 / 45%), 0 0 0 1px var(--p-content-border-color);
  font-size: 0.5rem;
  opacity: 0;
  transform: translateY(-4px);
  animation: pop-2 var(--dur) infinite;
}
.win-pop__app {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.win-pop__btns {
  display: flex;
  justify-content: flex-end;
  gap: 0.35rem;
  font-weight: 600;
}
.win-pop__btns span {
  padding: 0.1rem 0.35rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color);
}
.win-pop__ok {
  color: #fff;
  border-color: transparent !important;
  background: var(--hit);
}
.win-app {
  position: absolute;
  inset: 1.4rem 2rem 0.8rem 2.6rem;
  z-index: 4;
  overflow: hidden;
  border-radius: 0.45rem;
  background: var(--p-content-background);
  box-shadow: 0 16px 30px -10px rgb(0 0 0 / 55%), 0 0 0 1px var(--p-content-border-color);
  opacity: 0;
  transform: scale(0.85);
  animation: pop-3 var(--dur) infinite;
}
.win-app__title {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.45rem;
  background: color-mix(in srgb, var(--p-primary-color) 18%, var(--p-content-background));
}
.cursor {
  position: absolute;
  z-index: 9;
  font-size: 0.85rem;
  color: var(--p-text-color);
  filter: drop-shadow(0 1px 1px rgb(0 0 0 / 35%));
  animation: cursor-desk var(--dur) infinite ease-in-out;
}
@keyframes cursor-desk {
  0%, 5% { left: 45%; top: 70%; transform: scale(1); }
  20% { left: 77%; top: 25%; transform: scale(1); }
  25% { transform: scale(0.8); }
  30% { left: 77%; top: 25%; transform: scale(1); }
  50% { left: 68%; top: 56%; transform: scale(1); }
  56% { transform: scale(0.8); }
  62% { left: 68%; top: 56%; transform: scale(1); }
  80%, 100% { left: 55%; top: 85%; transform: scale(1); }
}

/* --- shared timing: step 1 = 0–25 %, 2 = 25–50 %, 3 = 50–75 %, 4 = 75–100 % (3-step scenes: thirds) --- */
@keyframes lit-1 {
  0%, 12% { background: transparent; box-shadow: none; }
  16%, 24% { background: color-mix(in srgb, var(--hit) 22%, transparent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--hit) 30%, transparent); }
  30%, 100% { background: transparent; box-shadow: none; }
}
@keyframes lit-2 {
  0%, 38% { background: var(--p-content-hover-background); }
  42%, 49% { background: color-mix(in srgb, var(--hit) 22%, transparent); }
  52%, 100% { background: var(--p-content-hover-background); }
}
@keyframes lit-3 {
  0%, 62% { background: var(--p-content-hover-background); }
  66%, 74% { background: color-mix(in srgb, var(--hit) 22%, transparent); }
  76%, 100% { background: var(--p-content-hover-background); }
}
@keyframes lit-4 {
  0%, 88% { background: transparent; }
  91%, 98% { background: color-mix(in srgb, var(--hit) 22%, transparent); }
  100% { background: transparent; }
}
@keyframes sheet-2 {
  0%, 22% { transform: translateY(110%); }
  27%, 48% { transform: translateY(0); }
  52%, 100% { transform: translateY(110%); }
}
@keyframes sheet-3 {
  0%, 47% { transform: translateY(110%); }
  52%, 73% { transform: translateY(0); }
  77%, 100% { transform: translateY(110%); }
}
@keyframes sheet-4 {
  0%, 72% { transform: translateY(110%); }
  77%, 100% { transform: translateY(0); }
}
@keyframes pop-2 {
  0%, 28% { opacity: 0; transform: scale(0.85); }
  33%, 60% { opacity: 1; transform: scale(1); }
  64%, 100% { opacity: 0; transform: scale(0.85); }
}
@keyframes pop-3 {
  0%, 62% { opacity: 0; transform: scale(0.9); }
  67%, 96% { opacity: 1; transform: scale(1); }
  100% { opacity: 0; transform: scale(0.9); }
}
/* Android and desktop step 2/3 rows light in their own windows */
.stage--android .hit-2,
.stage--desktop .hit-2 {
  animation-name: lit-pop-2;
}
.stage--android .hit-3 {
  animation-name: lit-pop-3;
}
@keyframes lit-pop-2 {
  0%, 44% { filter: none; outline: 0 solid transparent; }
  48%, 58% { filter: brightness(1.05); outline: 3px solid color-mix(in srgb, var(--hit) 35%, transparent); }
  62%, 100% { filter: none; outline: 0 solid transparent; }
}
@keyframes lit-pop-3 {
  0%, 80% { outline: 0 solid transparent; }
  84%, 94% { outline: 3px solid color-mix(in srgb, var(--hit) 35%, transparent); }
  100% { outline: 0 solid transparent; }
}

/* --- the steps, lit in time with the scene --- */
.guide__steps {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.guide__step {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 0.55rem;
  border-radius: 10px;
  font-size: 0.86rem;
  animation: step-4 var(--dur) infinite;
  animation-delay: calc(var(--dur) * var(--i) / 4);
}
.guide__steps--3 .guide__step {
  animation-name: step-3;
  animation-delay: calc(var(--dur) * var(--i) / 3);
}
.guide__n {
  flex: none;
  display: grid;
  place-items: center;
  width: 1.45rem;
  height: 1.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--p-primary-contrast-color);
  background: var(--p-primary-color);
}
@keyframes step-4 {
  0%, 25% { background: color-mix(in srgb, var(--p-primary-color) 12%, transparent); color: var(--p-text-color); }
  26%, 100% { background: transparent; color: var(--p-text-muted-color); }
}
@keyframes step-3 {
  0%, 33% { background: color-mix(in srgb, var(--p-primary-color) 12%, transparent); color: var(--p-text-color); }
  34%, 100% { background: transparent; color: var(--p-text-muted-color); }
}

/* No motion: the first frame, every step plain */
@media (prefers-reduced-motion: reduce) {
  .stage *,
  .guide__step {
    animation: none !important;
  }
  .finger,
  .cursor {
    display: none;
  }
}
</style>
