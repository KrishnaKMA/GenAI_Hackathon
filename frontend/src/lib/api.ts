import axios from 'axios'
import type {
  ClaimInput,
  ClaimRecord,
  FactsheetEntry,
  InvestigatorReport,
  LoginResponse,
  RiskLevel,
} from '../types'

const OFFLINE_DEMO_USERS = {
  admin: { password: 'admin123', role: 'admin' },
  adjuster1: { password: 'pass123', role: 'adjuster' },
  investigator1: { password: 'pass123', role: 'investigator' },
} as const

function resolveApiBaseUrl() {
  const explicitUrl = import.meta.env.VITE_API_URL?.trim()
  if (explicitUrl) return explicitUrl

  const explicitHost = import.meta.env.VITE_API_HOST?.trim()
  if (explicitHost) {
    return explicitHost.startsWith('http') ? explicitHost : `https://${explicitHost}`
  }

  return 'http://localhost:8000'
}

const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('cs_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

type ClaimListParams = {
  limit?: number
  offset?: number
  status?: string
  risk_level?: RiskLevel
}

type CacheEntry<T> = {
  value: T
  expiresAt: number
}

const responseCache = new Map<string, CacheEntry<unknown>>()
const inflightRequests = new Map<string, Promise<unknown>>()
const CACHE_STORAGE_PREFIX = 'cs_cache_'
const REPORT_STORAGE_PREFIX = 'cs_report_'

function getCachedValue<T>(key: string): T | null {
  const entry = responseCache.get(key)
  if (entry) {
    if (entry.expiresAt <= Date.now()) {
      responseCache.delete(key)
    } else {
      return entry.value as T
    }
  }

  const stored = sessionStorage.getItem(`${CACHE_STORAGE_PREFIX}${key}`)
  if (!stored) return null

  try {
    const parsed = JSON.parse(stored) as CacheEntry<T>
    if (parsed.expiresAt <= Date.now()) {
      sessionStorage.removeItem(`${CACHE_STORAGE_PREFIX}${key}`)
      return null
    }
    responseCache.set(key, parsed as CacheEntry<unknown>)
    return parsed.value
  } catch {
    sessionStorage.removeItem(`${CACHE_STORAGE_PREFIX}${key}`)
    return null
  }
}

function setCachedValue<T>(key: string, value: T, ttlMs: number) {
  const entry = {
    value,
    expiresAt: Date.now() + ttlMs,
  }
  responseCache.set(key, entry)
  sessionStorage.setItem(`${CACHE_STORAGE_PREFIX}${key}`, JSON.stringify(entry))
}

async function getCachedRequest<T>(key: string, ttlMs: number, fetcher: () => Promise<T>): Promise<T> {
  const cached = getCachedValue<T>(key)
  if (cached !== null) {
    return cached
  }

  const inflight = inflightRequests.get(key)
  if (inflight) {
    return inflight as Promise<T>
  }

  const request = fetcher()
    .then((value) => {
      setCachedValue(key, value, ttlMs)
      return value
    })
    .finally(() => {
      inflightRequests.delete(key)
    })

  inflightRequests.set(key, request)
  return request
}

function claimListCacheKey(params: ClaimListParams): string {
  const normalized = {
    limit: params.limit ?? 20,
    offset: params.offset ?? 0,
    status: params.status,
    risk_level: params.risk_level,
  }
  const search = new URLSearchParams()
  Object.entries(normalized).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  })
  return `claims:${search.toString()}`
}

export function cacheReport(report: InvestigatorReport) {
  sessionStorage.setItem(`${REPORT_STORAGE_PREFIX}${report.claim_token}`, JSON.stringify(report))
}

export function getCachedReport(claimToken: string): InvestigatorReport | null {
  const stored = sessionStorage.getItem(`${REPORT_STORAGE_PREFIX}${claimToken}`)
  if (!stored) return null
  try {
    return JSON.parse(stored) as InvestigatorReport
  } catch {
    sessionStorage.removeItem(`${REPORT_STORAGE_PREFIX}${claimToken}`)
    return null
  }
}

function removeCachedValue(key: string) {
  responseCache.delete(key)
  inflightRequests.delete(key)
  sessionStorage.removeItem(`${CACHE_STORAGE_PREFIX}${key}`)
}

export function invalidateClaimsCache() {
  for (const key of Array.from(responseCache.keys())) {
    if (key.startsWith('claims:')) {
      removeCachedValue(key)
    }
  }
  for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
    const storageKey = sessionStorage.key(index)
    if (storageKey?.startsWith(`${CACHE_STORAGE_PREFIX}claims:`)) {
      sessionStorage.removeItem(storageKey)
    }
  }
}

export function invalidateFactsheetsCache() {
  for (const key of Array.from(responseCache.keys())) {
    if (key.startsWith('factsheets:')) {
      removeCachedValue(key)
    }
  }
  for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
    const storageKey = sessionStorage.key(index)
    if (storageKey?.startsWith(`${CACHE_STORAGE_PREFIX}factsheets:`)) {
      sessionStorage.removeItem(storageKey)
    }
  }
}

export function invalidateAdminStatsCache() {
  removeCachedValue('admin:stats')
}

export function invalidateReportCache(claimToken?: string) {
  if (claimToken) {
    sessionStorage.removeItem(`${REPORT_STORAGE_PREFIX}${claimToken}`)
    return
  }
  for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
    const storageKey = sessionStorage.key(index)
    if (storageKey?.startsWith(REPORT_STORAGE_PREFIX)) {
      sessionStorage.removeItem(storageKey)
    }
  }
}

export const authApi = {
  async login(username: string, password: string, totp_code?: string): Promise<LoginResponse> {
    try {
      const { data } = await apiClient.post<LoginResponse>('/auth/login', {
        username,
        password,
        totp_code,
      })
      return data
    } catch (error) {
      if (!axios.isAxiosError(error) || error.response) {
        throw error
      }

      const offlineUser = OFFLINE_DEMO_USERS[username as keyof typeof OFFLINE_DEMO_USERS]
      if (!offlineUser || offlineUser.password !== password) {
        throw new Error('Backend unreachable and demo credentials did not match')
      }

      return {
        access_token: `offline-demo-token-${username}`,
        token_type: 'bearer',
        role: offlineUser.role,
        username,
      }
    }
  },
}

export const claimsApi = {
  async list(params: ClaimListParams = {}): Promise<ClaimRecord[]> {
    const cacheKey = claimListCacheKey(params)
    return getCachedRequest(cacheKey, 15000, async () => {
      const { data } = await apiClient.get<ClaimRecord[]>('/claims', { params })
      return data
    })
  },

  async create(payload: ClaimInput): Promise<ClaimRecord> {
    const { data } = await apiClient.post<ClaimRecord>('/claims', payload, {
      timeout: 45000,
    })
    invalidateClaimsCache()
    invalidateAdminStatsCache()
    return data
  },

  async getFactsheets(limit = 10): Promise<FactsheetEntry[]> {
    return getCachedRequest(`factsheets:${limit}`, 15000, async () => {
      const { data } = await apiClient.get<FactsheetEntry[]>('/factsheets', {
        params: { limit },
      })
      return data
    })
  },
}

export const analysisApi = {
  async analyze(claimToken: string): Promise<InvestigatorReport> {
    const { data } = await apiClient.post<InvestigatorReport>(`/analyze/${claimToken}`, undefined, {
      timeout: 90000,
    })
    cacheReport(data)
    invalidateClaimsCache()
    invalidateFactsheetsCache()
    invalidateAdminStatsCache()
    return data
  },

  async getDemo(riskLevel: RiskLevel): Promise<InvestigatorReport> {
    const { data } = await apiClient.post<InvestigatorReport>(`/analyze/demo/${riskLevel}`, undefined, {
      timeout: 60000,
    })
    return data
  },
}

export const adminApi = {
  async getStats(): Promise<{
    total_claims: number
    flagged: number
    approved: number
    pending: number
    critical: number
  }> {
    return getCachedRequest('admin:stats', 15000, async () => {
      const { data } = await apiClient.get('/admin/stats')
      return data
    })
  },
}

export { apiClient }
