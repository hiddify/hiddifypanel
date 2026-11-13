<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { detectPwaPlatform, desktopOsName, type PwaPlatform } from '@/shared/composables/usePwaInstall'

/**
 * How to install the panel as an app, as a looping animation of the browser's own controls: Safari on iPhone / iPad,
 * Chrome on Android, Chrome on a computer. The detected platform is shown first; the others are one tap away.
 */
/** The installed app's icon, drawn where the animation shows the app (home screen, install prompt, window title). */
const props = defineProps<{ icon?: string; ownShape?: boolean }>()
const iconStyle = computed(() => (props.icon ? { '--app-icon-img': `url("${props.icon}")` } : undefined))

const { t } = useI18n()
const detected = detectPwaPlatform()
const platform = ref<PwaPlatform>(detected)

const PLATFORMS: PwaPlatform[] = ['ios', 'android', 'desktop']
/** This panel's address: the install prompts show it under the app's name. */
const host = typeof window === 'undefined' ? '' : window.location.host
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
  <div class="guide" :class="{ 'guide--own-icon': ownShape }" :style="iconStyle">
    <div class="guide__tabs" role="tablist" :aria-label="t('pwa.guide.platform')">
      <button
        v-for="p in PLATFORMS"
        :key="p"
        type="button"
        role="tab"
        class="guide__tab"
        :class="[`guide__tab--${p}`, { 'guide__tab--on': platform === p }]"
        :aria-selected="platform === p"
        :aria-label="tabLabel(p)"
        :title="tabLabel(p)"
        @click="platform = p"
      >
        <!-- Only the system's logo, in its own colors (the label is read out, and shows as a tooltip) -->
        <svg v-if="p === 'ios'" class="guide__os" viewBox="4.5 3 15 18" aria-hidden="true">
          <path fill="currentColor" d="M16.52,12.46a3.31,3.31,0,0,1,1.78-3,3.85,3.85,0,0,0-3-1.6c-1.27-.1-2.65.74-3.16.74s-1.77-.7-2.73-.7c-2,0-4.11,1.59-4.11,4.76a9,9,0,0,0,.51,2.9C6.25,16.84,7.9,20.05,9.62,20c.9,0,1.54-.64,2.71-.64s1.72.64,2.73.64c1.73,0,3.23-2.95,3.66-4.26a3.54,3.54,0,0,1-2.2-3.28Zm-2-5.87A3.37,3.37,0,0,0,15.35,4a3.79,3.79,0,0,0-2.42,1.25A3.41,3.41,0,0,0,12,7.81,3,3,0,0,0,14.5,6.59Z" />
        </svg>
        <svg v-else-if="p === 'android'" class="guide__os" viewBox="4 3 16 18" aria-hidden="true">
          <g fill="#3ddc84">
            <path d="M18.06,9.33a.94.94,0,0,0-.94.94v4.26a.94.94,0,0,0,1.88,0V10.27A.94.94,0,0,0,18.06,9.33Z" />
            <path d="M5.94,9.33a.94.94,0,0,0-.94.94v4.26a.94.94,0,0,0,1.88,0V10.27A.94.94,0,0,0,5.94,9.33Z" />
            <path d="M7.56,9.33v6.4A1.07,1.07,0,0,0,8.63,16.8h.68v2.27a.94.94,0,0,0,1.88,0h0V16.8h1.62v2.27a.94.94,0,0,0,1.88,0h0V16.8h.68a1.07,1.07,0,0,0,1.07-1.07V9.33Z" />
            <path d="M16.32,8a4.13,4.13,0,0,0-1.83-2.36l-.15-.09-.16-.08.18-.31.53-1A.14.14,0,0,0,14.84,4h0l-.07,0a.17.17,0,0,0-.13.07L14.1,5l-.17.31-.16-.07-.17-.06a4.88,4.88,0,0,0-3.2,0l-.16.06-.17.07L9.9,5l-.54-1a.14.14,0,0,0-.25.14l.53,1,.18.31-.16.08-.15.09A4.07,4.07,0,0,0,7.69,8a3.11,3.11,0,0,0-.13.8h8.88A3.6,3.6,0,0,0,16.32,8ZM10,7.47a.4.4,0,1,1,.4-.4A.4.4,0,0,1,10,7.47Zm4,0a.4.4,0,1,1,.4-.4A.4.4,0,0,1,14,7.47Z" />
          </g>
        </svg>
        <svg v-else class="guide__os" viewBox="0 0 18 18" aria-hidden="true">
          <rect x="0" y="0" width="8.5" height="8.5" fill="#f25022" />
          <rect x="9.5" y="0" width="8.5" height="8.5" fill="#7fba00" />
          <rect x="0" y="9.5" width="8.5" height="8.5" fill="#00a4ef" />
          <rect x="9.5" y="9.5" width="8.5" height="8.5" fill="#ffb900" />
        </svg>
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
          <div class="ios-add__app"><span class="app-icon" /><span class="app-name"><b>Hiddify</b><small>{{ host }}</small></span></div>
          <div class="ios-add__opt"><span>Open as Web App</span><i class="ios-add__switch" /></div>
        </div>
        <!-- After "Add": the home screen, with the app on it -->
        <div class="home">
          <span v-for="n in 5" :key="n" class="home__app" />
          <span class="home__app home__app--new"><span class="app-icon" /><b>Hiddify</b></span>
          <span v-for="n in 2" :key="`after-${n}`" class="home__app" />
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
          <div class="and-dialog__app"><span class="app-icon" /><span class="app-name"><b>Hiddify</b><small>{{ host }}</small></span></div>
          <div class="and-dialog__btns"><span>Cancel</span><span class="and-dialog__ok hit-3">Install</span></div>
        </div>
        <!-- After "Install": the home screen, with the app on it -->
        <div class="home">
          <span v-for="n in 5" :key="n" class="home__app" />
          <span class="home__app home__app--new"><span class="app-icon" /><b>Hiddify</b></span>
          <span v-for="n in 2" :key="`after-${n}`" class="home__app" />
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
          <div class="win-pop__app"><span class="app-icon" /><span class="app-name"><b>Hiddify</b><small>{{ host }}</small></span></div>
          <div class="win-pop__btns"><span class="win-pop__ok hit-2">Install</span><span>Cancel</span></div>
        </div>
        <div class="win-app">
          <div class="win-app__title"><span class="app-icon app-icon--tiny" /><b>Hiddify</b></div>
          <div class="page"><span class="page__bar page__bar--wide" /><span class="page__card" /></div>
        </div>
        <i class="pi pi-arrow-up-left cursor" />
      </div>
    </div>

    <!-- The steps, one at a time: only the step the scene is showing now, so the guide stays short -->
    <ol :key="`s-${platform}`" class="guide__steps" :class="`guide__steps--${steps.length}`">
      <li v-for="(s, i) in steps" :key="i" class="guide__step" :style="{ '--i': i }"><span class="guide__n">{{ i + 1 }}</span>{{ s }}</li>
    </ol>
    <!-- Which step of how many -->
    <div :key="`t-${platform}`" class="guide__ticks" :class="`guide__ticks--${steps.length}`" aria-hidden="true">
      <span v-for="(_, i) in steps" :key="i" class="guide__tick" :style="{ '--i': i }" />
    </div>
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
  gap: 0.45rem;
}
/* One tab per system: its logo in its own colors, on a very pale tint of its own */
.guide__tab {
  --tab: #8e8e93;
  flex: 1;
  display: grid;
  place-items: center;
  height: 2.5rem;
  padding: 0;
  border: 0;
  border-radius: 12px;
  background: color-mix(in srgb, var(--tab) 11%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--tab) 16%, transparent);
  color: var(--p-text-color);
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}
.guide__tab--ios {
  --tab: #8e8e93;
}
.guide__tab--android {
  --tab: #3ddc84;
}
.guide__tab--desktop {
  --tab: #00a4ef;
}
.guide__os {
  display: block;
  height: 1.35rem;
  width: auto;
  opacity: 0.6;
  transition: opacity 0.2s ease;
}
.guide__tab:hover .guide__os,
.guide__tab--on .guide__os {
  opacity: 1;
}
.guide__tab:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
/* The chosen one: a little more of its tint, and a ring in its color */
.guide__tab--on {
  background: color-mix(in srgb, var(--tab) 20%, transparent);
  box-shadow: inset 0 0 0 1.5px color-mix(in srgb, var(--tab) 70%, transparent);
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
  z-index: 6; /* over the home screen too */
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
  background: var(--app-icon-img, none) center / cover no-repeat,
    linear-gradient(135deg, var(--p-primary-400, #60a5fa), var(--p-primary-700, #1d4ed8));
}
.app-icon--tiny {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 0.2rem;
}
/* The panel's own icon is already cut to its shape: no corner radius, nothing behind it */
.guide--own-icon .app-icon {
  border-radius: 0;
  background: var(--app-icon-img) center / contain no-repeat;
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

/* The app in an install prompt: its name and, under it, its address (as the real prompts show) */
.app-name {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.3;
}
.app-name b,
.app-name small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.app-name b {
  font-size: 0.52rem;
  color: var(--p-text-color);
}
.app-name small {
  font-size: 0.4rem;
  color: var(--p-text-muted-color);
}
/* After the last tap on a phone: the home screen, with the app among the others */
.home {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  align-content: start;
  gap: 0.75rem 0.2rem;
  padding: 1.3rem 0.45rem 0;
  background: linear-gradient(165deg, color-mix(in srgb, var(--p-primary-color) 34%, var(--p-content-background)), color-mix(in srgb, var(--p-primary-color) 10%, var(--p-content-background)));
  opacity: 0;
  animation: home-4 var(--dur) infinite;
}
.stage--android .home {
  padding-top: 0.7rem;
  animation-name: home-3;
}
.home__app {
  justify-self: center;
  width: 1.2rem;
  height: 1.2rem;
  border-radius: 0.33rem;
  background: color-mix(in srgb, var(--p-text-color) 15%, transparent);
}
.home__app--new {
  position: relative;
  background: none;
  animation: home-new-4 var(--dur) infinite;
}
.stage--android .home__app--new {
  animation-name: home-new-3;
}
.home__app--new .app-icon {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 0.33rem;
}
.home__app--new b {
  position: absolute;
  top: calc(100% + 0.1rem);
  left: 50%;
  font-size: 0.34rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--p-text-color);
  transform: translateX(-50%);
}
@keyframes home-4 {
  0%, 91% { opacity: 0; }
  94%, 100% { opacity: 1; }
}
@keyframes home-3 {
  0%, 88% { opacity: 0; }
  91%, 100% { opacity: 1; }
}
@keyframes home-new-4 {
  0%, 92% { transform: scale(0.3); }
  96%, 100% { transform: scale(1); }
}
@keyframes home-new-3 {
  0%, 89% { transform: scale(0.3); }
  94%, 100% { transform: scale(1); }
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
/* "Open as Web App", on: the sheet's own switch */
.ios-add__opt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.15rem;
  padding: 0.25rem 0.3rem;
  border-radius: 6px;
  background: var(--p-content-hover-background);
  font-size: 0.42rem;
}
.ios-add__switch {
  position: relative;
  width: 0.8rem;
  height: 0.46rem;
  border-radius: 999px;
  background: #34c759;
}
.ios-add__switch::after {
  content: '';
  position: absolute;
  top: 0.05rem;
  right: 0.05rem;
  width: 0.36rem;
  height: 0.36rem;
  border-radius: 50%;
  background: #fff;
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
  84% { left: 84%; top: 13%; transform: scale(1); }
  87% { transform: scale(0.7); }
  90% { left: 84%; top: 13%; transform: scale(1); }
  98%, 100% { left: 70%; top: 60%; transform: scale(1); }
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
  animation: pop-3-phone var(--dur) infinite;
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
  78% { left: 76%; top: 66%; transform: scale(1); }
  82% { transform: scale(0.7); }
  86% { left: 76%; top: 66%; transform: scale(1); }
  97%, 100% { left: 50%; top: 70%; transform: scale(1); }
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
  font-size: 0.45rem;
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
  0%, 82% { background: transparent; }
  85%, 90% { background: color-mix(in srgb, var(--hit) 22%, transparent); }
  92%, 100% { background: transparent; }
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
/* The last sheet goes once "Add" is tapped: the home screen shows for the rest of the step */
@keyframes sheet-4 {
  0%, 72% { transform: translateY(110%); }
  77%, 90% { transform: translateY(0); }
  93%, 100% { transform: translateY(110%); }
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
/* On a phone the install dialog closes after "Install": the home screen shows for the rest of the step */
@keyframes pop-3-phone {
  0%, 62% { opacity: 0; transform: scale(0.9); }
  67%, 87% { opacity: 1; transform: scale(1); }
  90%, 100% { opacity: 0; transform: scale(0.9); }
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
  0%, 76% { outline: 0 solid transparent; }
  79%, 86% { outline: 3px solid color-mix(in srgb, var(--hit) 35%, transparent); }
  88%, 100% { outline: 0 solid transparent; }
}

/* --- the steps, lit in time with the scene --- */
/* One box for all the steps: they lie on top of each other and each shows only during its part of the scene. The
   box is as tall as the longest step, so nothing moves when the step changes. */
.guide__steps {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
  border-radius: 12px;
  background: color-mix(in srgb, var(--p-primary-color) 11%, transparent);
  overflow: hidden;
}
.guide__step {
  grid-area: 1 / 1;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0.65rem;
  font-size: 0.88rem;
  opacity: 0;
  animation: step-4 var(--dur) infinite ease-in-out backwards;
  animation-delay: calc(var(--dur) * var(--i) / 4);
}
.guide__steps--3 .guide__step {
  animation-name: step-3;
  animation-delay: calc(var(--dur) * var(--i) / 3);
}
/* Should the animation not run, the first step is there */
.guide__step:first-child {
  opacity: 1;
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
/* A step comes up into the box as the one before it leaves upward: the two cross for a moment (its own part of the
   scene is the first quarter, or third, of its timeline). */
@keyframes step-4 {
  0% { opacity: 0; transform: translateY(0.6rem); }
  4.5%, 25% { opacity: 1; transform: none; }
  29.5%, 100% { opacity: 0; transform: translateY(-0.6rem); }
}
@keyframes step-3 {
  0% { opacity: 0; transform: translateY(0.6rem); }
  4.5%, 33.33% { opacity: 1; transform: none; }
  37.83%, 100% { opacity: 0; transform: translateY(-0.6rem); }
}
/* Under the box: a mark for each step, the current one long */
.guide__ticks {
  display: flex;
  justify-content: center;
  gap: 0.3rem;
  margin-top: -0.3rem;
}
.guide__tick {
  width: 0.4rem;
  height: 0.25rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-text-color) 16%, transparent);
  animation: tick-4 var(--dur) infinite ease-in-out backwards;
  animation-delay: calc(var(--dur) * var(--i) / 4);
}
.guide__ticks--3 .guide__tick {
  animation-name: tick-3;
  animation-delay: calc(var(--dur) * var(--i) / 3);
}
.guide__tick:first-child {
  width: 1.4rem;
  background: var(--p-primary-color);
}
@keyframes tick-4 {
  0% { width: 0.4rem; background: color-mix(in srgb, var(--p-text-color) 16%, transparent); }
  4.5%, 25% { width: 1.4rem; background: var(--p-primary-color); }
  29.5%, 100% { width: 0.4rem; background: color-mix(in srgb, var(--p-text-color) 16%, transparent); }
}
@keyframes tick-3 {
  0% { width: 0.4rem; background: color-mix(in srgb, var(--p-text-color) 16%, transparent); }
  4.5%, 33.33% { width: 1.4rem; background: var(--p-primary-color); }
  37.83%, 100% { width: 0.4rem; background: color-mix(in srgb, var(--p-text-color) 16%, transparent); }
}

/* Short screens: a smaller scene, step by step, so the step and the dialog's buttons fit */
@media (max-height: 640px) {
  .stage {
    height: 10.4rem;
  }
  .stage > * {
    zoom: 0.8;
  }
}
@media (max-height: 560px) {
  .guide {
    gap: 0.5rem;
  }
  .guide__ticks {
    margin-top: -0.15rem;
  }
  .stage {
    height: 9.1rem;
  }
  .stage > * {
    zoom: 0.7;
  }
}
@media (max-height: 480px) {
  .stage {
    height: 8rem;
  }
  .stage > * {
    zoom: 0.61;
  }
}
/* No motion: the first frame of the scene, and every step in a plain list */
@media (prefers-reduced-motion: reduce) {
  .stage *,
  .guide__step {
    animation: none !important;
  }
  .guide__steps {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    background: none;
  }
  .guide__step {
    padding: 0.4rem 0.55rem;
    opacity: 1;
  }
  .guide__ticks {
    display: none;
  }
  .guide__tick {
    animation: none !important;
  }
  .finger,
  .cursor {
    display: none;
  }
}
</style>
