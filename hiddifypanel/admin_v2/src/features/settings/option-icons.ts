/**
 * Icons of the settings' select options, by setting key and option value: each one says what the option says
 * (High → three bars, No Wait → a bolt), in a colour of its own. Options not listed keep their label as it is.
 */
export interface OptionIcon {
  /** a PrimeIcons class, or a flag (country code), or a level (1–3 bars) */
  icon?: string
  flag?: string
  level?: 1 | 2 | 3
  color: string
}

const GRAY = 'var(--p-surface-500)'
const GREEN = 'var(--p-green-500)'
const AMBER = 'var(--p-amber-500)'
const ORANGE = 'var(--p-orange-500)'
const RED = 'var(--p-red-500)'
const SKY = 'var(--p-sky-500)'
const BLUE = 'var(--p-blue-500)'
const INDIGO = 'var(--p-indigo-500)'
const PURPLE = 'var(--p-purple-500)'
const TEAL = 'var(--p-teal-500)'

/** "Default": the protocol's own setting */
const DEFAULT: OptionIcon = { icon: 'pi pi-sliders-h', color: GRAY }

export const OPTION_ICONS: Record<string, Record<string, OptionIcon>> = {
  mieru_multiplexing: {
    MULTIPLEXING_DEFAULT: DEFAULT,
    MULTIPLEXING_LOW: { level: 1, color: GREEN },
    MULTIPLEXING_MIDDLE: { level: 2, color: AMBER },
    MULTIPLEXING_HIGH: { level: 3, color: ORANGE },
  },
  mieru_handshake: {
    HANDSHAKE_DEFAULT: DEFAULT,
    HANDSHAKE_NO_WAIT: { icon: 'pi pi-bolt', color: AMBER },
    HANDSHAKE_STANDARD: { icon: 'pi pi-shield', color: BLUE },
  },
  warp_mode: {
    disable: { icon: 'pi pi-ban', color: GRAY },
    all: { icon: 'pi pi-globe', color: BLUE },
    custom: { icon: 'pi pi-filter', color: GREEN },
  },
  package_mode: {
    release: { icon: 'pi pi-verified', color: GREEN },
    beta: { icon: 'pi pi-wrench', color: AMBER },
  },
  common_proxy_core: {
    xray: { icon: 'pi pi-microchip', color: SKY },
    hiddify_core: { icon: 'pi pi-box', color: INDIGO },
    both: { icon: 'pi pi-clone', color: PURPLE },
  },
  utls: {
    none: { icon: 'pi pi-ban', color: GRAY },
    chrome: { icon: 'pi pi-google', color: BLUE },
    edge: { icon: 'pi pi-microsoft', color: TEAL },
    ios: { icon: 'pi pi-apple', color: GRAY },
    android: { icon: 'pi pi-android', color: GREEN },
    safari: { icon: 'pi pi-compass', color: SKY },
    firefox: { icon: 'pi pi-globe', color: ORANGE },
    random: { icon: 'pi pi-sync', color: PURPLE },
    randomized: { icon: 'pi pi-sparkles', color: INDIGO },
  },
  country: {
    ir: { flag: 'ir', color: GREEN },
    zh: { flag: 'cn', color: RED },
    ru: { flag: 'ru', color: BLUE },
    other: { icon: 'pi pi-globe', color: SKY },
  },
}

/**
 * Setting descriptions that explain the options with emoji markers: those markers get the options' icons, so the
 * text and the list match (WARP: ✴️ All, ☑️ Only Domestic and Blocked Sites).
 */
export const DESCRIPTION_ICONS: Record<string, Record<string, OptionIcon>> = {
  warp_mode: { '✴': OPTION_ICONS.warp_mode.all, '☑': OPTION_ICONS.warp_mode.custom },
}

export function optionIcon(key: string, value: unknown): OptionIcon | null {
  return OPTION_ICONS[key]?.[String(value ?? '')] ?? null
}
