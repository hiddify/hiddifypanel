<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiErrorMessage } from '@/core/api/client'
import { quickSetupApi, type QuickSetupState } from '@/features/quick-setup/api'

const props = defineProps<{ state: QuickSetupState }>()
const emit = defineEmits<{ error: [message: string] }>()

const { t } = useI18n()

// Native names: the admin may not read the current UI language yet.
const LANGUAGE_LOOK: Record<string, { flag: string; name: string }> = {
  en: { flag: '🇺🇸', name: 'English' },
  fa: { flag: '🇮🇷', name: 'فارسی' },
  zh: { flag: '🇨🇳', name: '中文' },
  pt: { flag: '🇧🇷', name: 'Português' },
  ru: { flag: '🇷🇺', name: 'Русский' },
  my: { flag: '🇲🇲', name: 'မြန်မာ' },
}
const COUNTRY_FLAG: Record<string, string> = { ir: '🇮🇷', zh: '🇨🇳', ru: '🇷🇺', other: '🌍' }

const lang = ref(props.state.admin_lang)
const country = ref(props.state.country)

/** Saves; resolves to true to go on (the page reloads first when the language changed). */
async function submit(): Promise<boolean> {
  try {
    const res = await quickSetupApi.language(lang.value, country.value)
    if (res.reload) {
      // Load the UI in the new language, continuing at the next step.
      const url = new URL(window.location.href)
      url.searchParams.set('step', '2')
      window.location.replace(url.toString())
      return false
    }
    return true
  } catch (err) {
    emit('error', apiErrorMessage(err))
    return false
  }
}

defineExpose({ submit })
</script>

<template>
  <div class="flex flex-col gap-6">
    <section>
      <h3 class="qs-label"><i class="pi pi-language" /> {{ t('quickSetup.language.adminLang') }}</h3>
      <p class="qs-hint">{{ t('quickSetup.language.adminLangHint') }}</p>
      <div class="qs-options qs-options--lang" role="radiogroup" :aria-label="t('quickSetup.language.adminLang')">
        <button
          v-for="code in state.languages"
          :key="code"
          type="button"
          role="radio"
          :aria-checked="lang === code"
          class="qs-option"
          :class="{ 'qs-option--on': lang === code }"
          @click="lang = code"
        >
          <span class="qs-option__flag">{{ LANGUAGE_LOOK[code]?.flag ?? '🏳️' }}</span>
          <span class="qs-option__name">{{ LANGUAGE_LOOK[code]?.name ?? code }}</span>
          <i v-if="lang === code" class="pi pi-check-circle qs-option__check" />
        </button>
      </div>
    </section>

    <section>
      <h3 class="qs-label"><i class="pi pi-globe" /> {{ t('quickSetup.language.country') }}</h3>
      <p class="qs-hint">{{ t('quickSetup.language.countryHint') }}</p>
      <div class="qs-options" role="radiogroup" :aria-label="t('quickSetup.language.country')">
        <button
          v-for="code in state.countries"
          :key="code"
          type="button"
          role="radio"
          :aria-checked="country === code"
          class="qs-option"
          :class="{ 'qs-option--on': country === code }"
          @click="country = code"
        >
          <span class="qs-option__flag">{{ COUNTRY_FLAG[code] ?? '🌍' }}</span>
          <span class="qs-option__name">{{ t(`quickSetup.countries.${code}`) }}</span>
          <i v-if="country === code" class="pi pi-check-circle qs-option__check" />
        </button>
      </div>
    </section>
  </div>
</template>
