<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Popover from 'primevue/popover'
import { noticeKey, usePanelNotifications, type PanelNoticeSeverity } from './composables/usePanelNotifications'

/** Top bar: the panel's notices (default domain, SSH password login, …) behind a bell, instead of banners above
 *  every page. Shown only while there are notices; a blinking red dot while some have not been seen yet. */
const { t } = useI18n()
const { visibleNotices, unseenNotices, unseenCount, dismiss, markAllSeen } = usePanelNotifications()

const ICON: Record<PanelNoticeSeverity, string> = {
  error: 'pi-times-circle',
  warn: 'pi-exclamation-triangle',
  info: 'pi-info-circle',
  success: 'pi-check-circle',
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
    <b v-if="unseenCount" class="notifications-dot" aria-hidden="true" />
  </button>

  <Popover ref="panel" class="notifications-popover" @show="onShow" @hide="onHide">
    <div class="notifications" role="dialog" :aria-label="t('notifications.title')">
      <header class="notifications__head">
        <span class="notifications__title"><i class="pi pi-bell" />{{ t('notifications.title') }}</span>
        <span class="notifications__count">{{ visibleNotices.length }}</span>
      </header>
      <TransitionGroup name="notifications-item" tag="ul" class="notifications__list">
        <li
          v-for="notice in visibleNotices"
          :key="noticeKey(notice)"
          class="notifications__item"
          :class="[`notifications__item--${notice.severity}`, { 'notifications__item--new': freshKeys.has(noticeKey(notice)) }]"
        >
          <i :class="['pi', ICON[notice.severity], 'notifications__icon']" aria-hidden="true" />
          <div class="notifications__body">
            <span v-if="freshKeys.has(noticeKey(notice))" class="notifications__new">{{ t('notifications.new') }}</span>
            <!-- eslint-disable-next-line vue/no-v-html -- the panel's own notice HTML, as in the banners before -->
            <div class="notifications__text" v-html="notice.summary" />
            <!-- eslint-disable-next-line vue/no-v-html -- idem -->
            <p v-if="notice.detail" class="notifications__detail" v-html="notice.detail" />
          </div>
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
/* The red dot: blinks while there is something not seen yet. */
.notifications-dot {
  display: block;
  position: absolute;
  top: 0.45rem;
  inset-inline-end: 0.45rem;
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
