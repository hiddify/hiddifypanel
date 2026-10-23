<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAdminMenu, type AdminMenuItem } from '@/core/layout/sakai/composables/useAdminMenu'
import { menuIconColor } from '@/core/layout/sakai/menu-icons'

const props = defineProps<{
  title: string
  subtitle?: string
  /** The icon before the title; by default the one of this page's menu item. */
  icon?: string
}>()

const route = useRoute()
const { menuGroups } = useAdminMenu()

/** The menu item whose route is this page (the deepest match, e.g. /templates over its group). */
const menuItem = computed(() => {
  const found: AdminMenuItem[] = []
  const walk = (items: AdminMenuItem[]) => {
    for (const item of items) {
      if (item.items) walk(item.items)
      else if (item.to && (item.to === route.path || (item.to !== '/' && route.path.startsWith(`${item.to}/`)))) found.push(item)
    }
  }
  for (const group of menuGroups.value) walk(group.items)
  return found.sort((a, b) => String(b.to).length - String(a.to).length)[0]
})
const icon = computed(() => props.icon ?? menuItem.value?.icon)
const color = computed(() => menuIconColor(icon.value))
</script>

<template>
  <div class="mb-5">
    <h2 class="page-title text-2xl font-semibold m-0">
      <span v-if="icon" class="page-title__icon" :style="color ? { '--mi': color } : undefined" aria-hidden="true"><i :class="icon" /></span>
      <span>{{ title }}</span>
    </h2>
    <p v-if="subtitle" class="text-muted-color mt-2 mb-0">{{ subtitle }}</p>
  </div>
</template>

<style scoped>
.page-title {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
/* The page's menu icon, larger, on a chip of its colour */
.page-title__icon {
  --mi: var(--p-primary-color);
  display: inline-grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  flex: none;
  border-radius: 12px;
  color: var(--mi);
  background: color-mix(in srgb, var(--mi) 15%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--mi) 22%, transparent);
}
.page-title__icon .pi {
  font-size: 1.2rem;
}
</style>
