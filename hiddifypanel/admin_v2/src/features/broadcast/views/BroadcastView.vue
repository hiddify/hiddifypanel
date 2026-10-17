<template>
  <div class="bc-page">
    <PageHeader :title="t('broadcast.title')" :subtitle="t('broadcast.subtitle')" />
    <BroadcastComposer :ids="ids" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/shared/components/PageHeader.vue'
import BroadcastComposer from '@/features/broadcast/components/BroadcastComposer.vue'

const { t } = useI18n()
const route = useRoute()
/** ?ids=1,2,3: a link to the page with chosen users as the audience */
const ids = computed(() =>
  String(route.query.ids ?? '')
    .split(',')
    .map((x) => Number(x))
    .filter((x) => Number.isInteger(x) && x > 0),
)
</script>

<style scoped>
.bc-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-bottom: 5.5rem; /* room for the send bar */
}
</style>
