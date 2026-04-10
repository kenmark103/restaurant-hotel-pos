import { FormEvent, useState } from 'react'

import { useSettings, type AppSettings } from '@/contexts/SettingsContext'
import { Input } from '@/shared/ui/Input'
import { Button } from '@/shared/ui/Button'

const CURRENCIES = [
  { code: 'KES', symbol: 'KES', locale: 'en-KE', label: 'Kenyan Shilling (KES)' },
  { code: 'USD', symbol: '$',   locale: 'en-US', label: 'US Dollar (USD)' },
  { code: 'GBP', symbol: '£',   locale: 'en-GB', label: 'British Pound (GBP)' },
  { code: 'EUR', symbol: '€',   locale: 'de-DE', label: 'Euro (EUR)' },
  { code: 'TZS', symbol: 'TZS', locale: 'sw-TZ', label: 'Tanzanian Shilling (TZS)' },
  { code: 'UGX', symbol: 'UGX', locale: 'sw-UG', label: 'Ugandan Shilling (UGX)' },
]

export function SettingsPage() {
  const { settings, updateSettings, formatPrice } = useSettings()
  const [form, setForm] = useState<AppSettings>({ ...settings })
  const [saved, setSaved] = useState(false)

  const handleCurrencyChange = (code: string) => {
    const curr = CURRENCIES.find((c) => c.code === code)
    if (!curr) return
    setForm((f) => ({
      ...f,
      currency: curr.code,
      currencySymbol: curr.symbol,
      currencyLocale: curr.locale,
    }))
  }

  const handleSave = (e: FormEvent) => {
    e.preventDefault()
    updateSettings(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="label">Settings</p>
        <h2 className="mt-1 text-lg font-bold text-ink">System configuration</h2>
      </div>

      <form className="space-y-4" onSubmit={handleSave}>

        {/* Restaurant identity */}
        <SettingsCard title="Restaurant identity">
          <Field label="Restaurant name">
            <Input
              value={form.restaurantName}
              onChange={(e) => setForm((f) => ({ ...f, restaurantName: e.target.value }))}
              placeholder="e.g. The Grand Restaurant"
            />
          </Field>
          <Field label="Receipt footer message">
            <Input
              value={form.receiptFooter}
              onChange={(e) => setForm((f) => ({ ...f, receiptFooter: e.target.value }))}
              placeholder="Thank you for dining with us."
            />
          </Field>
          <Field label="Timezone">
            <Input
              value={form.timezone}
              onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))}
              placeholder="Africa/Nairobi"
            />
          </Field>
        </SettingsCard>

        {/* Currency & tax */}
        <SettingsCard title="Currency & tax">
          <Field label="Currency">
            <select
              className="field text-[13px]"
              value={form.currency}
              onChange={(e) => handleCurrencyChange(e.target.value)}
            >
              {CURRENCIES.map((c) => (
                <option key={c.code} value={c.code}>{c.label}</option>
              ))}
            </select>
          </Field>

          <Field label="Tax rate (%)">
            <Input
              type="number"
              min={0}
              max={100}
              step={0.1}
              value={form.taxRate}
              onChange={(e) => setForm((f) => ({ ...f, taxRate: Number(e.target.value) }))}
            />
          </Field>

          <Field label="Tax treatment">
            <select
              className="field text-[13px]"
              value={form.taxInclusive ? 'inclusive' : 'exclusive'}
              onChange={(e) => setForm((f) => ({ ...f, taxInclusive: e.target.value === 'inclusive' }))}
            >
              <option value="inclusive">Tax-inclusive (prices already include tax)</option>
              <option value="exclusive">Tax-exclusive (tax added at checkout)</option>
            </select>
          </Field>

          {/* Preview */}
          <div className="mt-2 rounded-btn border border-accent-border bg-accent-light p-3 text-[12px] text-accent-text">
            <p className="font-semibold">Price preview</p>
            <p className="mt-1">
              Item at 1,000 → displays as{' '}
              <span className="font-mono font-bold">
                {new Intl.NumberFormat(form.currencyLocale, {
                  style: 'currency',
                  currency: form.currency,
                }).format(1000)}
              </span>
            </p>
          </div>
        </SettingsCard>

        <div className="flex items-center gap-3">
          <Button type="submit">Save settings</Button>
          {saved && (
            <span className="text-[12px] font-medium text-success">
              ✓ Saved
            </span>
          )}
        </div>
      </form>
    </div>
  )
}

function SettingsCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <p className="section-title mb-4">{title}</p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {children}
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="label mb-1.5 block">{label}</label>
      {children}
    </div>
  )
}