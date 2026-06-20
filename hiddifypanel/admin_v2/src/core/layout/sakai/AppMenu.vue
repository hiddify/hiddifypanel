<script setup lang="ts">
import AppMenuItem from './AppMenuItem.vue'
import { useAdminMenu } from './composables/useAdminMenu'

const { menuGroups } = useAdminMenu()
</script>

<template>
  <ul class="layout-menu">
    <AppMenuItem v-for="item in menuGroups" :key="item.label" :item="item" :root="true" />
  </ul>
</template>
