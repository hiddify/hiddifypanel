<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Panel from 'primevue/panel'
import PageHeader from '@/shared/components/PageHeader.vue'

const { t } = useI18n()
</script>

<template>
  <PageHeader :title="t('dashboard.title')" :subtitle="t('dashboard.subtitle')" />
  <Panel :header="t('dashboard.welcomePanel')">
    <p class="m-0 leading-relaxed">{{ t('dashboard.underConstruction') }}</p>
  </Panel>
</template>
