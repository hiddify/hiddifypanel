<script setup lang="ts">
import { avatarHue, initials } from '@/features/inbox/format'

defineProps<{ id: number; name: string; size?: 'md' | 'lg' }>()
</script>

<template>
  <span class="avatar" :class="`avatar--${size ?? 'md'}`" :style="{ '--hue': avatarHue(id) }" aria-hidden="true">{{ initials(name) }}</span>
</template>

<style scoped>
.avatar {
  display: grid;
  place-items: center;
  flex: none;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  background: linear-gradient(135deg, hsl(var(--hue) 75% 58%), hsl(calc(var(--hue) + 30) 70% 46%));
  color: #fff;
  font-weight: 700;
  font-size: 0.95rem;
}
.avatar--lg {
  width: 2.9rem;
  height: 2.9rem;
}
</style>
