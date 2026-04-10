import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

// ─── Types ──────────────────────────────────────────────────────────────────

export interface AppSettings {
  restaurantName: string
  currency: string          // ISO 4217 code: KES, USD, GBP
  currencySymbol: string    // Display symbol: KES, $, £
  currencyLocale: string    // BCP 47 locale for Intl.NumberFormat: en-KE, en-US
  taxRate: number           // Percentage, e.g. 16 for 16%
  taxInclusive: boolean     // true = prices already include tax
  timezone: string          // IANA timezone: Africa/Nairobi
  defaultBranchId: number | null
  receiptFooter: string
}

interface SettingsContextValue {
  settings: AppSettings
  updateSettings: (patch: Partial<AppSettings>) => void
  formatPrice: (amount: number | string) => string
  computeTax: (amount: number) => number
  priceWithTax: (amount: number) => number
}

// ─── Defaults ───────────────────────────────────────────────────────────────

const STORAGE_KEY = 'pos_app_settings'

const DEFAULT_SETTINGS: AppSettings = {
  restaurantName: 'RestaurantOS',
  currency: 'KES',
  currencySymbol: 'KES',
  currencyLocale: 'en-KE',
  taxRate: 16,
  taxInclusive: true,
  timezone: 'Africa/Nairobi',
  defaultBranchId: null,
  receiptFooter: 'Thank you for dining with us.',
}

function loadFromStorage(): AppSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_SETTINGS
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) }
  } catch {
    return DEFAULT_SETTINGS
  }
}

// ─── Context ─────────────────────────────────────────────────────────────────

const SettingsContext = createContext<SettingsContextValue | null>(null)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(loadFromStorage)

  const updateSettings = useCallback((patch: Partial<AppSettings>) => {
    setSettings((current) => {
      const next = { ...current, ...patch }
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      } catch {
        // localStorage unavailable — silently continue
      }
      return next
    })
  }, [])

  /**
   * Format a raw number as a price string using the configured currency.
   * e.g. 1250 → "KES 1,250.00" or "$1,250.00"
   */
  const formatPrice = useCallback(
    (amount: number | string): string => {
      const num = typeof amount === 'string' ? parseFloat(amount) : amount
      if (isNaN(num)) return `${settings.currencySymbol} —`
      return new Intl.NumberFormat(settings.currencyLocale, {
        style: 'currency',
        currency: settings.currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(num)
    },
    [settings.currency, settings.currencyLocale],
  )

  /**
   * Extract the tax portion from an inclusive price, or compute tax on top of an exclusive price.
   */
  const computeTax = useCallback(
    (amount: number): number => {
      if (settings.taxInclusive) {
        // Tax is already inside the price: tax = amount - (amount / (1 + rate))
        return amount - amount / (1 + settings.taxRate / 100)
      }
      return (amount * settings.taxRate) / 100
    },
    [settings.taxRate, settings.taxInclusive],
  )

  /**
   * Return the final price the customer pays.
   * If tax-exclusive, adds tax on top. If inclusive, returns amount unchanged.
   */
  const priceWithTax = useCallback(
    (amount: number): number => {
      if (settings.taxInclusive) return amount
      return amount + (amount * settings.taxRate) / 100
    },
    [settings.taxRate, settings.taxInclusive],
  )

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, formatPrice, computeTax, priceWithTax }}>
      {children}
    </SettingsContext.Provider>
  )
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext)
  if (!ctx) throw new Error('useSettings must be used within <SettingsProvider>')
  return ctx
}