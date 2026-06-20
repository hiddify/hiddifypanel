import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { HiddifyPreset } from '@/core/theme/preset'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import Ripple from 'primevue/ripple'
import '@/assets/sakai/tailwind.css'
import '@/assets/sakai/styles.scss'
import '@/shared/monaco/setup'

import App from './App.vue'
import { createAppRouter } from './router'
import { i18n } from './core/i18n'
import { initApiClient, getRouterBase } from './core/api/client'

async function bootstrap() {
  await initApiClient()

  const app = createApp(App)
  app.use(createPinia())
  app.use(createAppRouter(getRouterBase()))
  app.use(i18n)
  app.use(PrimeVue, {
    ripple: true,
    theme: {
      preset: HiddifyPreset,
      options: {
        darkModeSelector: '.app-dark',
      },
    },
  })
  app.directive('ripple', Ripple)
  app.use(ConfirmationService)
  app.use(ToastService)
  app.mount('#app')
}

bootstrap().catch((err) => {
  console.error(err)
  document.body.textContent = String(err)
})
