<script setup lang="ts">
/** A select option's icon (option-icons.ts) on a soft tile of its colour: an icon, a flag, or 1–3 level bars (styles: _emoji-icons.scss). */
import FlagIcon from '@/shared/components/FlagIcon.vue'
import type { OptionIcon } from '@/features/settings/option-icons'

defineProps<{ icon: OptionIcon }>()
</script>

<template>
  <span class="ui-opt-icon" :style="{ '--c': icon.color }" aria-hidden="true">
    <FlagIcon v-if="icon.flag" :code="icon.flag" />
    <span v-else-if="icon.level" class="ui-opt-icon__level">
      <i v-for="n in 3" :key="n" :class="{ on: n <= icon.level! }" :style="{ height: `${n * 0.22 + 0.2}rem` }" />
    </span>
    <i v-else :class="icon.icon" />
  </span>
</template>
