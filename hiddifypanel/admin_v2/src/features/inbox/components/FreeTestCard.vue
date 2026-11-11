<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import HiddifyQrCode from '@/shared/components/HiddifyQrCode.vue'
import PackageChips from '@/features/inbox/components/PackageChips.vue'
import { inboxApi, type FreePackage, type FreeTest } from '@/features/inbox/api'

/** One of this admin's free test packages. The default one is what the bot offers: it carries the link to share; the
 *  others wait (`multi`: the admin has several, each can be made the default). */
const props = defineProps<{ free: FreeTest; pkg: FreePackage; isDefault: boolean; multi: boolean }>()
const emit = defineEmits<{ edit: [pkg: FreePackage]; saved: [free: FreeTest] }>()

const { t } = useI18n()
const toast = useToast()
const dangerConfirm = useDangerConfirm()
const qrVisible = ref(false)
const deleting = ref(false)
const defaulting = ref(false)
const pkg = computed(() => props.pkg)
/** The default package's public link; another package's private one. */
const link = computed(() => (props.isDefault ? props.free.link : (props.free.private_links[props.pkg.id ?? ''] ?? null)))
/** One of this admin's own packages (a parent's one is not theirs to delete). */
const isOwn = computed(() => !!props.pkg.id && props.free.packages.some((p) => p.id === props.pkg.id))
const canDelete = computed(() => props.free.can_edit && isOwn.value && (props.multi || props.pkg.enabled))

async function makeDefault() {
  defaulting.value = true
  try {
    emit('saved', await inboxApi.savePackages(props.free.packages, props.pkg.id ?? null))
    toast.add({ severity: 'success', summary: t('inbox.free.madeDefault'), life: 2500 })
  } catch (err) {
    toast.add({ severity: 'error', summary: t('inbox.dialog.saveFailed'), detail: apiErrorMessage(err), life: 5000 })
  } finally {
    defaulting.value = false
  }
}

function askDelete() {
  dangerConfirm({
    header: t('inbox.free.deleteTitle'),
    // The last package: the free test turns off. One of several: the others stay (the first one becomes the default).
    message: props.multi ? t('inbox.free.deleteConfirmOne') : t('inbox.free.deleteConfirm'),
    acceptLabel: t('inbox.free.delete'),
    accept: async () => {
      deleting.value = true
      try {
        const rest = props.free.packages.filter((p) => p.id !== props.pkg.id)
        emit('saved', await inboxApi.savePackages(rest, props.isDefault ? null : props.free.default_id))
        toast.add({ severity: 'success', summary: t('inbox.free.deleted'), life: 2500 })
      } catch (err) {
        toast.add({ severity: 'error', summary: t('inbox.free.deleteFailed'), detail: apiErrorMessage(err), life: 5000 })
      } finally {
        deleting.value = false
      }
    },
  })
}

async function copy() {
  if (!link.value) return
  try {
    await navigator.clipboard.writeText(link.value)
    toast.add({ severity: 'success', summary: t('inbox.free.copied'), life: 2000 })
  } catch {
    toast.add({ severity: 'warn', summary: t('inbox.free.copyFailed'), detail: link.value, life: 6000 })
  }
}
</script>

<template>
  <section class="ft-card" :class="{ 'ft-card--off': isDefault && !pkg.enabled, 'ft-card--default': multi && isDefault, 'ft-card--private': multi && !isDefault }">
    <div class="ft-head">
      <span class="ft-icon" aria-hidden="true"><i class="pi pi-gift" /></span>
      <div class="ft-title">
        <h3>
          {{ t('inbox.free.title') }}
          <span v-if="multi && isDefault" class="ft-state ft-state--default"><i class="pi pi-star-fill" />{{ t('inbox.free.default') }}</span>
          <span v-if="isDefault" class="ft-state" :class="pkg.enabled ? 'ft-state--on' : 'ft-state--off'">{{ pkg.enabled ? t('inbox.free.on') : t('inbox.free.off') }}</span>
          <span v-else class="ft-state ft-state--private" :title="t('inbox.free.standbyHint')"><i class="pi pi-lock" />{{ t('inbox.free.standby') }}</span>
        </h3>
        <p v-if="pkg.enabled || !isDefault">
          <i class="pi" :class="pkg.approval === 'auto' ? 'pi-bolt' : 'pi-user-edit'" />
          {{ pkg.approval === 'auto' ? t('inbox.free.auto') : t('inbox.free.manual') }}
          <template v-if="free.inherited_from"> · {{ t('inbox.free.inherited', { name: free.inherited_from }) }}</template>
        </p>
        <p v-else>{{ free.can_edit ? t('inbox.free.offHint') : t('inbox.free.offNoEdit') }}</p>
      </div>
      <div v-if="free.can_edit" class="ft-actions">
        <Button
          :label="isDefault && !pkg.enabled ? t('inbox.free.setup') : t('inbox.free.edit')"
          :icon="isDefault && !pkg.enabled ? 'pi pi-play' : 'pi pi-pencil'"
          :severity="isDefault && !pkg.enabled ? undefined : 'secondary'"
          :outlined="!isDefault || pkg.enabled"
          size="small"
          class="ft-edit"
          @click="emit('edit', pkg)"
        />
        <Button
          v-if="multi && !isDefault && isOwn"
          :label="t('inbox.free.makeDefault')"
          icon="pi pi-star"
          severity="secondary"
          outlined
          size="small"
          :loading="defaulting"
          @click="makeDefault"
        />
        <Button
          v-if="canDelete"
          :label="t('inbox.free.delete')"
          icon="pi pi-trash"
          severity="danger"
          outlined
          size="small"
          class="ft-delete"
          :title="t('inbox.free.deleteTitle')"
          :loading="deleting"
          @click="askDelete"
        />
      </div>
    </div>

    <template v-if="pkg.enabled || !isDefault">
      <PackageChips :days="pkg.days" :usage-gb="pkg.usage_gb" tag :approval="pkg.approval" class="ft-chips" />

      <!-- The default package: the public link, what everyone in the bot gets. Another one: its private link -->
      <div v-if="link" class="ft-link">
        <span class="ft-link__label">{{ isDefault ? t('inbox.free.linkLabel') : t('inbox.free.privateLinkLabel') }}</span>
        <div class="ft-link__row">
          <button type="button" class="ft-link__url" dir="ltr" :title="t('inbox.free.copy')" @click="copy">
            <i class="pi" :class="isDefault ? 'pi-link' : 'pi-lock'" /><span>{{ link }}</span>
          </button>
        </div>
        <!-- Each action says what it does: an icon alone was hard to tell apart -->
        <div class="ft-link__actions">
          <Button :label="t('inbox.free.copyShort')" icon="pi pi-copy" severity="secondary" outlined size="small" :title="t('inbox.free.copy')" @click="copy" />
          <Button :label="t('inbox.free.qr')" icon="pi pi-qrcode" severity="secondary" outlined size="small" @click="qrVisible = true" />
          <Button
            as="a"
            :href="link"
            target="_blank"
            rel="noopener"
            :label="t('inbox.free.openShort')"
            icon="pi pi-send"
            severity="secondary"
            outlined
            size="small"
            :title="t('inbox.free.openTelegram')"
          />
        </div>
        <small>{{ isDefault ? t('inbox.free.shareHint') : t('inbox.free.privateHint') }}</small>
      </div>
      <p v-if="isDefault && !free.has_room" class="ft-warn"><i class="pi pi-exclamation-triangle" />{{ t('inbox.free.noRoom') }}</p>
    </template>

    <Dialog v-model:visible="qrVisible" modal dismissable-mask :draggable="false" :header="isDefault ? t('inbox.free.linkLabel') : t('inbox.free.privateLinkLabel')" :style="{ width: '22rem' }" :breakpoints="{ '575px': 'calc(100vw - 2rem)' }">
      <div v-if="link" class="ft-qr">
        <HiddifyQrCode :value="link" :size="220" />
        <PackageChips :days="pkg.days" :usage-gb="pkg.usage_gb" tag />
      </div>
    </Dialog>
  </section>
</template>

<style scoped>
.ft-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.1rem 1.25rem;
  border-radius: 18px;
  border: 1px solid var(--surface-border);
  background:
    radial-gradient(120% 140% at 100% 0%, color-mix(in srgb, var(--primary-color) 12%, transparent), transparent 60%),
    var(--surface-card);
}
.ft-card--off {
  background: var(--surface-card);
}
/* The default package (when there are several): a warm gold, so it stands out from the ones waiting. */
.ft-card--default {
  --ft-gold: var(--p-amber-500);
  border-color: color-mix(in srgb, var(--ft-gold) 45%, var(--surface-border));
  background:
    radial-gradient(120% 140% at 100% 0%, color-mix(in srgb, var(--ft-gold) 16%, transparent), transparent 60%),
    linear-gradient(color-mix(in srgb, var(--ft-gold) 5%, var(--surface-card)), color-mix(in srgb, var(--ft-gold) 5%, var(--surface-card)));
  box-shadow: 0 10px 28px -18px color-mix(in srgb, var(--ft-gold) 70%, transparent);
}
.ft-head {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  flex-wrap: wrap;
}
.ft-icon {
  display: grid;
  place-items: center;
  width: 2.9rem;
  height: 2.9rem;
  flex: none;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--primary-color), color-mix(in srgb, var(--primary-color) 60%, var(--p-purple-500, #a855f7)));
  color: var(--primary-contrast-color);
  font-size: 1.3rem;
}
.ft-card--off .ft-icon {
  background: var(--p-content-hover-background, var(--surface-hover));
  color: var(--text-color-secondary);
}
.ft-card--default .ft-icon {
  background: linear-gradient(135deg, var(--p-amber-400), var(--p-orange-500));
  color: #fff;
}
/* A private package: the violet of its "Private" tag. */
.ft-card--private .ft-icon {
  background: linear-gradient(135deg, var(--p-violet-400), var(--p-violet-600));
  color: #fff;
}
/* Alive: the tile floats softly and the gift rocks a little; the default one also breathes a gold glow. */
.ft-card:not(.ft-card--off) .ft-icon {
  animation: ft-float 3.4s ease-in-out infinite;
}
.ft-card:not(.ft-card--off) .ft-icon .pi {
  animation: ft-rock 3.4s ease-in-out infinite;
}
.ft-card--default .ft-icon {
  animation:
    ft-float 3.4s ease-in-out infinite,
    ft-glow 2.8s ease-in-out infinite;
}
@keyframes ft-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-3px);
  }
}
@keyframes ft-rock {
  0%,
  60%,
  100% {
    transform: rotate(0) scale(1);
  }
  70% {
    transform: rotate(-10deg) scale(1.08);
  }
  80% {
    transform: rotate(8deg) scale(1.08);
  }
  90% {
    transform: rotate(-3deg) scale(1.02);
  }
}
@keyframes ft-glow {
  0%,
  100% {
    box-shadow: 0 4px 12px -4px color-mix(in srgb, var(--p-amber-500) 45%, transparent);
  }
  50% {
    box-shadow:
      0 6px 18px -4px color-mix(in srgb, var(--p-amber-500) 70%, transparent),
      0 0 0 4px color-mix(in srgb, var(--p-amber-400) 22%, transparent);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ft-icon,
  .ft-icon .pi {
    animation: none !important;
  }
}
.ft-title {
  flex: 1;
  min-width: 12rem;
}
.ft-title h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 1.1rem;
}
.ft-title p {
  margin: 0.2rem 0 0;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}
.ft-title p .pi {
  font-size: 0.8rem;
  margin-inline-end: 0.2rem;
}
.ft-state {
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
}
.ft-state--on {
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 16%, transparent);
  color: var(--p-green-600, #16a34a);
}
.ft-state--off {
  background: var(--p-content-hover-background, var(--surface-hover));
  color: var(--text-color-secondary);
}
.ft-state--private {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background: color-mix(in srgb, var(--p-violet-500) 14%, transparent);
  color: var(--p-violet-600, #7c3aed);
}
.ft-state--private .pi {
  font-size: 0.65rem;
}
.ft-state--default {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background: color-mix(in srgb, var(--p-amber-500) 16%, transparent);
  color: var(--p-amber-700, #b45309);
}
.ft-state--default .pi {
  font-size: 0.65rem;
}
.ft-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
/* Outlines that show on every theme: the frosted Caddy and Liquid themes make the default ones near-white. */
.ft-card :deep(.p-button-outlined.p-button-secondary) {
  border-color: color-mix(in srgb, var(--p-text-color) 22%, transparent);
  background: color-mix(in srgb, var(--p-content-background) 55%, transparent);
  color: var(--p-text-color);
}
.ft-card :deep(.p-button-outlined.p-button-secondary:not(:disabled):hover) {
  border-color: color-mix(in srgb, var(--p-text-color) 35%, transparent);
  background: color-mix(in srgb, var(--p-text-color) 6%, var(--p-content-background));
}
.ft-delete {
  background: color-mix(in srgb, var(--p-content-background) 55%, transparent);
}
.ft-link {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.ft-link__actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}
.ft-link__actions :deep(.p-button) {
  min-width: 0;
  text-decoration: none;
}
.ft-link__actions :deep(.p-button-label) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ft-link__label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}
.ft-link__row {
  display: flex;
  gap: 0.4rem;
}
.ft-link__url {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
  padding: 0 0.8rem;
  min-height: 2.6rem;
  border: 1px dashed color-mix(in srgb, var(--p-text-color) 28%, transparent);
  border-radius: 10px;
  background: color-mix(in srgb, var(--p-content-background) 55%, transparent);
  color: var(--text-color);
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.85rem;
  cursor: pointer;
  text-align: start;
}
.ft-link__url:hover {
  border-color: var(--primary-color);
}
.ft-link__url span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ft-link small {
  margin-top: 0.15rem;
  color: var(--text-color-secondary);
  line-height: 1.45;
}
.ft-warn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  color: var(--p-orange-500, #f97316);
  font-size: 0.88rem;
}
.ft-qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding-bottom: 0.5rem;
}
@media (max-width: 575px) {
  .ft-actions {
    width: 100%;
  }
  .ft-edit {
    flex: 1;
  }
}
</style>
