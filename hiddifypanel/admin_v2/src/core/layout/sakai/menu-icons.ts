/**
 * The colour of each menu icon, by what it is (the menu sends PrimeIcons classes: v2_menu.py, useAdminMenu.ts).
 * Vivid on both themes; the page header shows the same icon and colour as the page's menu item.
 */
const ICON_COLOR: Record<string, string> = {
  'pi-home': '#3b82f6', // dashboard, parent panel
  'pi-users': '#8b5cf6', // users
  'pi-sitemap': '#6366f1', // admins
  'pi-user-edit': '#6366f1',
  'pi-send': '#0ea5e9', // send message
  'pi-server': '#14b8a6', // nodes, node home, proxy editor
  'pi-wrench': '#f97316', // tools
  'pi-bolt': '#f59e0b', // config tester, actions
  'pi-wifi': '#06b6d4', // clean IP scanner
  'pi-code': '#10b981', // decoders, API
  'pi-desktop': '#a855f7', // SSH
  'pi-link': '#2563eb', // domains
  'pi-sliders-h': '#ec4899', // protocols
  'pi-directions': '#22c55e', // outbounds
  'pi-cog': '#0891b2', // settings
  'pi-share-alt': '#d946ef', // custom proxies
  'pi-file-edit': '#eab308', // templates
  'pi-list': '#84cc16', // template variables
  'pi-save': '#16a34a', // backup
  'pi-question-circle': '#0ea5e9', // help
  'pi-exclamation-circle': '#eab308', // bug / feature
  'pi-heart': '#ef4444', // donation
  'pi-telegram': '#229ed9', // Telegram
  'pi-chart-bar': '#8b5cf6',
}

/** `pi pi-fw pi-users` → its colour; undefined for an icon without one (it keeps the text colour). */
export function menuIconColor(icon: unknown): string | undefined {
  if (typeof icon !== 'string') return undefined
  const name = icon.split(/\s+/).find((c) => c.startsWith('pi-') && c !== 'pi-fw')
  return name ? ICON_COLOR[name] : undefined
}
