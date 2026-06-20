import type { TemplateVariable } from '@/core/api/generated'

export function flattenTemplateVariableGroups(
  groups: Array<{ id?: string; label?: string; variables: TemplateVariable[] }>,
): TemplateVariable[] {
  return groups.flatMap((g) =>
    (g.variables ?? []).map((v) => ({
      ...v,
      category: v.category ?? g.id,
      category_label: g.label,
    })),
  )
}
