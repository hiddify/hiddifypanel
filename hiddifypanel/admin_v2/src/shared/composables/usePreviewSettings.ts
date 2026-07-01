import { ref, watch } from 'vue'

const STORAGE_KEY = 'hiddify-editor-preview-settings'

export interface PreviewSettings {
  domainMode: 'pick' | 'custom'
  selectedDomainId: number | null
  customDomain: string
  uaMode: 'preset' | 'custom'
  selectedUaId: string | null
  customUa: string
  userMode: 'pick' | 'sample'
  selectedUserId: number | null
  ip: string
  ignoreSkip: boolean
}

const defaults: PreviewSettings = {
  domainMode: 'pick',
  selectedDomainId: null,
  customDomain: '',
  uaMode: 'preset',
  selectedUaId: null,
  customUa: '',
  userMode: 'sample',
  selectedUserId: null,
  ip: '203.0.113.1',
  ignoreSkip: true,
}

function loadFromStorage(): PreviewSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...defaults }
    return { ...defaults, ...JSON.parse(raw) }
  } catch {
    return { ...defaults }
  }
}

const settings = ref<PreviewSettings>(loadFromStorage())

watch(
  settings,
  (val) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(val))
  },
  { deep: true },
)

export function usePreviewSettings() {
  return { settings }
}

export interface UaPreset {
  id: string
  label?: string
  value: string
}

export function resolvePreviewParams(
  settings: PreviewSettings,
  uaPresets: UaPreset[],
  domains?: Array<{ id: number; domain: string }>,
): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    ip: settings.ip.trim() || '203.0.113.1',
    ignore_skip: settings.ignoreSkip,
  }

  if (settings.domainMode === 'pick' && settings.selectedDomainId) {
    payload.domain_id = settings.selectedDomainId
    const picked = domains?.find((d) => d.id === settings.selectedDomainId)
    if (picked) payload.domain = picked.domain
  } else if (settings.domainMode === 'custom' && settings.customDomain.trim()) {
    payload.domain = settings.customDomain.trim()
  }

  if (settings.userMode === 'pick' && settings.selectedUserId) {
    payload.user_id = settings.selectedUserId
  }

  let ua = ''
  if (settings.uaMode === 'custom') {
    ua = settings.customUa.trim()
  } else {
    const preset = uaPresets.find((item) => item.id === settings.selectedUaId)
    ua = preset?.value ?? uaPresets[0]?.value ?? ''
  }
  if (ua) payload.user_agent = ua

  return payload
}
