<script setup lang="ts">
/**
 * Why this panel could not talk to a node, in the panel's language: what happened, why, and what to do.
 * The technical text (the server's own words, without the node's secret path) is only behind "Copy technical details".
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'

const props = defineProps<{
  /** hutils.node.contact_error: auth, not_found, timeout, refused, dns, tls, gateway, not_panel, server_error, no_url, unknown */
  code?: string | null
  detail?: string | null
  /** What could not be done, above the explanation (e.g. the live charts) */
  title?: string
}>()

const { t, te } = useI18n()
const toast = useToast()

const ICON: Record<string, string> = {
  auth: 'pi pi-key',
  not_found: 'pi pi-map-marker',
  timeout: 'pi pi-clock',
  refused: 'pi pi-ban',
  dns: 'pi pi-globe',
  tls: 'pi pi-lock',
  gateway: 'pi pi-cloud',
  not_panel: 'pi pi-question-circle',
  server_error: 'pi pi-exclamation-triangle',
  no_url: 'pi pi-link',
}
const key = computed(() => (props.code && te(`nodes.contact.${props.code}.title`) ? props.code : 'unknown'))

async function copy() {
  if (!props.detail) return
  try {
    await navigator.clipboard.writeText(props.detail)
    toast.add({ severity: 'success', summary: t('nodes.errorCopied'), life: 4000 })
  } catch {
    toast.add({ severity: 'warn', summary: props.detail, life: 10000 })
  }
}
</script>

<template>
  <div class="ncerr" role="alert">
    <p v-if="title" class="ncerr__context">{{ title }}</p>
    <div class="ncerr__head">
      <span class="ncerr__icon" aria-hidden="true"><i :class="ICON[key] ?? 'pi pi-times'" /></span>
      <b>{{ t(`nodes.contact.${key}.title`) }}</b>
    </div>
    <p class="ncerr__why">{{ t(`nodes.contact.${key}.why`) }}</p>
    <div class="ncerr__fix">
      <span class="ncerr__label"><i class="pi pi-wrench" aria-hidden="true" />{{ t('nodes.errorFixTitle') }}</span>
      <p>{{ t(`nodes.contact.${key}.fix`) }}</p>
    </div>
    <div v-if="detail || $slots.actions" class="ncerr__foot">
      <slot name="actions" />
      <Button v-if="detail" type="button" :label="t('nodes.errorCopy')" icon="pi pi-copy" text size="small" class="ncerr__copy" @click="copy" />
    </div>
  </div>
</template>

<style scoped>
.ncerr {
  --err: var(--p-red-500, #ef4444);
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding: 0.8rem 0.9rem;
  border-radius: 14px;
  border: 1px solid color-mix(in srgb, var(--err) 32%, transparent);
  background: color-mix(in srgb, var(--err) 6%, var(--p-content-background));
  font-size: 0.85rem;
}
.ncerr__context {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.ncerr__head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  color: color-mix(in srgb, var(--err) 85%, var(--p-text-color));
}
.ncerr__icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 1.9rem;
  height: 1.9rem;
  border-radius: 10px;
  color: #fff;
  background: var(--err);
}
.ncerr__why {
  margin: 0;
  line-height: 1.7;
  color: var(--p-text-color);
}
.ncerr__fix {
  padding: 0.55rem 0.7rem;
  border-radius: 10px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.ncerr__fix p {
  margin: 0.3rem 0 0;
  line-height: 1.7;
}
.ncerr__label {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--p-primary-color);
}
.ncerr__foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
}
.ncerr__copy {
  margin-inline-start: auto;
}
</style>
