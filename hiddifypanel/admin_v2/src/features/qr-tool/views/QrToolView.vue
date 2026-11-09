<template>
  <PageHeader :title="t('qrTool.title')" :subtitle="t('qrTool.subtitle')" />
  <Panel>
    <!-- lazy: leaving the Scan tab unmounts it, which turns the camera off. -->
    <Tabs v-model:value="tab" lazy>
      <TabList>
        <Tab value="make"><i class="pi pi-qrcode me-2" aria-hidden="true" />{{ t('qrTool.makeTab') }}</Tab>
        <Tab value="scan"><i class="pi pi-camera me-2" aria-hidden="true" />{{ t('qrTool.scanTab') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="make">
          <QrMaker v-model:text="makerText" />
        </TabPanel>
        <TabPanel value="scan">
          <QrScanner @make="makeFrom" @inspect="inspect" />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </Panel>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Panel from 'primevue/panel'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import PageHeader from '@/shared/components/PageHeader.vue'
import QrMaker from '@/features/qr-tool/components/QrMaker.vue'
import QrScanner from '@/features/qr-tool/components/QrScanner.vue'

type QrTab = 'make' | 'scan'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

/** The tab is in the address (?tab=scan), so a bookmark or a phone's home-screen link opens the scanner. */
const tab = computed<string>({
  get: (): QrTab => (route.query.tab === 'scan' ? 'scan' : 'make'),
  set: (value) => void router.replace({ query: { ...route.query, tab: value === 'scan' ? 'scan' : undefined } }),
})
const makerText = ref('')

function makeFrom(text: string) {
  makerText.value = text
  tab.value = 'make'
}

/** Opens the scanned links in Text Decoders (Sublink tab), which reads them from the navigation state. */
function inspect(text: string) {
  void router.push({ name: 'utils', state: { sublinks: text } })
}
</script>
