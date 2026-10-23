<script setup lang="ts">
/**
 * A panel over the node's card (under its name) that pings the node's server from this panel once a second, until it
 * is closed: the latest time, min / avg / max and loss, a bar per answer, and the last lines as a terminal prints them.
 * Each card has its own, so several nodes can be pinged at once.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { apiErrorMessage } from '@/core/api/client'
import { nodesApi, type PanelNode } from '@/features/nodes/api'

const props = defineProps<{ node: PanelNode }>()
const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()

interface Reply {
  seq: number
  ok: boolean
  ms: number | null
  error: string
}
const KEEP = 40
const replies = ref<Reply[]>([])
const ip = ref('')
const method = ref<'icmp' | 'tcp' | ''>('')
const sent = ref(0)
const received = ref(0)
let run = 0

async function loop(id: number, mine: number) {
  while (run === mine) {
    const started = Date.now()
    const seq = sent.value + 1
    sent.value = seq
    let reply: Reply
    try {
      const res = await nodesApi.icmp(id)
      ip.value = res.ip
      if (res.method) method.value = res.method
      reply = { seq, ok: res.ok, ms: res.ms, error: res.error === 'no_address' ? t('nodes.pingDialog.noAddress') : res.error }
    } catch (err) {
      reply = { seq, ok: false, ms: null, error: apiErrorMessage(err) }
    }
    if (run !== mine) return
    if (reply.ok) received.value++
    replies.value = [...replies.value.slice(-(KEEP - 1)), reply]
    // one a second (a slow answer is not followed at once by the next)
    await new Promise((r) => window.setTimeout(r, Math.max(0, 1000 - (Date.now() - started))))
  }
}

watch(
  () => props.node.id,
  (id) => {
    run++
    replies.value = []
    sent.value = received.value = 0
    ip.value = ''
    method.value = ''
    if (id != null) void loop(id, run)
  },
  { immediate: true },
)
onBeforeUnmount(() => run++)

const times = computed(() => replies.value.filter((r) => r.ok && r.ms != null).map((r) => r.ms as number))
const stats = computed(() => {
  const list = times.value
  if (!list.length) return null
  return { min: Math.min(...list), max: Math.max(...list), avg: list.reduce((a, b) => a + b, 0) / list.length }
})
const loss = computed(() => (sent.value ? Math.round(((sent.value - received.value) / sent.value) * 100) : 0))
const last = computed(() => replies.value[replies.value.length - 1])
/** Bar heights relative to the slowest answer kept */
const top = computed(() => Math.max(1, ...times.value))
const tone = (ms: number | null) => (ms == null ? 'lost' : ms < 80 ? 'good' : ms < 200 ? 'fair' : 'slow')
const fmt = (ms: number) => (ms < 10 ? ms.toFixed(1) : Math.round(ms).toString())
</script>

<template>
  <section class="nping" role="dialog" :aria-label="t('nodes.pingDialog.title', { name: node.name })" @keydown.esc="emit('close')">
    <div class="nping__target">
      <!-- A long address (IPv6, a long name) ends in "…": the close button stays where it is -->
      <span class="nping__ip" dir="ltr" :title="ip">{{ ip || '…' }}</span>
      <span v-if="method" class="nping__method">{{ method === 'icmp' ? 'ICMP' : t('nodes.pingDialog.tcp') }}</span>
      <span class="nping__live"><i class="nping__dot" />{{ t('nodes.pingDialog.running') }}</span>
      <Button icon="pi pi-times" text rounded size="small" severity="secondary" class="nping__close" :aria-label="t('common.close')" v-tooltip.top="t('common.close')" autofocus @click="emit('close')" />
    </div>

    <div class="nping__now" :class="`nping__now--${tone(last?.ms ?? null)}`">
      <template v-if="last?.ok && last.ms != null">{{ fmt(last.ms) }}<small> ms</small></template>
      <template v-else-if="last">{{ t('nodes.pingDialog.timeout') }}</template>
      <template v-else>…</template>
    </div>

    <div class="nping__bars" aria-hidden="true">
      <i v-for="r in replies" :key="r.seq" :class="`nping__bar--${tone(r.ms)}`" :style="{ height: r.ms != null ? `${Math.max(8, (r.ms / top) * 100)}%` : '100%' }" />
    </div>

    <dl class="nping__stats">
      <div><dt>{{ t('nodes.pingDialog.min') }}</dt><dd>{{ stats ? fmt(stats.min) : '—' }}</dd></div>
      <div><dt>{{ t('nodes.pingDialog.avg') }}</dt><dd>{{ stats ? fmt(stats.avg) : '—' }}</dd></div>
      <div><dt>{{ t('nodes.pingDialog.max') }}</dt><dd>{{ stats ? fmt(stats.max) : '—' }}</dd></div>
      <div><dt>{{ t('nodes.pingDialog.loss') }}</dt><dd :class="{ 'nping__bad': loss > 0 }">{{ loss }}%</dd></div>
    </dl>

    <ol class="nping__log" dir="ltr">
      <li v-for="r in replies.slice(-5).reverse()" :key="r.seq" :class="{ 'nping__bad': !r.ok }">
        <span>seq={{ r.seq }}</span>
        <span v-if="r.ok && r.ms != null">time={{ fmt(r.ms) }} ms</span>
        <span v-else>{{ r.error || t('nodes.pingDialog.timeout') }}</span>
      </li>
    </ol>
    <p class="nping__hint">{{ t('nodes.pingDialog.hint', { sent, received }) }}</p>
  </section>
</template>

<style scoped>
.nping {
  display: flex;
  flex-direction: column;
  padding: 0.75rem 0.85rem 0.8rem;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  box-shadow: 0 18px 40px -18px rgb(15 23 42 / 45%);
  overflow: hidden auto;
  animation: nping-in 0.18s ease-out;
}
.nping__close {
  margin-inline-start: -0.25rem;
}
@keyframes nping-in {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
}
.nping__target {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.nping__ip {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nping__method,
.nping__live,
.nping__close {
  flex: none;
}
.nping__method {
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  font-family: inherit;
  font-size: 0.7rem;
  font-weight: 700;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.nping__live {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  margin-inline-start: auto;
  font-family: var(--font-family, inherit);
  font-size: 0.75rem;
}
.nping__dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--p-green-500);
  animation: nping-pulse 1s ease-in-out infinite;
}
.nping__now {
  margin: 0.6rem 0 0.4rem;
  font-size: 2.2rem;
  font-weight: 700;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.nping__now small {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.nping__now--good {
  color: var(--p-green-500);
}
.nping__now--fair {
  color: var(--p-amber-500, #f59e0b);
}
.nping__now--slow,
.nping__now--lost {
  color: var(--p-red-500);
}
.nping__bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 3rem;
  padding: 0.25rem;
  border-radius: 8px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
}
.nping__bars i {
  flex: 1 1 0;
  min-width: 2px;
  border-radius: 2px;
  transition: height 0.3s ease;
}
.nping__bar--good {
  background: var(--p-green-500);
}
.nping__bar--fair {
  background: var(--p-amber-500, #f59e0b);
}
.nping__bar--slow {
  background: var(--p-red-500);
}
.nping__bar--lost {
  background: color-mix(in srgb, var(--p-red-500) 30%, transparent);
}
.nping__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.4rem;
  margin: 0.75rem 0 0.5rem;
}
.nping__stats div {
  padding: 0.35rem 0.45rem;
  border-radius: 8px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
}
.nping__stats dt {
  font-size: 0.68rem;
  color: var(--p-text-muted-color);
}
.nping__stats dd {
  margin: 0;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.nping__log {
  margin: 0;
  padding: 0.5rem 0.65rem;
  list-style: none;
  border-radius: 8px;
  background: #0f172a;
  color: #cbd5e1;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
  line-height: 1.6;
  min-height: 5.6rem;
}
.nping__log li {
  display: flex;
  gap: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nping__log li.nping__bad {
  color: #fca5a5;
}
.nping__bad {
  color: var(--p-red-500);
}
.nping__hint {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
@keyframes nping-pulse {
  50% {
    opacity: 0.3;
  }
}
@media (prefers-reduced-motion: reduce) {
  .nping__dot {
    animation: none;
  }
}
</style>
