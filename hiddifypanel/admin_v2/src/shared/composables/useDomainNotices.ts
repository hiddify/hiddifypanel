import { ref } from 'vue'
import { getHttp } from '@/core/api/client'

/**
 * The Domains page's problems for the topbar's notifications, so an admin hears of them on any page: domains whose
 * certificate does not work (from the server), and the warnings of the last saves (kept in this browser).
 */
export interface DomainProblem {
  id: number
  domain: string
  /** failed | renew_failed | rate_limited | expired | self_signed | missing | invalid */
  kind: string
  status: string
  error: string
}
export interface DomainSaveWarning {
  at: number
  text: string
}

export const domainProblems = ref<DomainProblem[]>([])

export async function loadDomainProblems(): Promise<void> {
  try {
    domainProblems.value = (await getHttp().get<{ problems: DomainProblem[] }>('domains-page/problems/')).data.problems ?? []
  } catch {
    /* not this admin's page, or offline: the list stays as it was */
  }
}

const WARNINGS_KEY = 'hiddify.domains.warnings'
/** A save's warning stays in the notifications this long (or until it is dismissed there) */
const WARNING_TTL_MS = 3 * 24 * 3600_000

function readWarnings(): DomainSaveWarning[] {
  try {
    const list = JSON.parse(localStorage.getItem(WARNINGS_KEY) || '[]')
    return Array.isArray(list) ? list.filter((w) => w && typeof w.text === 'string' && Date.now() - Number(w.at) < WARNING_TTL_MS) : []
  } catch {
    return []
  }
}

export const domainSaveWarnings = ref<DomainSaveWarning[]>(readWarnings())

/** The warnings a save answered with (also shown as toasts on the page), as plain text. */
export function rememberDomainWarnings(texts: string[]) {
  if (!texts.length) return
  const fresh = texts.map((text) => ({ at: Date.now(), text }))
  const known = new Set(fresh.map((w) => w.text))
  domainSaveWarnings.value = [...fresh, ...readWarnings().filter((w) => !known.has(w.text))].slice(0, 10)
  try {
    localStorage.setItem(WARNINGS_KEY, JSON.stringify(domainSaveWarnings.value))
  } catch {
    /* private mode: for this visit only */
  }
}
