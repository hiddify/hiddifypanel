import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { tagsApi, type Tag, type TagColor, type TagKind } from './api'

/** macOS-like label colors; black follows the theme's text color so it stays visible in dark mode. */
export const TAG_COLORS: Record<TagColor, string> = {
  red: '#ff453a',
  orange: '#ff9f0a',
  green: '#30d158',
  blue: '#0a84ff',
  black: 'var(--p-text-color)',
}
export const COLOR_ORDER: TagColor[] = ['red', 'orange', 'green', 'blue', 'black']

// One list for the whole dashboard: the users and admins pages share it.
const tags = ref<Tag[]>([])
const loaded = ref(false)
let loading: Promise<void> | null = null

async function load(force = false) {
  if (loaded.value && !force) return
  loading ??= tagsApi
    .list()
    .then((out) => {
      tags.value = out.tags
      loaded.value = true
    })
    .finally(() => (loading = null))
  await loading
}

export function useTags() {
  const { t, te } = useI18n()
  const byId = computed(() => new Map(tags.value.map((tag) => [tag.id, tag])))

  /** The default tags are translated; custom ones show as typed. */
  const label = (tag: Tag) => (tag.is_default && te(`tags.default.${tag.name}`) ? t(`tags.default.${tag.name}`) : tag.name)
  const color = (tag: Tag) => TAG_COLORS[tag.color] ?? TAG_COLORS.blue

  async function create(name: string, tagColor: TagColor): Promise<number> {
    const out = await tagsApi.create(name, tagColor)
    tags.value = out.tags
    return out.created_id
  }
  async function update(id: number, name: string, tagColor: TagColor) {
    tags.value = (await tagsApi.update(id, name, tagColor)).tags
  }
  async function remove(id: number) {
    tags.value = (await tagsApi.remove(id)).tags
  }
  /** Keep the counts shown on the chips right after a change, without another request. */
  function bump(added: number[], removed: number[]) {
    tags.value = tags.value.map((tag) => ({ ...tag, count: Math.max(0, tag.count + (added.includes(tag.id) ? 1 : 0) - (removed.includes(tag.id) ? 1 : 0)) }))
  }

  return { tags, loaded, byId, load, label, color, create, update, remove, bump }
}

/** Save the tags chosen in a form after the account was saved. Returns whether they were stored. */
export async function saveFormTags(kind: TagKind, uuid: string, wanted: number[], initial: number[]): Promise<boolean> {
  const same = wanted.length === initial.length && wanted.every((id) => initial.includes(id))
  if (same) return true
  try {
    await tagsApi.assign(kind, uuid, wanted)
    return true
  } catch {
    return false
  } finally {
    void load(true)
  }
}

/** The filter's "Tagged" option: anyone with at least one tag. */
export const ANY_TAG = 0

/** A row passes when it has any of the picked tags (nothing picked: everyone). */
export function matchesTags(ids: number[], picked: number[]): boolean {
  if (!picked.length) return true
  return picked.some((id) => (id === ANY_TAG ? ids.length > 0 : ids.includes(id)))
}
