<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DomainMode, QuickSetupState } from '@/features/quick-setup/api'

const props = defineProps<{ state: QuickSetupState }>()

const { t } = useI18n()

const LANG_NAMES: Record<string, string> = { en: 'English', fa: 'فارسی', zh: '中文', pt: 'Português', ru: 'Русский', my: 'မြန်မာ' }

const MODES: { mode: DomainMode; icon: string }[] = [
  { mode: 'direct', icon: 'pi pi-bolt' },
  { mode: 'cdn', icon: 'pi pi-cloud' },
  { mode: 'reality', icon: 'pi pi-eye-slash' },
  { mode: 'relay', icon: 'pi pi-share-alt' },
]

const rows = computed<{ icon: string; label: string; value: string; ltr?: boolean }[]>(() => [
  { icon: 'pi pi-language', label: t('quickSetup.language.adminLang'), value: LANG_NAMES[props.state.admin_lang] ?? props.state.admin_lang },
  { icon: 'pi pi-globe', label: t('quickSetup.language.country'), value: t(`quickSetup.countries.${props.state.country}`) },
  ...MODES.flatMap(({ mode, icon }) => {
    const names = props.state.entries.filter((e) => e.mode === mode).map((e) => e.domain)
    return names.length ? [{ icon, label: t(`quickSetup.domains.modes.${mode}`), value: names.join(', '), ltr: true }] : []
  }),
  ...(props.state.sublink_domains.length ? [{ icon: 'pi pi-shield', label: t('quickSetup.domains.sublink'), value: props.state.sublink_domains.join(', '), ltr: true }] : []),
  { icon: 'pi pi-ban', label: t('quickSetup.domains.block'), value: props.state.block_iran_sites ? t('quickSetup.finish.on') : t('quickSetup.finish.off') },
  ...(props.state.decoy_domain ? [{ icon: 'pi pi-desktop', label: t('quickSetup.domains.decoy'), value: props.state.decoy_domain, ltr: true }] : []),
])
</script>

<template>
  <div class="flex flex-col gap-5">
    <div class="qs-finish-hero">
      <span class="qs-finish-hero__icon"><i class="pi pi-flag-fill" /></span>
      <div>
        <div class="text-lg font-semibold">{{ t('quickSetup.finish.ready') }}</div>
        <div class="text-muted-color">{{ t('quickSetup.finish.readyHint') }}</div>
      </div>
    </div>

    <dl class="qs-summary">
      <div v-for="row in rows" :key="row.label" class="qs-summary__row">
        <dt><i :class="row.icon" /> {{ row.label }}</dt>
        <dd :dir="row.ltr ? 'ltr' : undefined">{{ row.value }}</dd>
      </div>
    </dl>

    <div class="qs-callout">
      <i class="pi pi-info-circle" />
      <span>{{ t('quickSetup.finish.whatHappens') }}</span>
    </div>

    <a class="qs-docs" href="https://hiddify.com/manager/" target="_blank" rel="noopener">
      <i class="pi pi-book" />
      <span class="flex-1">
        <span class="font-semibold block">{{ t('quickSetup.finish.docs') }}</span>
        <span class="text-muted-color text-sm">hiddify.com/manager</span>
      </span>
      <i class="pi pi-external-link" />
    </a>
  </div>
</template>
