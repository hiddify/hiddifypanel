import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { HiddifyPreset } from '@/core/theme/preset'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import Ripple from 'primevue/ripple'
import Tooltip from 'primevue/tooltip'
import '@/assets/sakai/tailwind.css'
import '@/assets/sakai/styles.scss'

import App from './App.vue'
// Early, to catch the browser's install event (it can come before any view).
import '@/shared/composables/usePwaInstall'
import { createAppRouter } from './router'
import { i18n, primeVueLocale, setLocale } from './core/i18n'
import { initApiClient, getRouterBase } from './core/api/client'
import { stripEmoji } from '@/shared/utils/emoji-icons'

async function bootstrap() {
  await initApiClient()
  // Bootstrap may have resolved the locale after the i18n module was evaluated.
  if (window.__LOCALE__) setLocale(window.__LOCALE__)

  const app = createApp(App)
  app.use(createPinia())
  app.use(createAppRouter(getRouterBase()))
  app.use(i18n)
  app.use(PrimeVue, {
    ripple: true,
    locale: primeVueLocale(),
    theme: {
      preset: HiddifyPreset,
      options: {
        darkModeSelector: '.app-dark',
      },
    },
  })
  app.directive('ripple', Ripple)
  app.directive('tooltip', Tooltip)
  app.use(ConfirmationService)
  app.use(ToastService)
  // Toast text from the server can carry a legacy emoji ("⚠️ …"); the toast has its own severity icon
  const toast = app.config.globalProperties.$toast
  const add = toast.add
  toast.add = (message) =>
    add({
      ...message,
      summary: typeof message.summary === 'string' ? stripEmoji(message.summary) : message.summary,
      detail: typeof message.detail === 'string' ? stripEmoji(message.detail) : message.detail,
    })
  app.mount('#app')
}

bootstrap().catch((err) => {
  console.error(err)
  document.body.textContent = String(err)
})
