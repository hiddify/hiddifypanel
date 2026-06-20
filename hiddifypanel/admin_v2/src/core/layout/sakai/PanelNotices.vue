<script setup lang="ts">
import Message from 'primevue/message'
import { usePanelNotifications } from './composables/usePanelNotifications'

const { visibleNotices, dismiss } = usePanelNotifications()
</script>

<template>
  <div v-if="visibleNotices.length" class="panel-notices flex flex-col gap-2 mb-4">
    <Message
      v-for="(notice, index) in visibleNotices"
      :key="`${notice.severity}-${index}`"
      :severity="notice.severity"
      :closable="true"
      class="w-full"
      @close="dismiss(notice, index)"
    >
      <span class="notice-body" v-html="notice.summary" />
      <p v-if="notice.detail" class="m-0 mt-2 text-sm notice-body" v-html="notice.detail" />
    </Message>
  </div>
</template>
