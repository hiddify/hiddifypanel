import { ref } from 'vue'
import { templateVariablesApi, type TemplateVariable } from '@/core/api/generated'
import { flattenTemplateVariableGroups } from '@/shared/utils/template-variables'

let cached: TemplateVariable[] | null = null
let loadingPromise: Promise<TemplateVariable[]> | null = null

function mergeValues(target: TemplateVariable[], valueGroups: { variables?: TemplateVariable[] }[]) {
  const byAccess = new Map<string, unknown>()
  for (const g of valueGroups) {
    for (const v of g.variables ?? []) {
      if (v.value !== undefined) byAccess.set(v.access, v.value)
    }
  }
  for (const v of target) {
    if (byAccess.has(v.access)) v.value = byAccess.get(v.access)
  }
}

export function useTemplateVariableCatalog() {
  const variables = ref<TemplateVariable[]>(cached ?? [])
  const loading = ref(false)

  async function load(force = false) {
    if (!force && cached) {
      variables.value = cached
      return cached
    }
    if (!force && loadingPromise) {
      variables.value = await loadingPromise
      return variables.value
    }
    loading.value = true
    loadingPromise = templateVariablesApi
      .list()
      .then((res) => {
        cached = flattenTemplateVariableGroups(res.groups)
        variables.value = cached
        void templateVariablesApi.list({ values: true }).then((withValues) => {
          if (!cached) return
          mergeValues(cached, withValues.groups)
          variables.value = [...cached]
        })
        return cached
      })
      .finally(() => {
        loading.value = false
        loadingPromise = null
      })
    return loadingPromise
  }

  function invalidate() {
    cached = null
  }

  return { variables, loading, load, invalidate }
}
