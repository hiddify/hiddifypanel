<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'
import HiddifyQrCode from '@/shared/components/HiddifyQrCode.vue'
import PackageChips from '@/features/inbox/components/PackageChips.vue'
import type { FreeTest } from '@/features/inbox/api'

/** This admin's free test: the package people get, whether it is on, and the link to share. */
const props = defineProps<{ free: FreeTest }>()
defineEmits<{ edit: [] }>()

const { t } = useI18n()
const toast = useToast()
const qrVisible = ref(false)
const pkg = computed(() => props.free.package)

async function copy() {
  if (!props.free.link) return
  try {
    await navigator.clipboard.writeText(props.free.link)
    toast.add({ severity: 'success', summary: t('inbox.free.copied'), life: 2000 })
  } catch {
    toast.add({ severity: 'warn', summary: t('inbox.free.copyFailed'), detail: props.free.link, life: 6000 })
  }
}
</script>

<template>
  <section class="ft-card" :class="{ 'ft-card--off': !pkg.enabled }">
    <div class="ft-head">
      <span class="ft-icon" aria-hidden="true"><i class="pi pi-gift" /></span>
      <div class="ft-title">
        <h3>
          {{ t('inbox.free.title') }}
          <span class="ft-state" :class="pkg.enabled ? 'ft-state--on' : 'ft-state--off'">{{ pkg.enabled ? t('inbox.free.on') : t('inbox.free.off') }}</span>
        </h3>
        <p v-if="pkg.enabled">
          <i class="pi" :class="pkg.approval === 'auto' ? 'pi-bolt' : 'pi-user-edit'" />
          {{ pkg.approval === 'auto' ? t('inbox.free.auto') : t('inbox.free.manual') }}
          <template v-if="free.inherited_from"> · {{ t('inbox.free.inherited', { name: free.inherited_from }) }}</template>
        </p>
        <p v-else>{{ free.can_edit ? t('inbox.free.offHint') : t('inbox.free.offNoEdit') }}</p>
      </div>
      <Button
        v-if="free.can_edit"
        :label="pkg.enabled ? t('inbox.free.edit') : t('inbox.free.setup')"
        :icon="pkg.enabled ? 'pi pi-pencil' : 'pi pi-play'"
        :severity="pkg.enabled ? 'secondary' : undefined"
        :outlined="pkg.enabled"
        size="small"
        class="ft-edit"
        @click="$emit('edit')"
      />
    </div>

    <template v-if="pkg.enabled">
      <PackageChips :days="pkg.days" :usage-gb="pkg.usage_gb" tag class="ft-chips" />

      <div v-if="free.link" class="ft-link">
        <span class="ft-link__label">{{ t('inbox.free.linkLabel') }}</span>
        <div class="ft-link__row">
          <button type="button" class="ft-link__url" dir="ltr" :title="t('inbox.free.copy')" @click="copy">
            <i class="pi pi-link" /><span>{{ free.link }}</span>
          </button>
          <Button icon="pi pi-copy" severity="secondary" outlined :aria-label="t('inbox.free.copy')" :title="t('inbox.free.copy')" @click="copy" />
          <Button icon="pi pi-qrcode" severity="secondary" outlined :aria-label="t('inbox.free.qr')" :title="t('inbox.free.qr')" @click="qrVisible = true" />
          <Button as="a" :href="free.link" target="_blank" rel="noopener" icon="pi pi-send" severity="secondary" outlined :aria-label="t('inbox.free.openTelegram')" :title="t('inbox.free.openTelegram')" />
        </div>
        <small>{{ t('inbox.free.shareHint') }}</small>
      </div>
      <p v-if="!free.has_room" class="ft-warn"><i class="pi pi-exclamation-triangle" />{{ t('inbox.free.noRoom') }}</p>
    </template>

    <Dialog v-model:visible="qrVisible" modal dismissable-mask :draggable="false" :header="t('inbox.free.linkLabel')" :style="{ width: '22rem' }" :breakpoints="{ '575px': 'calc(100vw - 2rem)' }">
      <div v-if="free.link" class="ft-qr">
        <HiddifyQrCode :value="free.link" :size="220" />
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
.ft-link {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
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
  border: 1px dashed var(--surface-border);
  border-radius: 10px;
  background: var(--surface-ground);
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
  color: var(--text-color-secondary);
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
  .ft-edit {
    width: 100%;
  }
  .ft-link__row {
    flex-wrap: wrap;
  }
  .ft-link__url {
    flex-basis: 100%;
    min-height: 2.6rem;
  }
  .ft-link__row :deep(.p-button) {
    flex: 1;
  }
}
</style>
