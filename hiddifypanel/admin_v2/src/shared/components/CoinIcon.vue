<script setup lang="ts">
import { computed } from 'vue'

interface CoinMark {
  color: string
  viewBox: string
  /** White mark drawn on the brand-coloured disc. */
  path: string
}

/** Brand marks (circle + glyph); ids match hutils/donation.py. */
const COINS: Record<string, CoinMark> = {
  bitcoin: {
    color: '#F7931A',
    viewBox: '0 0 32 32',
    path: 'M23.189 14.02c.314-2.096-1.283-3.223-3.465-3.975l.708-2.84-1.728-.43-.69 2.765c-.454-.114-.92-.22-1.385-.326l.695-2.783L15.596 6l-.708 2.839c-.376-.086-.746-.17-1.104-.26l.002-.009-2.384-.595-.46 1.846s1.283.294 1.256.312c.7.175.826.638.805 1.006l-.806 3.235c.048.012.11.03.18.057l-.183-.045-1.13 4.532c-.086.212-.303.531-.793.41.018.025-1.256-.313-1.256-.313l-.858 1.978 2.25.561c.418.105.828.215 1.231.318l-.715 2.872 1.727.43.708-2.84c.472.127.93.245 1.378.357l-.706 2.828 1.728.43.715-2.866c2.948.558 5.164.333 6.097-2.333.752-2.146-.037-3.385-1.588-4.192 1.13-.26 1.98-1.003 2.207-2.538zm-3.95 5.538c-.533 2.147-4.148.986-5.32.695l.95-3.805c1.172.293 4.929.872 4.37 3.11zm.535-5.569c-.487 1.953-3.495.96-4.47.717l.86-3.45c.975.243 4.118.696 3.61 2.733z',
  },
  'usdt-bep20': {
    color: '#26A17B',
    viewBox: '0 0 32 32',
    path: 'M17.922 17.383v-.002c-.11.008-.677.042-1.942.042-1.01 0-1.721-.03-1.971-.042v.003c-3.888-.171-6.79-.848-6.79-1.658 0-.809 2.902-1.486 6.79-1.66v2.644c.254.018.982.061 1.988.061 1.207 0 1.812-.05 1.925-.06v-2.643c3.88.173 6.775.85 6.775 1.658 0 .81-2.895 1.485-6.775 1.657m0-3.59v-2.366h5.414V7.819H8.595v3.608h5.414v2.365c-4.4.202-7.709 1.074-7.709 2.118 0 1.044 3.309 1.915 7.709 2.118v7.582h3.913v-7.584c4.393-.202 7.694-1.073 7.694-2.116 0-1.043-3.301-1.914-7.694-2.117',
  },
  tron: {
    color: '#EF0027',
    viewBox: '0 0 32 32',
    path: 'M21.932 9.913L7.5 7.257l7.595 19.112 10.583-12.894-3.746-3.562zm-.232 1.17l2.208 2.099-6.038 1.093 3.83-3.192zm-5.142 2.973l-6.364-5.278 10.402 1.914-4.038 3.364zm-.453.934l-1.038 8.58L9.472 9.487l6.633 5.502zm.96.455l6.687-1.21-7.67 9.343.983-8.133z',
  },
  litecoin: {
    color: '#345D9D',
    viewBox: '0 0 32 32',
    path: 'M10.427 19.214L9 19.768l.688-2.759 1.444-.58L13.213 8h5.129l-1.519 6.196 1.41-.571-.68 2.75-1.427.571-.848 3.483H23L22.127 24H9.252z',
  },
  ton: {
    color: '#0098EA',
    viewBox: '0 0 56 56',
    path: 'M37.56 15.63H18.44c-3.52 0-5.74 3.79-3.98 6.86l11.8 20.45c.77 1.34 2.7 1.34 3.47 0l11.8-20.45c1.77-3.06-.46-6.86-3.97-6.86zM26.25 36.81l-2.57-4.98-6.2-11.09c-.41-.71.1-1.62.95-1.62h7.82v17.69zm12.26-16.07l-6.2 11.1-2.57 4.97V19.12h7.82c.85 0 1.36.91.95 1.62z',
  },
}

const props = defineProps<{ coin: string; size?: string }>()
const mark = computed(() => COINS[props.coin])
const radius = computed(() => (mark.value?.viewBox.endsWith('56') ? 28 : 16))
</script>

<template>
  <svg v-if="mark" class="coin-icon" :style="{ width: size, height: size }" :viewBox="mark.viewBox" aria-hidden="true" focusable="false">
    <circle :cx="radius" :cy="radius" :r="radius" :fill="mark.color" />
    <path :d="mark.path" fill="#fff" fill-rule="evenodd" />
  </svg>
  <span v-else class="coin-icon coin-icon--generic" :style="{ width: size, height: size }" aria-hidden="true"><i class="pi pi-wallet" /></span>
</template>

<style scoped>
.coin-icon {
  display: block;
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
}
.coin-icon--generic {
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
</style>
