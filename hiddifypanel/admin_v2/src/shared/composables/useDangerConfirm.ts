import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'

export interface DangerConfirmOptions {
  message: string
  header: string
  acceptLabel?: string
  rejectLabel?: string
  accept: () => void | Promise<void>
}

/**
 * Confirmation for destructive or disruptive actions (delete, reinstall, reset…):
 * red accept button, neutral reject button, and focus on reject so Enter is safe.
 */
export function useDangerConfirm() {
  const confirm = useConfirm()
  const { t } = useI18n()

  return (options: DangerConfirmOptions) =>
    confirm.require({
      message: options.message,
      header: options.header,
      icon: 'pi pi-exclamation-triangle',
      defaultFocus: 'reject',
      rejectProps: { label: options.rejectLabel ?? t('common.no'), severity: 'secondary', outlined: true },
      acceptProps: { label: options.acceptLabel ?? t('common.yes'), severity: 'danger' },
      accept: options.accept,
    })
}
