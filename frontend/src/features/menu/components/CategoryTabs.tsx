import type { ReactNode } from 'react'

interface CategoryTabsProps {
  categories: Array<{ id: number; name: string; itemCount: number }>
  activeId: number | 'all'
  totalCount: number
  onChange: (id: number | 'all') => void
}

export function CategoryTabs({ categories, activeId, totalCount, onChange }: CategoryTabsProps) {
  return (
    <div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto">
      <TabBtn active={activeId === 'all'} onClick={() => onChange('all')}>
        All ({totalCount})
      </TabBtn>
      {categories.map((cat) => (
        <TabBtn key={cat.id} active={activeId === cat.id} onClick={() => onChange(cat.id)}>
          {cat.name} ({cat.itemCount})
        </TabBtn>
      ))}
    </div>
  )
}

function TabBtn({ active, children, onClick }: { active: boolean; children: ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`shrink-0 rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
        active
          ? 'border-accent bg-accent/10 text-accent'
          : 'border-line bg-white text-muted hover:border-accent/40 hover:text-ink'
      }`}
    >
      {children}
    </button>
  )
}
