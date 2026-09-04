<template>
  <PageHeader :title="t('utils.title')" :subtitle="t('utils.subtitle')" />
  <Panel>
    <Tabs v-model:value="tab">
      <TabList>
        <Tab value="sublink">{{ t('utils.sublinkTab') }}</Tab>
        <Tab value="base64">{{ t('utils.base64Tab') }}</Tab>
        <Tab value="url">{{ t('utils.urlTab') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="sublink">
          <p class="text-muted-color mt-0 mb-3">{{ t('utils.sublinkHint') }}</p>
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div class="flex flex-col gap-2">
              <div class="flex items-center justify-between gap-2">
                <label class="font-medium">{{ t('utils.links') }}</label>
                <Button icon="pi pi-copy" text rounded size="small" :aria-label="t('common.copy')" @click="copy(rawLinks)" />
              </div>
              <Textarea
                v-model="rawLinks"
                class="w-full font-mono text-sm util-textarea util-textarea--tall"
                :auto-resize="false"
                :rows="22"
                spellcheck="false"
                :placeholder="t('utils.linksPlaceholder')"
                @update:model-value="onRawInput"
              />
            </div>
            <div class="min-w-0">
              <label class="font-medium block mb-2">{{ t('utils.pretty') }}</label>
              <SublinkEditor v-model:links="links" @change="onEditorChange" />
            </div>
          </div>
          <Message v-if="unwrapped" severity="info" class="mt-3" :closable="false">{{ t('utils.unwrappedSubscription') }}</Message>
          <Message v-if="prettyError" severity="error" class="mt-3" :closable="false">{{ prettyError }}</Message>
        </TabPanel>
        <TabPanel value="base64">
          <CodecPanel
            v-model:left="base64Left"
            v-model:right="base64Right"
            :left-label="t('utils.input')"
            :right-label="t('utils.output')"
            :encode-label="t('utils.encode')"
            :decode-label="t('utils.decode')"
            :encode="encodeBase64"
            :decode="decodeBase64"
            show-url-safe
          />
        </TabPanel>
        <TabPanel value="url">
          <CodecPanel
            v-model:left="urlLeft"
            v-model:right="urlRight"
            :left-label="t('utils.input')"
            :right-label="t('utils.output')"
            :encode-label="t('utils.encode')"
            :decode-label="t('utils.decode')"
            :encode="encodeUrlValue"
            :decode="decodeUrlValue"
          />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </Panel>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Panel from 'primevue/panel'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Message from 'primevue/message'
import PageHeader from '@/shared/components/PageHeader.vue'
import CodecPanel from '@/features/utils/components/CodecPanel.vue'
import SublinkEditor from '@/features/utils/components/SublinkEditor.vue'
import { decodeUtf8Base64, decodeUrl, encodeUtf8Base64, encodeUrl } from '@/shared/utils/text-codecs'
import { parseSublinks, tryStringifySublinks, unwrapSubscriptionText, type PrettyLink } from '@/shared/utils/sublink-pretty'

const { t } = useI18n()
const toast = useToast()

const tab = ref('sublink')
const rawLinks = ref('')
const links = ref<PrettyLink[]>([])
const prettyError = ref<string | null>(null)
const unwrapped = ref(false)
const base64Left = ref('')
const base64Right = ref('')
const urlLeft = ref('')
const urlRight = ref('')
let syncing = false

function encodeBase64(value: string, urlSafe: boolean) {
  return encodeUtf8Base64(value, urlSafe)
}

function decodeBase64(value: string) {
  return decodeUtf8Base64(value)
}

function encodeUrlValue(value: string) {
  return encodeUrl(value)
}

function decodeUrlValue(value: string) {
  return decodeUrl(value)
}

function onRawInput(value: string) {
  if (syncing) return
  const { text, unwrapped: didUnwrap } = unwrapSubscriptionText(value)
  unwrapped.value = didUnwrap
  syncing = true
  if (didUnwrap && text !== value) rawLinks.value = text
  links.value = parseSublinks(text)
  prettyError.value = null
  void nextTick(() => {
    syncing = false
  })
}

function onEditorChange() {
  if (syncing) return
  const { text, error } = tryStringifySublinks(links.value)
  if (error) {
    prettyError.value = error
    return
  }
  syncing = true
  rawLinks.value = text
  prettyError.value = null
  unwrapped.value = false
  void nextTick(() => {
    syncing = false
  })
}

async function copy(value: string) {
  await navigator.clipboard.writeText(value)
  toast.add({ severity: 'success', summary: t('common.copied'), life: 1500 })
}
</script>

<style>
.util-textarea {
  min-height: 14rem;
  field-sizing: fixed;
}
.util-textarea--tall {
  min-height: 28rem;
}
.util-textarea--json {
  min-height: 16rem;
}
</style>
