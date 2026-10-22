import { onBeforeUnmount, ref, shallowRef } from 'vue'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import { cleanIpApi, type CleanIpCommand, type CleanIpReport } from '../api'

const POLL_MS = 5000

/** A one-day command for another device, and the reports its runs send back (polled while the page is open). */
export function useScanCommand<R extends CleanIpReport>(onReports: (list: R[]) => void) {
  const toast = useToast()
  const making = ref(false)
  const command = ref<CleanIpCommand | null>(null)
  const reports = shallowRef<R[]>([]) // replaced whole on each new report
  let timer = 0

  async function make(payload: Parameters<typeof cleanIpApi.command>[0]) {
    making.value = true
    try {
      command.value = await cleanIpApi.command(payload)
      reports.value = []
      window.clearInterval(timer)
      timer = window.setInterval(poll, POLL_MS)
    } catch (e) {
      toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 5000 })
    } finally {
      making.value = false
    }
  }

  async function poll() {
    if (!command.value) return
    try {
      const list = await cleanIpApi.reports<R>(command.value.token)
      if (list.length !== reports.value.length) {
        reports.value = list
        onReports(list)
      }
    } catch {
      window.clearInterval(timer) // expired
    }
  }

  onBeforeUnmount(() => window.clearInterval(timer))
  return { making, command, reports, make }
}
