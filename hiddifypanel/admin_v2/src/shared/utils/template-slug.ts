import type { ProxyBaseConfig, ProxyTemplate } from '@/core/api/generated'

type BuiltinContentFields = Pick<
  ProxyTemplate | ProxyBaseConfig,
  'content' | 'builtin_content' | 'builtin_override' | 'is_builtin'
>

/** Text used for display, include parsing, and side panel when builtin override is off. */
export function effectiveTemplateContent(
  item: BuiltinContentFields | null | undefined,
  fallback = '',
): string {
  if (!item) return fallback
  if (item.is_builtin && !item.builtin_override) {
    return item.builtin_content || item.content || fallback
  }
  return item.content ?? fallback
}

type BuiltinSaveFields = BuiltinContentFields & {
  name?: string
  description?: string
}

/** Build PATCH body for a built-in template/base-config content save. */
export function buildBuiltinContentPatch(
  item: BuiltinSaveFields,
  currentContent: string,
): {
  name?: string
  description?: string
  builtin_override: boolean
  content?: string
} {
  const builtinContent = item.builtin_content ?? ''
  const editedContent = currentContent ?? item.content ?? ''
  const contentChanged = editedContent.trim() !== builtinContent.trim()
  const override = Boolean(item.builtin_override) || contentChanged
  const patch: {
    name?: string
    description?: string
    builtin_override: boolean
    content?: string
  } = {
    name: item.name,
    description: item.description,
    builtin_override: override,
  }
  if (override) {
    patch.content = editedContent
  }
  return patch
}

/** Prefix portion of slug: core/server/ (e.g. xray/inbound/). */
export function templateSlugPrefix(core: string, category: string): string {
  const server = category.replace(/^server_/, '').replace(/^client_/, '').replace(/^base_/, '')
  return `${core}/${server}/`
}

/** Editable tail after core/category prefix. */
export function slugSuffixFromFullSlug(slug: string, prefix?: string): string {
  const p = prefix ?? ''
  if (p && slug.startsWith(p)) return slug.slice(p.length)
  const parts = slug.split('/')
  if (parts.length >= 3) return parts.slice(2).join('/')
  return slug
}

export function slugifyTemplateTail(label: string): string {
  return (
    label
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'template'
  )
}

/** Display label: description when set, otherwise full slug. */
export function templateDisplayName(
  t: Pick<ProxyTemplate, 'slug' | 'core' | 'category' | 'name' | 'description'>,
): string {
  if (t.description?.trim()) return t.description.trim()
  if (t.slug.includes('/')) return t.slug
  const server = t.category.replace(/^server_/, '').replace(/^client_/, '').replace(/^base_/, '')
  const tail = (t.name || 'template').toLowerCase().replace(/\s+/g, '-')
  return `${t.core}/${server}/${tail}`
}

export function asTemplateSlugList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((v): v is string => typeof v === 'string' && Boolean(v.trim()))
  }
  if (typeof value === 'string' && value.trim()) {
    return value.split(/[,\s]+/).map((part) => part.trim()).filter(Boolean)
  }
  return []
}

export function parseIncludedTemplateSlugs(templateText: string, explicitSlugs: string[] | unknown = []): string[] {
  const found = new Set(asTemplateSlugList(explicitSlugs))
  const includeRe = /\{%-?\s*include\s+['"]([^'"]+)['"]/g
  let match: RegExpExecArray | null
  while ((match = includeRe.exec(templateText)) !== null) {
    found.add(match[1]!)
  }
  return [...found]
}

export function parseIncludePathSlugs(templateText: string): string[] {
  const found = new Set<string>()
  const includePathRe = /include_path\s*\(\s*(?:\w+\s*,\s*)?['"]([^'"]+)['"]/g
  let match: RegExpExecArray | null
  while ((match = includePathRe.exec(templateText)) !== null) {
    found.add(match[1]!)
  }
  return [...found]
}

/** Direct {% include %} and include_path(ctx, 'slug') references in template text. */
export function parseReferencedTemplateSlugs(templateText: string, explicitSlugs: string[] | unknown = []): string[] {
  const found = new Set<string>()
  for (const slug of parseIncludedTemplateSlugs(templateText, explicitSlugs)) {
    found.add(slug)
  }
  for (const slug of parseIncludePathSlugs(templateText)) {
    found.add(slug)
  }
  return [...found]
}

export function expandReferencedTemplateSlugs(
  seedSlugs: string[],
  contentBySlug: Map<string, string | null | undefined>,
): string[] {
  const expanded = new Set(seedSlugs.filter(Boolean))
  const queue = [...expanded]
  while (queue.length) {
    const slug = queue.shift()!
    const content = contentBySlug.get(slug) ?? ''
    for (const ref of parseReferencedTemplateSlugs(content, [])) {
      if (!expanded.has(ref)) {
        expanded.add(ref)
        queue.push(ref)
      }
    }
  }
  return [...expanded]
}

export function sortTemplatesByIncluded<T extends { slug: string }>(
  templates: T[],
  includedSlugs: string[],
): T[] {
  const rank = new Map(includedSlugs.map((s, i) => [s, i]))
  return [...templates].sort((a, b) => {
    const ar = rank.has(a.slug) ? rank.get(a.slug)! : Number.MAX_SAFE_INTEGER
    const br = rank.has(b.slug) ? rank.get(b.slug)! : Number.MAX_SAFE_INTEGER
    if (ar !== br) return ar - br
    return a.slug.localeCompare(b.slug)
  })
}

export function buildIncludeSnippet(slug: string): string {
  return `{%- include '${slug}' -%}`
}

/** Slug path: core/server/custom_path (e.g. xray/inbound/my-template). */
export function buildTemplateSlug(core: string, category: string, label: string): string {
  return `${templateSlugPrefix(core, category)}${slugifyTemplateTail(label)}`
}

export function buildTemplateSlugFromSuffix(core: string, category: string, suffix: string): string {
  return `${templateSlugPrefix(core, category)}${slugifyTemplateTail(suffix)}`
}
