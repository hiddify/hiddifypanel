<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

/**
 * Shown once per admin on the Users page (users_layout.guide_seen): pinning (from the tag circle), moving rows
 * and widening Usage, each as a small looping animation of the real controls.
 */
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ gotIt: [] }>()
const { t } = useI18n()

function gotIt() {
  visible.value = false
  emit('gotIt')
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :closable="false"
    :close-on-escape="false"
    :header="t('users.guide.title')"
    :style="{ width: 'min(40rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
    class="users-guide"
  >
    <p class="users-guide__intro">{{ t('users.guide.intro') }}</p>
    <ol class="users-guide__tips">
      <!-- 1. Pin: click the tag circle, "Pin" first in its menu, the row goes to the top -->
      <li class="users-guide__tip">
        <div class="scene scene--pin" dir="ltr" aria-hidden="true">
          <div class="row row--a"><span class="row__grip" /><span class="row__tag row__tag--blue" /><span class="row__name" /></div>
          <div class="row row--b"><span class="row__grip" /><span class="row__tag row__tag--empty" /><span class="row__name row__name--short" /></div>
          <div class="row row--c">
            <span class="row__grip" />
            <i class="pi pi-thumbtack row__pin" />
            <span class="row__tag row__tag--green row__tag--clicked" />
            <span class="row__name" />
          </div>
          <div class="menu">
            <div class="menu__item menu__item--pin"><i class="pi pi-thumbtack" />{{ t('tags.pin') }}</div>
            <div class="menu__item"><span class="row__tag row__tag--blue" /><span class="menu__bar" /></div>
            <div class="menu__item"><span class="row__tag row__tag--green" /><span class="menu__bar menu__bar--short" /></div>
          </div>
          <i class="pi pi-arrow-up-left cursor cursor--pin" />
        </div>
        <div class="users-guide__text">
          <b>{{ t('users.guide.pinTitle') }}</b>
          <p>{{ t('users.guide.pinText') }}</p>
        </div>
      </li>

      <!-- 2. Move: row 4 lifted by its handle and dropped into row 2 -->
      <li class="users-guide__tip">
        <div class="scene scene--drag" dir="ltr" aria-hidden="true">
          <div class="row row--1"><span class="row__grip" /><span class="row__num">1</span><span class="row__name" /></div>
          <div class="row row--2"><span class="row__grip" /><span class="row__num">2</span><span class="row__name row__name--short" /></div>
          <div class="row row--3"><span class="row__grip" /><span class="row__num">3</span><span class="row__name" /></div>
          <div class="row row--4"><span class="row__grip row__grip--held" /><span class="row__num">4</span><span class="row__name row__name--accent" /></div>
          <i class="pi pi-arrow-up-left cursor cursor--drag" />
        </div>
        <div class="users-guide__text">
          <b>{{ t('users.guide.dragTitle') }}</b>
          <p>{{ t('users.guide.dragText') }}</p>
        </div>
      </li>

      <!-- 3. Widen Usage: the Name|Usage edge dragged, Usage and its bars grow -->
      <li class="users-guide__tip">
        <div class="scene scene--resize" dir="ltr" aria-hidden="true">
          <div class="grid">
            <div class="grid__name">
              <span class="grid__head">{{ t('users.col.name') }}</span>
              <span class="row__name" />
              <span class="row__name row__name--short" />
            </div>
            <div class="grid__edge"><i class="pi pi-arrows-h" /></div>
            <div class="grid__usage">
              <span class="grid__head grid__head--accent">{{ t('users.col.usage') }}</span>
              <span class="bar"><span class="bar__fill" style="width: 45%" /></span>
              <span class="bar"><span class="bar__fill" style="width: 70%" /></span>
            </div>
          </div>
          <i class="pi pi-arrow-up-left cursor cursor--resize" />
        </div>
        <div class="users-guide__text">
          <b>{{ t('users.guide.resizeTitle') }}</b>
          <p>{{ t('users.guide.resizeText') }}</p>
        </div>
      </li>
    </ol>
    <template #footer>
      <Button :label="t('users.guide.gotIt')" icon="pi pi-check" autofocus @click="gotIt" />
    </template>
  </Dialog>
</template>

<style scoped>
.users-guide__intro {
  margin: 0 0 1rem;
  color: var(--p-text-muted-color);
}
.users-guide__tips {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.users-guide__tip {
  display: grid;
  grid-template-columns: 13rem 1fr;
  gap: 1rem;
  align-items: center;
  padding: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 14px;
}
.users-guide__text p {
  margin: 0.2rem 0 0;
  font-size: 0.88rem;
  line-height: 1.55;
  color: var(--p-text-muted-color);
}

/* --- the little scenes: real-looking rows, a pointer, looped --- */
.scene {
  --row-h: 1.45rem;
  --gap: 0.25rem;
  --step: calc(var(--row-h) + var(--gap));
  --accent: var(--p-primary-color);
  --line: color-mix(in srgb, var(--p-text-color) 16%, transparent);
  position: relative;
  overflow: hidden;
  border-radius: 10px;
  background: color-mix(in srgb, var(--p-text-color) 4%, transparent);
}
.scene--pin {
  height: calc(var(--step) * 3 + 0.5rem);
}
.scene--drag {
  height: calc(var(--step) * 4 + 0.5rem);
}
.scene--resize {
  height: 5.6rem;
}
.row {
  position: absolute;
  inset-inline: 0.35rem;
  height: var(--row-h);
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0 0.4rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 7px;
  background: var(--p-content-background);
}
.row__grip {
  width: 0.55rem;
  height: 0.45rem;
  flex: none;
  background: repeating-linear-gradient(var(--line) 0 1.5px, transparent 1.5px 3px);
}
.row__grip--held {
  background: repeating-linear-gradient(var(--accent) 0 1.5px, transparent 1.5px 3px);
}
.row__num {
  width: 0.7rem;
  font-size: 0.6rem;
  font-weight: 700;
  color: var(--p-text-muted-color);
  text-align: center;
}
.row__tag {
  width: 0.65rem;
  height: 0.65rem;
  flex: none;
  border-radius: 50%;
}
.row__tag--blue {
  background: #3b82f6;
}
.row__tag--green {
  background: #10b981;
}
.row__tag--empty {
  border: 1.5px solid var(--line);
}
.row__name {
  flex: 1;
  height: 0.38rem;
  border-radius: 999px;
  background: var(--line);
}
.row__name--short {
  flex: 0 0 45%;
}
.row__name--accent {
  background: color-mix(in srgb, var(--accent) 55%, transparent);
}
.row__pin {
  width: 0;
  overflow: hidden;
  font-size: 0.6rem;
  color: var(--accent);
  transform: rotate(-30deg);
}
.cursor {
  position: absolute;
  z-index: 5;
  font-size: 0.85rem;
  color: var(--p-text-color);
  filter: drop-shadow(0 1px 1px rgb(0 0 0 / 35%));
}

/* 1. Pin (6s): pointer → C's tag circle → menu → "Pin" → C slides to the top with the pin */
.scene--pin .row--a { top: 0.25rem; animation: pin-down 6s ease-in-out infinite; }
.scene--pin .row--b { top: calc(0.25rem + var(--step)); animation: pin-down 6s ease-in-out infinite; }
.scene--pin .row--c { top: calc(0.25rem + var(--step) * 2); animation: pin-up 6s ease-in-out infinite; }
.scene--pin .row__pin { animation: pin-icon 6s ease-in-out infinite; }
.scene--pin .row__tag--clicked { animation: pin-click 6s ease-in-out infinite; }
.menu {
  position: absolute;
  top: 0.3rem;
  left: 3.4rem;
  z-index: 4;
  width: 6.4rem;
  padding: 0.2rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px;
  background: var(--p-content-background);
  box-shadow: 0 8px 18px -10px rgb(0 0 0 / 45%);
  opacity: 0;
  transform-origin: bottom left;
  animation: pin-menu 6s ease-in-out infinite;
}
.menu__item {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.12rem 0.3rem;
  border-radius: 5px;
  font-size: 0.6rem;
  font-weight: 600;
}
.menu__item--pin {
  color: var(--accent);
  border-bottom: 1px solid var(--p-content-border-color);
  animation: pin-hover 6s ease-in-out infinite;
}
.menu__item--pin .pi {
  font-size: 0.55rem;
  transform: rotate(-30deg);
}
.menu__bar {
  flex: 1;
  height: 0.3rem;
  border-radius: 999px;
  background: var(--line);
}
.menu__bar--short {
  flex: 0 0 55%;
}
.cursor--pin { animation: pin-cursor 6s ease-in-out infinite; }
@keyframes pin-cursor {
  0%, 8% { left: 85%; top: 85%; transform: scale(1); }
  24% { left: 2.05rem; top: calc(0.45rem + var(--step) * 2); transform: scale(1); }
  27% { transform: scale(0.8); }
  30% { transform: scale(1); }
  42% { left: 4.4rem; top: 0.5rem; transform: scale(1); }
  45% { transform: scale(0.8); }
  48% { left: 4.4rem; top: 0.5rem; transform: scale(1); }
  62%, 100% { left: 85%; top: 85%; }
}
@keyframes pin-click {
  0%, 25% { box-shadow: 0 0 0 0 transparent; }
  28% { box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 35%, transparent); }
  34%, 100% { box-shadow: 0 0 0 0 transparent; }
}
@keyframes pin-menu {
  0%, 27% { opacity: 0; transform: scale(0.9); }
  31%, 47% { opacity: 1; transform: scale(1); }
  51%, 100% { opacity: 0; transform: scale(0.9); }
}
@keyframes pin-hover {
  0%, 38% { background: transparent; }
  42%, 100% { background: color-mix(in srgb, var(--accent) 14%, transparent); }
}
@keyframes pin-up {
  0%, 50% { transform: translateY(0); }
  62%, 92% { transform: translateY(calc(var(--step) * -2)); border-color: color-mix(in srgb, var(--accent) 45%, var(--p-content-border-color)); }
  100% { transform: translateY(0); }
}
@keyframes pin-down {
  0%, 50% { transform: translateY(0); }
  62%, 92% { transform: translateY(var(--step)); }
  100% { transform: translateY(0); }
}
@keyframes pin-icon {
  0%, 52% { width: 0; opacity: 0; }
  60%, 92% { width: 0.6rem; opacity: 1; }
  100% { width: 0; opacity: 0; }
}

/* 2. Move (5s): row 4 lifted by its handle, moved to row 2, rows 2–3 make room */
.scene--drag .row--1 { top: 0.25rem; }
.scene--drag .row--2 { top: calc(0.25rem + var(--step)); animation: drag-room 5s ease-in-out infinite; }
.scene--drag .row--3 { top: calc(0.25rem + var(--step) * 2); animation: drag-room 5s ease-in-out infinite; }
.scene--drag .row--4 { top: calc(0.25rem + var(--step) * 3); z-index: 2; animation: drag-row 5s ease-in-out infinite; }
.cursor--drag { animation: drag-cursor 5s ease-in-out infinite; }
@keyframes drag-cursor {
  0%, 6% { left: 85%; top: 88%; transform: scale(1); }
  20% { left: 0.7rem; top: calc(0.55rem + var(--step) * 3); transform: scale(1); }
  24% { left: 0.7rem; top: calc(0.55rem + var(--step) * 3); transform: scale(0.85); }
  60% { left: 0.7rem; top: calc(0.55rem + var(--step)); transform: scale(0.85); }
  66% { left: 0.7rem; top: calc(0.55rem + var(--step)); transform: scale(1); }
  80%, 100% { left: 85%; top: 88%; }
}
@keyframes drag-row {
  0%, 22% { transform: translateY(0); box-shadow: none; }
  26% { transform: translate(3px, -2px) rotate(-1deg); box-shadow: 0 8px 16px -8px rgb(0 0 0 / 45%); }
  60% { transform: translate(3px, calc(var(--step) * -2)) rotate(-1deg); box-shadow: 0 8px 16px -8px rgb(0 0 0 / 45%); }
  66%, 92% { transform: translateY(calc(var(--step) * -2)); box-shadow: none; }
  100% { transform: translateY(0); }
}
@keyframes drag-room {
  0%, 34% { transform: translateY(0); }
  56%, 92% { transform: translateY(var(--step)); }
  100% { transform: translateY(0); }
}

/* 3. Widen Usage (5s): the Name|Usage edge dragged left, Usage and its bars grow */
.grid {
  position: absolute;
  inset: 0.35rem;
  display: flex;
}
.grid__name,
.grid__usage {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0.3rem 0.4rem;
}
.grid__name {
  width: 62%;
  flex: none;
  animation: resize-name 5s ease-in-out infinite;
}
.grid__usage {
  flex: 1;
  min-width: 0;
  border-radius: 6px;
  background: color-mix(in srgb, var(--accent) 7%, transparent);
}
.grid__head {
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.grid__head--accent {
  color: var(--accent);
}
.grid__edge {
  position: relative;
  width: 2px;
  flex: none;
  background: color-mix(in srgb, var(--accent) 60%, transparent);
}
.grid__edge .pi {
  position: absolute;
  top: 40%;
  left: 50%;
  font-size: 0.6rem;
  color: var(--accent);
  transform: translate(-50%, -50%);
}
.bar {
  display: block;
  height: 0.45rem;
  border-radius: 999px;
  background: var(--line);
  overflow: hidden;
}
.bar__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #34d399, #10b981);
}
.cursor--resize { animation: resize-cursor 5s ease-in-out infinite; }
@keyframes resize-name {
  0%, 18% { width: 62%; }
  58%, 88% { width: 34%; }
  100% { width: 62%; }
}
@keyframes resize-cursor {
  0%, 4% { left: 85%; top: 80%; transform: scale(1); }
  16% { left: calc(62% + 0.3rem); top: 2.4rem; transform: scale(1); }
  20% { left: calc(62% + 0.3rem); top: 2.4rem; transform: scale(0.85); }
  58% { left: calc(34% + 0.3rem); top: 2.4rem; transform: scale(0.85); }
  64% { left: calc(34% + 0.3rem); top: 2.4rem; transform: scale(1); }
  78%, 100% { left: 85%; top: 80%; }
}

@media (max-width: 520px) {
  .users-guide__tip {
    grid-template-columns: 1fr;
  }
}
/* No motion: the scenes show their first frame */
@media (prefers-reduced-motion: reduce) {
  .scene *,
  .scene {
    animation: none !important;
  }
  .menu {
    display: none;
  }
}
</style>
