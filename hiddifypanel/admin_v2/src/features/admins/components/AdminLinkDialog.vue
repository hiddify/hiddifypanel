<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import LinkShareDialog from '@/shared/components/LinkShareDialog.vue'
import type { AdminRow, LinkDomain } from '@/features/admins/api'

defineProps<{ admin: AdminRow | null; domains: LinkDomain[] }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ resetPassword: [admin: AdminRow] }>()

const { t } = useI18n()
</script>

<template>
  <LinkShareDialog
    v-if="admin"
    v-model:visible="visible"
    :title="t('admins.linkDialog.title', { name: admin.name })"
    :name="admin.name"
    :domains="domains"
    :path="`${admin.uuid}/`"
    :fallback-link="admin.admin_link"
  >
    <!-- The password is never shown: only a reset gives a new one. -->
    <div class="admin-link-pw">
      <i class="pi" :class="admin.has_password ? 'pi-key' : 'pi-unlock'" />
      <div class="flex-1 min-w-0">
        <div class="font-medium">{{ admin.has_password ? t('admins.linkDialog.pwSet') : t('admins.linkDialog.pwNone') }}</div>
        <small class="text-muted-color">{{ t('admins.linkDialog.pwHint') }}</small>
      </div>
      <Button v-if="admin.can_edit" icon="pi pi-refresh" :label="t('admins.resetPassword')" size="small" severity="warn" text @click="emit('resetPassword', admin)" />
    </div>
  </LinkShareDialog>
</template>

<style scoped>
.admin-link-pw {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.7rem;
  padding: 0.7rem 0.85rem;
  border-radius: 12px;
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 8%, transparent);
  font-size: 0.88rem;
}
.admin-link-pw > i {
  color: var(--p-amber-600, #d97706);
}
</style>
