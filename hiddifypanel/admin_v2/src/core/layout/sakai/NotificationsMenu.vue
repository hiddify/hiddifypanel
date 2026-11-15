<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Popover from 'primevue/popover'
import { noticeKey, usePanelNotifications, type PanelNoticeSeverity } from './composables/usePanelNotifications'
import { iconizeHtml } from '@/shared/utils/emoji-icons'
import UpdateGlyph from '@/shared/components/UpdateGlyph.vue'

/** Top bar: the panel's notices (default domain, SSH password login, …) behind a bell, instead of banners above
 *  every page. Shown only while there are notices; a blinking red dot while some have not been seen yet. */
const { t } = useI18n()
const { visibleNotices, unseenNotices, unseenCount, unseenUpdate, unseenOther, dismiss, markAllSeen } = usePanelNotifications()

const ICON: Record<PanelNoticeSeverity, string> = {
  error: 'pi-times-circle',
  warn: 'pi-exclamation-triangle',
  info: 'pi-info-circle',
  success: 'pi-check-circle',
  update: 'pi-arrow-circle-up',
}

const panel = ref<InstanceType<typeof Popover> | null>(null)
const open = ref(false)
/** The notices that were new when the list opened: marked "new" until it closes. */
const freshKeys = ref<Set<string>>(new Set())

const label = computed(() => (unseenCount.value ? t('notifications.unread', { n: unseenCount.value }, unseenCount.value) : t('notifications.title')))

function toggle(event: Event) {
  panel.value?.toggle(event)
}

function onShow() {
  open.value = true
  freshKeys.value = new Set(unseenNotices.value.map(noticeKey))
  markAllSeen()
}

function onHide() {
  open.value = false
  freshKeys.value = new Set()
}

// The last notice removed: nothing left to show.
watch(
  () => visibleNotices.value.length,
  (count) => {
    if (!count) panel.value?.hide()
  },
)
</script>

<template>
  <button
    v-if="visibleNotices.length"
    type="button"
    class="layout-topbar-action notifications-trigger"
    :class="{ 'layout-topbar-action--active': open }"
    :aria-label="label"
    aria-haspopup="dialog"
    :aria-expanded="open"
    @click="toggle"
  >
    <i class="pi pi-bell" />
    <!-- not a <span>: the topbar hides spans in its buttons on desktop (they are the mobile menu's labels) -->
    <!-- red: something not seen yet; green: a new panel version; both side by side when there are both -->
    <b v-if="unseenCount" class="notifications-dots" aria-hidden="true">
      <b v-if="unseenUpdate" class="notifications-dot notifications-dot--update" />
      <b v-if="unseenOther" class="notifications-dot" />
    </b>
  </button>

  <Popover ref="panel" class="notifications-popover" @show="onShow" @hide="onHide">
    <div class="notifications" role="dialog" :aria-label="t('notifications.title')">
      <header class="notifications__head">
        <span class="notifications__title"><i class="pi pi-bell" />{{ t('notifications.title') }}</span>
        <span class="notifications__count">{{ visibleNotices.length }}</span>
      </header>
      <TransitionGroup name="notifications-item" tag="ul" class="notifications__list">
        <li v-for="notice in visibleNotices" :key="noticeKey(notice)" class="notifications__item" :class="[`notifications__item--${notice.severity}`, { 'notifications__item--new': freshKeys.has(noticeKey(notice)) }]">
          <template v-if="notice.severity === 'update' && notice.version">
            <UpdateGlyph kind="new" size="2.1rem" class="notifications__glyph" />
            <div class="notifications__body">
              <span v-if="freshKeys.has(noticeKey(notice))" class="notifications__new notifications__new--update">{{ t('notifications.new') }}</span>
              <p class="notifications__update-title">{{ t('notifications.update.heading') }}</p>
              <p class="notifications__versions">
                <span class="notifications__ver notifications__ver--old" dir="ltr">{{ notice.version.current }}</span>
                <svg viewBox="0 0 20 10" class="notifications__arrow" aria-hidden="true">
                  <path d="M1 5h16M13 1.5 17 5l-4 3.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <span class="notifications__ver notifications__ver--new" dir="ltr">{{ notice.version.latest }}</span>
              </p>
              <RouterLink :to="{ name: 'apply' }" class="notifications__cta" @click="panel?.hide()">
                {{ t('notifications.update.cta') }}
                <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3.5 10.5 8 6 12.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
              </RouterLink>
            </div>
          </template>
          <template v-else>
            <i :class="['pi', ICON[notice.severity], 'notifications__icon']" aria-hidden="true" />
            <div class="notifications__body">
              <span v-if="freshKeys.has(noticeKey(notice))" class="notifications__new">{{ t('notifications.new') }}</span>
              <!-- eslint-disable-next-line vue/no-v-html -- the panel's own notice HTML, as in the banners before -->
              <div class="notifications__text" v-html="iconizeHtml(notice.summary)" />
              <!-- eslint-disable-next-line vue/no-v-html -- idem -->
              <p v-if="notice.detail" class="notifications__detail" v-html="iconizeHtml(notice.detail)" />
            </div>
          </template>
          <button type="button" class="notifications__close" :aria-label="t('notifications.dismiss')" v-tooltip.left="t('notifications.dismiss')" @click="dismiss(notice)">
            <i class="pi pi-times" />
          </button>
        </li>
      </TransitionGroup>
    </div>
  </Popover>
</template>

<style scoped>
.layout-topbar-action--active {
  color: var(--topbar-text, #fff);
  background: var(--topbar-hover, rgb(255 255 255 / 14%));
}
.notifications-trigger {
  position: relative;
}
/* The dots: blink while there is something not seen yet (green: a new version, red: the rest), side by side */
.notifications-dots {
  position: absolute;
  top: 0.45rem;
  inset-inline-end: 0.3rem;
  display: flex;
  gap: 0.15rem;
}
.notifications-dot {
  display: block;
  position: relative;
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 0 2px var(--p-primary-600, #2563eb);
  animation: notifications-blink 1.2s ease-in-out infinite;
}
.notifications-dot::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: #ef4444;
  animation: notifications-ping 1.6s cubic-bezier(0, 0, 0.2, 1) infinite;
}
.notifications {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: min(24rem, calc(100vw - 2.5rem));
}
.notifications__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.notifications__title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-weight: 600;
}
.notifications__title i {
  color: var(--p-primary-color);
}
.notifications__count {
  min-width: 1.5rem;
  padding: 0 0.45rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-align: center;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgb(127 127 127 / 12%));
}
.notifications__list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: min(60vh, 26rem);
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}
.notifications__item {
  --notice: var(--p-blue-500, #3b82f6);
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.65rem 0.6rem 0.65rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-inline-start: 3px solid var(--notice);
  border-radius: 12px;
  background: color-mix(in srgb, var(--notice) 7%, transparent);
}
.notifications__item--warn {
  --notice: var(--p-amber-500, #f59e0b);
}
.notifications__item--error {
  --notice: var(--p-red-500, #ef4444);
}
.notifications__item--success {
  --notice: var(--p-green-500, #22c55e);
}
.notifications__item--new {
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--notice) 35%, transparent);
}
.notifications__icon {
  margin-top: 0.15rem;
  color: var(--notice);
}
.notifications__body {
  flex: 1;
  min-width: 0;
  font-size: 0.86rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}
.notifications__new {
  display: inline-block;
  margin-bottom: 0.2rem;
  padding: 0 0.4rem;
  border-radius: 6px;
  font-size: 0.68rem;
  font-weight: 700;
  color: #fff;
  background: #ef4444;
}
.notifications__text :deep(a),
.notifications__detail :deep(a) {
  color: var(--p-primary-color);
}
.notifications__detail {
  margin: 0.35rem 0 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.notifications__close {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 1.6rem;
  height: 1.6rem;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.notifications__close:hover {
  color: var(--p-text-color);
  background: var(--p-content-hover-background, rgb(127 127 127 / 12%));
}
.notifications__close:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 1px;
}
.notifications-item-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.notifications-item-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
.notifications-dot--update,
.notifications-dot--update::after {
  background: #22c55e;
}
.notifications-dot--update {
  animation-delay: 0.6s;
}
.notifications-dot--update::after {
  animation-delay: 0.6s;
}
/* a new panel version: a green card of its own */
.notifications__item--update {
  --notice: #22c55e;
  align-items: center;
  border-inline-start-width: 1px;
  background: radial-gradient(120% 140% at 0% 0%, color-mix(in srgb, #22c55e 18%, transparent), transparent 60%), color-mix(in srgb, #22c55e 6%, var(--p-content-background));
}
html[dir='rtl'] .notifications__item--update {
  background: radial-gradient(120% 140% at 100% 0%, color-mix(in srgb, #22c55e 18%, transparent), transparent 60%), color-mix(in srgb, #22c55e 6%, var(--p-content-background));
}
.notifications__glyph {
  filter: drop-shadow(0 4px 8px rgb(22 163 74 / 35%));
}
.notifications__new--update {
  background: #16a34a;
}
.notifications__update-title {
  margin: 0;
  font-weight: 650;
}
.notifications__versions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0.3rem 0 0.45rem;
}
.notifications__ver {
  padding: 0.05rem 0.5rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}
.notifications__ver--old {
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgb(127 127 127 / 12%));
}
.notifications__ver--new {
  color: #fff;
  background: linear-gradient(180deg, #4ade80, #16a34a);
  box-shadow: 0 3px 8px -3px rgb(22 163 74 / 60%);
}
.notifications__arrow {
  width: 1.1rem;
  color: #16a34a;
}
html[dir='rtl'] .notifications__arrow,
html[dir='rtl'] .notifications__cta svg {
  transform: scaleX(-1);
}
.notifications__cta {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.8rem;
  font-weight: 650;
  color: #16a34a;
  text-decoration: none;
}
.notifications__cta svg {
  width: 0.85rem;
  height: 0.85rem;
  transition: translate 0.25s cubic-bezier(0.32, 0.72, 0, 1);
}
.notifications__cta:hover svg {
  translate: 3px 0;
}
html.app-dark .notifications__cta,
html.app-dark .notifications__arrow {
  color: #4ade80;
}
@keyframes notifications-blink {
  50% {
    opacity: 0.35;
  }
}
@keyframes notifications-ping {
  75%,
  100% {
    transform: scale(2.2);
    opacity: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .notifications-dot,
  .notifications-dot::after {
    animation: none;
  }
}
</style>
