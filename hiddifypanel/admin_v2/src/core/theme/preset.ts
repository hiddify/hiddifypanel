import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

/**
 * Sakai-style blue primary on Aura, with iOS-style soft corners on every form field (text, number, password, search,
 * date, Select, MultiSelect, AutoComplete, Textarea, input groups) and on their dropdown panels and options: one radius
 * for all of them, rounded but not a pill.
 */
export const HiddifyPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '{blue.50}',
      100: '{blue.100}',
      200: '{blue.200}',
      300: '{blue.300}',
      400: '{blue.400}',
      500: '{blue.500}',
      600: '{blue.600}',
      700: '{blue.700}',
      800: '{blue.800}',
      900: '{blue.900}',
      950: '{blue.950}',
    },
    formField: {
      borderRadius: '12px',
    },
    overlay: {
      select: {
        borderRadius: '14px',
      },
    },
    list: {
      option: {
        borderRadius: '8px',
      },
    },
  },
})
