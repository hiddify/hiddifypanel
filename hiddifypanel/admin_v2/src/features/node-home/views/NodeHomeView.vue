<template>
  <PageHeader :title="title" :subtitle="t('nodeHome.subtitle')" />
  <Card>
    <template #content>
      <div class="flex flex-col gap-4">
        <div class="flex items-start gap-3">
          <i class="pi pi-sitemap text-primary text-2xl mt-1" />
          <div class="min-w-0">
            <p class="m-0 text-lg">
              <template v-if="info?.parent_host">
                {{ t('nodeHome.connectedTo') }}
                <span class="font-semibold ltr">{{ info.parent_host }}</span>
              </template>
              <template v-else>{{ t('nodeHome.noParent') }}</template>
            </p>
            <p class="text-muted-color mt-2 mb-0">{{ t('nodeHome.managedOnParent') }}</p>
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            v-if="info?.parent_dashboard_url"
            as="a"
            :href="info.parent_dashboard_url"
            icon="pi pi-external-link"
            :label="t('nodeHome.openParent')"
          />
          <Button
            icon="pi pi-share-alt"
            :label="t('menu.customProxies')"
            severity="secondary"
            outlined
            @click="router.push({ name: 'custom-proxy-list' })"
          />
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Card from 'primevue/card'
import PageHeader from '@/shared/components/PageHeader.vue'
import { nodeInfo } from '@/core/panelShell'

const { t } = useI18n()
const router = useRouter()
const info = nodeInfo

const title = computed(() =>
  info.value?.node_name ? t('nodeHome.titleNamed', { name: info.value.node_name }) : t('nodeHome.title'),
)
</script>
