/**
 * Vector logos of hosting and network companies, for the IP details sheet: sharp at any size, unlike a website's
 * favicon. The drawings come from Simple Icons (https://simpleicons.org, CC0-1.0); the logos are trademarks of their
 * owners. Only the icons named here are bundled. Companies Simple Icons has no logo for (e.g. AWS, Microsoft, Oracle)
 * keep their website's own icon.
 */
import {
  siAkamai,
  siAlibabacloud,
  siApple,
  siCloudflare,
  siContabo,
  siDigitalocean,
  siFastly,
  siFlydotio,
  siGcore,
  siGithub,
  siGodaddy,
  siGooglecloud,
  siHetzner,
  siHostinger,
  siHuawei,
  siIonos,
  siMeta,
  siNamecheap,
  siNetcup,
  siNetlify,
  siOvh,
  siScaleway,
  siTelegram,
  siUpcloud,
  siVercel,
  siVultr,
  siYandexcloud,
  type SimpleIcon,
} from 'simple-icons'

export interface CompanyLogo {
  /** the drawing (24×24) and its brand colour */
  icon: SimpleIcon
  /** the company's websites: its abuse contacts' domains name it */
  domains: string[]
  /** words of the company's registered name (lower case), for when no website is known */
  names: string[]
}

export const COMPANY_LOGOS: CompanyLogo[] = [
  { icon: siHetzner, domains: ['hetzner.com', 'hetzner.de', 'hetzner.cloud', 'your-server.de'], names: ['hetzner'] },
  { icon: siOvh, domains: ['ovh.net', 'ovh.com', 'ovhcloud.com', 'ovh.ca', 'kimsufi.com', 'soyoustart.com'], names: ['ovh'] },
  { icon: siDigitalocean, domains: ['digitalocean.com'], names: ['digitalocean'] },
  { icon: siVultr, domains: ['vultr.com', 'choopa.com', 'choopa.net', 'constant.com'], names: ['vultr', 'choopa', 'the constant company'] },
  { icon: siAkamai, domains: ['akamai.com', 'akamaitechnologies.com', 'linode.com'], names: ['akamai', 'linode'] },
  { icon: siCloudflare, domains: ['cloudflare.com'], names: ['cloudflare'] },
  { icon: siGooglecloud, domains: ['google.com', 'googlecloud.com'], names: ['google'] },
  { icon: siAlibabacloud, domains: ['alibabacloud.com', 'aliyun.com', 'alibaba-inc.com', 'alibaba.com'], names: ['alibaba', 'aliyun'] },
  { icon: siIonos, domains: ['ionos.com', 'ionos.de', '1and1.com', '1und1.de', 'oneandone.net'], names: ['ionos', '1&1'] },
  { icon: siScaleway, domains: ['scaleway.com', 'online.net', 'iliad-datacenter.com'], names: ['scaleway'] },
  { icon: siUpcloud, domains: ['upcloud.com'], names: ['upcloud'] },
  { icon: siHostinger, domains: ['hostinger.com'], names: ['hostinger'] },
  { icon: siGodaddy, domains: ['godaddy.com', 'secureserver.net'], names: ['godaddy'] },
  { icon: siNamecheap, domains: ['namecheap.com'], names: ['namecheap'] },
  { icon: siContabo, domains: ['contabo.com', 'contabo.de'], names: ['contabo'] },
  { icon: siFastly, domains: ['fastly.com'], names: ['fastly'] },
  { icon: siNetcup, domains: ['netcup.de', 'netcup.com', 'netcup.eu'], names: ['netcup'] },
  { icon: siYandexcloud, domains: ['yandex.ru', 'yandex.net', 'yandex.com', 'yandex-team.ru', 'yandex.cloud'], names: ['yandex'] },
  { icon: siGcore, domains: ['gcore.com', 'gcorelabs.com', 'gcore.lu'], names: ['g-core', 'gcore'] },
  { icon: siHuawei, domains: ['huawei.com', 'huaweicloud.com'], names: ['huawei'] },
  { icon: siTelegram, domains: ['telegram.org'], names: ['telegram'] },
  { icon: siApple, domains: ['apple.com'], names: ['apple inc'] },
  { icon: siMeta, domains: ['fb.com', 'facebook.com', 'meta.com'], names: ['facebook', 'meta platforms'] },
  { icon: siGithub, domains: ['github.com'], names: ['github'] },
  { icon: siFlydotio, domains: ['fly.io'], names: ['fly.io'] },
  { icon: siVercel, domains: ['vercel.com'], names: ['vercel'] },
  { icon: siNetlify, domains: ['netlify.com'], names: ['netlify'] },
]

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** The company's vector logo, by its website (or a subdomain of it), else by a whole word of its name. */
export function companyLogo(domain?: string, name?: string): CompanyLogo | undefined {
  const host = (domain || '').trim().toLowerCase().replace(/^www\./, '')
  if (host) {
    const hit = COMPANY_LOGOS.find((c) => c.domains.some((d) => host === d || host.endsWith('.' + d)))
    if (hit) return hit
  }
  const words = (name || '').toLowerCase()
  if (!words) return undefined
  return COMPANY_LOGOS.find((c) => c.names.some((n) => new RegExp(`(^|[^a-z0-9])${escape(n)}($|[^a-z0-9])`).test(words)))
}

/** The logo's colour where it must stand on a dark background: near-black brands (Apple, GitHub…) turn white. */
export function logoColor(hex: string, dark: boolean): string {
  if (!dark) return `#${hex}`
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.06 ? '#ffffff' : `#${hex}`
}
