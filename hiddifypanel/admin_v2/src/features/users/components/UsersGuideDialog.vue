<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

/** Shown once per admin on the Users page (users_layout.guide_seen): what pinning and reordering do. */
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ gotIt: [] }>()
const { t } = useI18n()

function gotIt() {
  visible.value = false
  emit('gotIt')
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :closable="false"
    :close-on-escape="false"
    :header="t('users.guide.title')"
    :style="{ width: 'min(34rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
    class="users-guide"
  >
    <p class="users-guide__intro">{{ t('users.guide.intro') }}</p>
    <ol class="users-guide__tips">
      <li class="users-guide__tip">
        <!-- A pinned row: the pin is on, the row sits on top -->
        <div class="users-guide__art" aria-hidden="true">
          <div class="users-guide__row users-guide__row--pinned"><i class="pi pi-thumbtack users-guide__pin" /><span class="users-guide__bar" /></div>
          <div class="users-guide__row"><i class="pi pi-thumbtack users-guide__pin users-guide__pin--off" /><span class="users-guide__bar users-guide__bar--short" /></div>
        </div>
        <div>
          <b>{{ t('users.guide.pinTitle') }}</b>
          <p>{{ t('users.guide.pinText') }}</p>
        </div>
      </li>
      <li class="users-guide__tip">
        <!-- A row lifted by its handle -->
        <div class="users-guide__art" aria-hidden="true">
          <div class="users-guide__row"><i class="pi pi-bars users-guide__handle" /><span class="users-guide__bar users-guide__bar--short" /></div>
          <div class="users-guide__row users-guide__row--lifted"><i class="pi pi-bars users-guide__handle" /><span class="users-guide__bar" /></div>
        </div>
        <div>
          <b>{{ t('users.guide.dragTitle') }}</b>
          <p>{{ t('users.guide.dragText') }}</p>
        </div>
      </li>
      <li class="users-guide__tip">
        <div class="users-guide__art users-guide__art--cols" aria-hidden="true">
          <span class="users-guide__col">{{ t('users.col.name') }}</span>
          <span class="users-guide__grip"><i class="pi pi-arrows-h" /></span>
          <span class="users-guide__col users-guide__col--wide">{{ t('users.col.usage') }}</span>
        </div>
        <div>
          <b>{{ t('users.guide.resizeTitle') }}</b>
          <p>{{ t('users.guide.resizeText') }}</p>
        </div>
      </li>
    </ol>
    <template #footer>
      <Button :label="t('users.guide.gotIt')" icon="pi pi-check" autofocus @click="gotIt" />
    </template>
  </Dialog>
</template>

<style scoped>
.users-guide__intro {
  margin: 0 0 1rem;
  color: var(--p-text-muted-color);
}
.users-guide__tips {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.users-guide__tip {
  display: grid;
  grid-template-columns: 8.5rem 1fr;
  gap: 1rem;
  align-items: center;
  padding: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 14px;
}
.users-guide__tip p {
  margin: 0.2rem 0 0;
  font-size: 0.88rem;
  line-height: 1.55;
  color: var(--p-text-muted-color);
}
.users-guide__art {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.users-guide__row {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.45rem;
  border-radius: 8px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
}
.users-guide__row--pinned {
  border-color: color-mix(in srgb, var(--p-primary-color) 45%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-primary-color) 8%, var(--p-content-background));
}
.users-guide__row--lifted {
  transform: translateX(6px) rotate(-1.5deg);
  box-shadow: 0 8px 18px -10px rgb(0 0 0 / 45%);
  animation: users-guide-lift 2.4s ease-in-out infinite;
}
.users-guide__pin {
  font-size: 0.8rem;
  color: var(--p-primary-color);
}
.users-guide__pin--off {
  color: var(--p-text-muted-color);
  opacity: 0.5;
}
.users-guide__handle {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.users-guide__bar {
  flex: 1;
  height: 0.45rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-text-color) 18%, transparent);
}
.users-guide__bar--short {
  flex: 0 0 55%;
}
.users-guide__art--cols {
  flex-direction: row;
  align-items: stretch;
  gap: 0;
  font-size: 0.7rem;
  font-weight: 600;
}
.users-guide__col {
  flex: 1;
  padding: 0.4rem 0.35rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px 0 0 8px;
  color: var(--p-text-muted-color);
  text-align: center;
}
.users-guide__col--wide {
  flex: 1.6;
  border-radius: 0 8px 8px 0;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 8%, transparent);
}
.users-guide__grip {
  display: grid;
  place-items: center;
  width: 1.1rem;
  color: var(--p-primary-color);
  font-size: 0.75rem;
}
@keyframes users-guide-lift {
  50% {
    transform: translateX(6px) translateY(-3px) rotate(-1.5deg);
  }
}
@media (max-width: 480px) {
  .users-guide__tip {
    grid-template-columns: 1fr;
  }
}
@media (prefers-reduced-motion: reduce) {
  .users-guide__row--lifted {
    animation: none;
  }
}
</style>
