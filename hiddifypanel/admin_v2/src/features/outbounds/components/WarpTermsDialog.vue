<template>
  <Dialog
    v-model:visible="open"
    modal
    :header="t('outbounds.terms.title')"
    :style="{ width: 'min(36rem, calc(100vw - 2rem))' }"
    :dismissable-mask="false"
    :closable="!busy"
    :close-on-escape="!busy"
    @hide="onHide"
  >
    <p class="warp-terms__lead">{{ t('outbounds.terms.lead') }}</p>
    <p class="warp-terms__body">{{ t('outbounds.terms.body') }}</p>
    <p class="warp-terms__links">
      <a :href="TERMS_URL" target="_blank" rel="noopener noreferrer">{{ t('outbounds.terms.termsLink') }}</a>
      <a :href="PRIVACY_URL" target="_blank" rel="noopener noreferrer">{{ t('outbounds.terms.privacyLink') }}</a>
    </p>
    <div class="warp-terms__check">
      <Checkbox v-model="checked" binary input-id="warp-tos-accept" :disabled="busy" />
      <label for="warp-tos-accept">{{ t('outbounds.terms.check') }}</label>
    </div>
    <template #footer>
      <div class="warp-terms__actions">
        <Button type="button" :label="t('outbounds.terms.cancel')" severity="secondary" text :disabled="busy" @click="cancel" />
        <Button type="button" :label="t('outbounds.terms.accept')" icon="pi pi-check" :disabled="!checked || busy" :loading="busy" @click="accept" />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'

/** Cloudflare's own terms and privacy pages. The text stays there; this dialog only links to it. */
const TERMS_URL = 'https://www.cloudflare.com/application/terms/'
const PRIVACY_URL = 'https://www.cloudflare.com/application/privacypolicy/'

const props = defineProps<{ visible: boolean; busy?: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean]; accept: []; cancel: [] }>()

const { t } = useI18n()
const checked = ref(false)
/** Set when Accept closed the dialog, so the following hide is not treated as Cancel. */
const confirmed = ref(false)

const open = computed({
  get: () => props.visible,
  set: (value: boolean) => emit('update:visible', value),
})

watch(
  () => props.visible,
  (shown) => {
    if (shown) checked.value = false
  },
)

function accept() {
  if (!checked.value || props.busy) return
  confirmed.value = true
  emit('accept')
  emit('update:visible', false)
}

function cancel() {
  emit('update:visible', false)
}

function onHide() {
  checked.value = false
  if (confirmed.value) {
    confirmed.value = false
    return
  }
  emit('cancel')
}
</script>

<style scoped>
.warp-terms__lead {
  margin: 0 0 0.6rem;
  font-weight: 600;
  line-height: 1.45;
}

.warp-terms__body {
  margin: 0;
  color: var(--p-text-muted-color);
  line-height: 1.5;
}

.warp-terms__links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  margin-block-start: 0.85rem;
}

.warp-terms__links a {
  color: var(--p-primary-color);
  font-weight: 600;
}

.warp-terms__check {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  margin-block-start: 1rem;
  line-height: 1.45;
}

.warp-terms__check label {
  cursor: pointer;
}

.warp-terms__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
  width: 100%;
}
</style>
