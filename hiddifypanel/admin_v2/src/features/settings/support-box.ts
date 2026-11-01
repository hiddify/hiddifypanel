/** The support box's title and "View More" button: four settings edited in the HTML editor of ``branding_freetext``. */
import type { BoxParts } from './components/html-editor/support-frame'
import type { SettingValue } from './api'

export const SUPPORT_TEXT_KEY = 'branding_freetext'

const PART_SETTINGS: Record<keyof BoxParts, string> = {
  titleShow: 'branding_support_title_show',
  title: 'branding_support_title',
  moreShow: 'branding_support_more_show',
  more: 'branding_support_more',
}

/** The parts as ``values`` hold them; undefined when the server has not got these settings. */
export function readParts(values: Record<string, SettingValue>): BoxParts | undefined {
  if (!Object.values(PART_SETTINGS).every((key) => key in values)) return undefined
  return {
    titleShow: values[PART_SETTINGS.titleShow] !== false,
    title: String(values[PART_SETTINGS.title] ?? ''),
    moreShow: values[PART_SETTINGS.moreShow] !== false,
    more: String(values[PART_SETTINGS.more] ?? ''),
  }
}

/** The settings to write for ``parts``. */
export function partSettings(parts: BoxParts): [string, SettingValue][] {
  return (Object.keys(PART_SETTINGS) as (keyof BoxParts)[]).map((part) => [PART_SETTINGS[part], parts[part]])
}
