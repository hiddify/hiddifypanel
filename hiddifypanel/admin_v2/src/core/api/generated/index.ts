import { getHttp } from '../client'

export type CustomProxyMode =
  | 'domains_l7_gateway'
  | 'domains_sni_gateway'
  | 'domains_auto_public_ports'
  | 'domains_single_public_port'
  | 'ip'

export interface ServerConfig {
  core?: string
  inbound_tcp_ports?: number[]
  inbound_udp_ports?: number[]
  inbound_port?: number | null
  tag?: string
  direct_port_access?: boolean
  template_slugs?: string[]
  inbound_template?: string
}

export interface ClientCoreConfig {
  core: string
  version?: string | null
  min_version?: string | null
  max_version?: string | null
  slug?: string | null
  is_builtin?: boolean
  outbounds_template?: string
  override?: boolean
}

export interface ClientConfig {
  sublink?: {
    core?: string
    version?: string | null
    do_base64_after?: boolean
    outbounds_template?: string
  }
  core_configs?: ClientCoreConfig[]
}

export type L7Proto = 'h1' | 'h2' | 'h3'

export type ProxyProto =
  | 'vless'
  | 'trojan'
  | 'vmess'
  | 'ss'
  | 'v2ray'
  | 'ssr'
  | 'ssh'
  | 'tuic'
  | 'hysteria'
  | 'hysteria2'
  | 'wireguard'
  | 'naive'
  | 'mieru'
  | 'anytls'
  | 'dnstt'

export interface CustomProxy {
  id?: number
  name: string
  slug?: string
  enable?: boolean
  mode: CustomProxyMode
  proto?: ProxyProto
  l7_proto?: L7Proto | null
  alpns?: string[]
  download_alpns?: string[]
  tags?: string[]
  domain_modes?: string[]
  custom_path?: string
  domain_ids?: number[]
  faketls_domains?: string[]
  server_config?: ServerConfig
  client_config?: ClientConfig
  sort_order?: number
  client_cores?: string[]
  server_core?: string
  is_builtin?: boolean
  server_override?: boolean
  client_override?: boolean
  builtin?: Record<string, unknown>
  builtin_overrides?: Record<string, boolean>
  builtin_server_config?: string
  builtin_client_config?: ClientConfig
}

export interface ProxyTemplate {
  id?: number
  slug: string
  core: string
  category: string
  name: string
  description?: string
  content?: string
  is_builtin?: boolean
  builtin_override?: boolean
  builtin_content?: string
}

export interface DomainOption {
  id: number
  domain: string
  alias?: string
  mode?: string
}

export interface RenderErrorDetail {
  phase?: string | null
  line?: number | null
  column?: number | null
  message?: string | null
  source?: string | null
  excerpt?: string | null
  template_source?: string | null
  template_excerpt?: string | null
  label?: string | null
}

export interface ValidationIssue {
  code: string
  message: string
  detail?: RenderErrorDetail | null
}

export interface ValidationResult {
  ok: boolean
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
  compiled_preview?: string
  compiled_json?: unknown
}

export interface TemplatePreviewResult {
  ok: boolean
  rendered: string
  parsed?: unknown
  skipped?: boolean
  error?: string | null
  error_detail?: RenderErrorDetail | null
  warnings?: ValidationIssue[]
}

export interface GeneratedSection {
  core: string
  version?: string | null
  label?: string | null
  index?: number | null
  rendered: string
  parsed?: unknown
  skipped: boolean
  error?: string | null
  error_detail?: RenderErrorDetail | null
  auto?: boolean
  variant_label?: string | null
  configs?: GeneratedSection[] | null
  sublink_formats?: SublinkFormats | null
  clash_yaml?: string | null
  config_yaml?: string | null
}

export interface SublinkFormats {
  raw: string
  vless_json?: Record<string, unknown> | null
  vless_uri?: string | null
  vmess_json?: Record<string, unknown> | null
  vmess_uri?: string | null
  parse_error?: string | null
}

export interface GenerateExampleResult {
  ok: boolean
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
  context: Record<string, unknown>
  server?: GeneratedSection | null
  clients: GeneratedSection[]
  auto_client_cores?: string[]
  auto_client_core?: string | null
  default_client_core?: string | null
}

export interface GenerateExampleInput {
  custom_proxy_id: number
  domain?: string
  domain_id?: number
  user_id?: number
  user_uuid?: string
  ip?: string
  user_agent?: string
  ignore_skip?: boolean
}

export interface CustomProxyPreviewInput extends Partial<GenerateExampleInput> {
  proxy: Partial<CustomProxy>
  proxy_id?: number
  side: string
  core: string
  template: string
  require_user?: boolean
}

export interface BaseConfigPreviewInput extends Partial<GenerateExampleInput> {
  side: string
  core: string
  version?: string
  content: string
}

export interface GenerateBundleInput {
  domain?: string
  domain_id?: number
  user_id?: number
  user_uuid?: string
  ip?: string
  user_agent?: string
}

export interface GenerateBundleResult {
  ok: boolean
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
  context: Record<string, unknown>
  servers: GeneratedSection[]
  clients: GeneratedSection[]
}

export interface PanelUserOption {
  id?: number
  uuid?: string
  name?: string
}

export interface CustomProxyMeta {
  modes: string[]
  protos: string[]
  alpns: string[]
  l7_protos: string[]
  domain_modes: string[]
  server_cores: string[]
  client_cores: string[]
  template_categories: string[]
  suggested_tags?: string[]
  default_sublink_link?: string
  example_user_agents?: Array<{ id: string; label: string; value: string }>
}

export const customProxiesApi = {
  list: () => getHttp().get<CustomProxy[]>('/custom-proxies/').then((r) => r.data),
  get: (id: number) => getHttp().get<CustomProxy>(`/custom-proxies/${id}/`).then((r) => r.data),
  create: (data: CustomProxy) => getHttp().post<CustomProxy>('/custom-proxies/', data).then((r) => r.data),
  update: (id: number, data: Partial<CustomProxy>) =>
    getHttp().patch<CustomProxy>(`/custom-proxies/${id}/`, data).then((r) => r.data),
  delete: (id: number) => getHttp().delete(`/custom-proxies/${id}/`),
  enable: (id: number, enable: boolean) =>
    getHttp().patch<CustomProxy>(`/custom-proxies/${id}/enable/`, { enable }).then((r) => r.data),
  duplicate: (id: number) => getHttp().post<CustomProxy>(`/custom-proxies/${id}/duplicate/`).then((r) => r.data),
  validate: (data: Partial<CustomProxy> & { sections?: string[] }) =>
    getHttp().post<ValidationResult>('/custom-proxies/validate/', data).then((r) => r.data),
  validateById: (id: number, data?: Partial<CustomProxy> & { sections?: string[] }) =>
    getHttp().post<ValidationResult>(`/custom-proxies/${id}/validate/`, data ?? {}).then((r) => r.data),
  preview: (data: CustomProxyPreviewInput) =>
    getHttp().post<TemplatePreviewResult>('/custom-proxies/preview/', data).then((r) => r.data),
  generateExample: (data: GenerateExampleInput) =>
    getHttp().post<GenerateExampleResult>('/custom-proxies/generate-example/', data).then((r) => r.data),
  generateExampleById: (id: number, data?: GenerateExampleInput) =>
    getHttp()
      .post<GenerateExampleResult>(`/custom-proxies/${id}/generate-example/`, data ?? {})
      .then((r) => r.data),
  generateBundle: (data?: GenerateBundleInput) =>
    getHttp().post<GenerateBundleResult>('/custom-proxies/generate-bundle/', data ?? {}).then((r) => r.data),
  listUsers: () => getHttp().get<PanelUserOption[]>('/user/').then((r) => r.data),
  meta: () => getHttp().get<CustomProxyMeta>('/custom-proxies/meta/').then((r) => r.data),
  exportBundle: (data: Partial<CustomProxy> & { exclude_builtin_templates?: boolean }) =>
    getHttp().post<CustomProxyBundle>('/custom-proxies/export/', data).then((r) => r.data),
  importBundle: (data: CustomProxyBundle) =>
    getHttp()
      .post<{ proxy: Partial<CustomProxy>; slug_map: Record<string, string>; templates_imported: number }>(
        '/custom-proxies/import/',
        data,
      )
      .then((r) => r.data),
}

export interface CustomProxyBundle {
  version: number
  proxy: Partial<CustomProxy>
  templates: Array<{
    slug: string
    core: string
    category: string
    name: string
    description?: string
    content?: string
  }>
}

export const proxyTemplatesApi = {
  list: (params?: { core?: string; category?: string }) =>
    getHttp().get<ProxyTemplate[]>('/proxy-templates/', { params }).then((r) => r.data),
  get: (id: number) => getHttp().get<ProxyTemplate>(`/proxy-templates/${id}/`).then((r) => r.data),
  create: (data: ProxyTemplate) => getHttp().post<ProxyTemplate>('/proxy-templates/', data).then((r) => r.data),
  update: (id: number, data: Partial<ProxyTemplate>) =>
    getHttp().patch<ProxyTemplate>(`/proxy-templates/${id}/`, data).then((r) => r.data),
  delete: (id: number) => getHttp().delete(`/proxy-templates/${id}/`),
  duplicate: (id: number) => getHttp().post<ProxyTemplate>(`/proxy-templates/${id}/duplicate/`).then((r) => r.data),
}

export const domainsApi = {
  options: (params?: { modes?: string[] }) => {
    const modes = params?.modes?.filter(Boolean).join(',')
    return getHttp()
      .get<DomainOption[]>('/domains/options/', { params: modes ? { modes } : undefined })
      .then((r) => r.data)
  },
  create: (data: { domain: string; alias?: string; mode?: string }) =>
    getHttp().post<DomainOption>('/domains/', data).then((r) => r.data),
}

export interface ProxyBaseConfig {
  id?: number
  side: string
  core: string
  version?: string
  name: string
  description?: string
  content?: string
  is_builtin?: boolean
  enable?: boolean
  builtin_override?: boolean
  builtin_content?: string
}

export interface ProxyBaseConfigMeta {
  sides: string[]
  cores_by_side: Record<string, string[]>
  template_category: string
}

export interface BaseConfigValidationResult {
  ok: boolean
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
}

export interface ProxyBaseConfigBundle {
  version: number
  base_config: Partial<ProxyBaseConfig>
  templates: CustomProxyBundle['templates']
}

export const proxyBaseConfigsApi = {
  list: (params?: { side?: string; core?: string }) =>
    getHttp().get<ProxyBaseConfig[]>('/proxy-base-configs/', { params }).then((r) => r.data),
  get: (id: number) => getHttp().get<ProxyBaseConfig>(`/proxy-base-configs/${id}/`).then((r) => r.data),
  create: (data: ProxyBaseConfig) =>
    getHttp().post<ProxyBaseConfig>('/proxy-base-configs/', data).then((r) => r.data),
  update: (id: number, data: Partial<ProxyBaseConfig>) =>
    getHttp().patch<ProxyBaseConfig>(`/proxy-base-configs/${id}/`, data).then((r) => r.data),
  enable: (id: number, enable: boolean) =>
    getHttp().patch<ProxyBaseConfig>(`/proxy-base-configs/${id}/`, { enable }).then((r) => r.data),
  delete: (id: number) => getHttp().delete(`/proxy-base-configs/${id}/`),
  duplicate: (id: number) =>
    getHttp().post<ProxyBaseConfig>(`/proxy-base-configs/${id}/duplicate/`).then((r) => r.data),
  meta: () => getHttp().get<ProxyBaseConfigMeta>('/proxy-base-configs/meta/').then((r) => r.data),
  validate: (data: Partial<ProxyBaseConfig>) =>
    getHttp().post<BaseConfigValidationResult>('/proxy-base-configs/validate/', data).then((r) => r.data),
  preview: (data: BaseConfigPreviewInput) =>
    getHttp().post<TemplatePreviewResult>('/proxy-base-configs/preview/', data).then((r) => r.data),
  exportBundle: (data: Partial<ProxyBaseConfig> & { exclude_builtin_templates?: boolean }) =>
    getHttp().post<ProxyBaseConfigBundle>('/proxy-base-configs/export/', data).then((r) => r.data),
  importBundle: (data: ProxyBaseConfigBundle) =>
    getHttp()
      .post<{ base_config: Partial<ProxyBaseConfig>; slug_map: Record<string, string>; templates_imported: number }>(
        '/proxy-base-configs/import/',
        data,
      )
      .then((r) => r.data),
}

export interface TemplateVariable {
  category?: string
  category_label?: string
  name: string
  access: string
  access_bracket?: string
  value?: unknown
  label: string
  description: string
}

export interface TemplateVariableGroup {
  id: string
  label: string
  variables: TemplateVariable[]
}

export interface TemplateVariablesResponse {
  groups: TemplateVariableGroup[]
  variables?: TemplateVariable[]
}

export const templateVariablesApi = {
  list: (params?: { values?: boolean }) =>
    getHttp()
      .get<TemplateVariablesResponse>('/template-variables/', {
        params: params?.values ? { values: 1 } : undefined,
      })
      .then((r) => r.data),
}

export const adminApi = {
  me: () => getHttp().get<{ lang?: string }>('/me/').then((r) => r.data),
}
