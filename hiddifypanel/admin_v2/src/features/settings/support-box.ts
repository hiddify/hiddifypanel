/**
 * The support box's title, "View More" button and Full text (shown by "Read More"): settings edited in the HTML editor of
 * ``branding_freetext`` (the Lite text, shown in the box).
 */
import type { BoxParts } from './components/html-editor/support-frame'
import type { SettingValue } from './api'

export const SUPPORT_TEXT_KEY = 'branding_freetext'

const PART_SETTINGS: Record<Exclude<keyof BoxParts, 'full'>, string> = {
  titleShow: 'branding_support_title_show',
  title: 'branding_support_title',
  moreShow: 'branding_support_more_show',
  more: 'branding_support_more',
}
const FULL_SETTING = 'branding_freetext_full'

/** The parts as ``values`` hold them; undefined when the server has not got these settings. */
export function readParts(values: Record<string, SettingValue>): BoxParts | undefined {
  if (!Object.values(PART_SETTINGS).every((key) => key in values)) return undefined
  return {
    titleShow: values[PART_SETTINGS.titleShow] !== false,
    title: String(values[PART_SETTINGS.title] ?? ''),
    moreShow: values[PART_SETTINGS.moreShow] !== false,
    more: String(values[PART_SETTINGS.more] ?? ''),
    ...(FULL_SETTING in values ? { full: String(values[FULL_SETTING] ?? '') } : {}),
  }
}

/** The settings to write for ``parts``. */
export function partSettings(parts: BoxParts): [string, SettingValue][] {
  const rows: [string, SettingValue][] = (Object.keys(PART_SETTINGS) as (keyof typeof PART_SETTINGS)[]).map((part) => [PART_SETTINGS[part], parts[part]])
  if (parts.full !== undefined) rows.push([FULL_SETTING, parts.full])
  return rows
}
