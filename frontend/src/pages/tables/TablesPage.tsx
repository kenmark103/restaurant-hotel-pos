import { FormEvent, useEffect, useState } from 'react'

import { useBranches } from '@/features/staff/hooks/useBranches'
import { useCreateTable, useTables, useUpdateTableStatus } from '@/features/tables/hooks/useTables'
import { type TableRecord } from '@/features/tables/types'
import { Spinner } from '@/shared/ui/Spinner'
import { Input } from '@/shared/ui/Input'
import { Button } from '@/shared/ui/Button'

type Status = TableRecord['status']

const NEXT_STATUS: Record<Status, Status> = {
  available: 'occupied',
  occupied:  'cleaning',
  cleaning:  'available',
  reserved:  'occupied',
}

const STATUS_STYLE: Record<Status, { card: string; pill: string; label: string }> = {
  available: {
    card:  'border-success/40 bg-success-light hover:border-success/70',
    pill:  'bg-success-light text-success-text',
    label: 'Available',
  },
  occupied: {
    card:  'border-danger/40 bg-danger-light hover:border-danger/70',
    pill:  'bg-danger-light text-danger-text',
    label: 'Occupied',
  },
  reserved: {
    card:  'border-warning/40 bg-warning-light hover:border-warning/70',
    pill:  'bg-warning-light text-warning-text',
    label: 'Reserved',
  },
  cleaning: {
    card:  'border-info/40 bg-info-light hover:border-info/70',
    pill:  'bg-info-light text-info-text',
    label: 'Cleaning',
  },
}

export function TablesPage() {
  const { data: branches, isLoading: branchesLoading } = useBranches()
  const [selectedBranchId, setSelectedBranchId] = useState<number | null>(null)
  const [filter, setFilter] = useState<Status | 'all'>('all')
  const [addOpen, setAddOpen] = useState(false)
  const [formState, setFormState] = useState({ table_number: '', capacity: '4' })

  const { data: tables, isLoading } = useTables(selectedBranchId)
  const updateStatusMutation = useUpdateTableStatus(selectedBranchId)
  const createTableMutation = useCreateTable(selectedBranchId)

  useEffect(() => {
    if (!selectedBranchId && branches?.length) {
      setSelectedBranchId(branches[0].id)
    }
  }, [branches, selectedBranchId])

  const handleAdvance = async (table: TableRecord) => {
    await updateStatusMutation.mutateAsync({
      tableId: table.id,
      status: NEXT_STATUS[table.status],
    })
  }

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!selectedBranchId) return
    await createTableMutation.mutateAsync({
      branch_id: selectedBranchId,
      table_number: formState.table_number,
      capacity: Number(formState.capacity),
    })
    setFormState({ table_number: '', capacity: '4' })
    setAddOpen(false)
  }

  const displayed = tables?.filter((t) => filter === 'all' || t.status === filter) ?? []

  const counts = {
    available: tables?.filter((t) => t.status === 'available').length ?? 0,
    occupied:  tables?.filter((t) => t.status === 'occupied').length  ?? 0,
    reserved:  tables?.filter((t) => t.status === 'reserved').length  ?? 0,
    cleaning:  tables?.filter((t) => t.status === 'cleaning').length  ?? 0,
  }

  if (isLoading || branchesLoading) return <Spinner />

  return (
    <div className="flex h-full flex-col gap-4">

      {/* ── Toolbar ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Branch */}
        <select
          className="field h-9 w-auto min-w-[180px] text-[13px]"
          value={selectedBranchId ?? ''}
          onChange={(e) => setSelectedBranchId(e.target.value ? Number(e.target.value) : null)}
        >
          {branches?.map((b) => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>

        {/* Status filter tabs */}
        <div className="flex items-center gap-1 rounded-btn border border-line bg-panel p-1">
          {(['all', 'available', 'occupied', 'reserved', 'cleaning'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`rounded-[6px] px-3 py-1.5 text-[12px] font-medium capitalize transition
                ${filter === s ? 'bg-accent text-white' : 'text-muted hover:bg-appbg hover:text-ink'}`}
            >
              {s === 'all' ? `All (${tables?.length ?? 0})` : `${STATUS_STYLE[s].label} (${counts[s]})`}
            </button>
          ))}
        </div>

        <button
          className="btn-primary ml-auto text-[12px] py-1.5"
          onClick={() => setAddOpen((v) => !v)}
        >
          {addOpen ? '✕ Cancel' : '+ Add table'}
        </button>
      </div>

      {/* ── Add table panel ─────────────────────────────────────────── */}
      {addOpen && (
        <div className="card p-5">
          <p className="section-title mb-3">Add a table</p>
          <form className="flex flex-wrap items-end gap-3" onSubmit={handleCreate}>
            <div className="w-40">
              <label className="label mb-1 block">Table number</label>
              <Input
                placeholder="T1 / Bar-3"
                required
                value={formState.table_number}
                onChange={(e) => setFormState((s) => ({ ...s, table_number: e.target.value }))}
              />
            </div>
            <div className="w-28">
              <label className="label mb-1 block">Capacity</label>
              <Input
                type="number"
                min={1}
                required
                value={formState.capacity}
                onChange={(e) => setFormState((s) => ({ ...s, capacity: e.target.value }))}
              />
            </div>
            <Button disabled={createTableMutation.isPending || !selectedBranchId} type="submit">
              {createTableMutation.isPending ? 'Adding…' : 'Add table'}
            </Button>
          </form>
        </div>
      )}

      {/* ── Floor grid ──────────────────────────────────────────────── */}
      {displayed.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center py-20 text-center">
          <span className="text-5xl opacity-30">🪑</span>
          <p className="mt-4 text-[15px] font-semibold text-ink">
            {tables?.length ? 'No tables match this filter' : 'No tables set up yet'}
          </p>
          <p className="mt-1 text-[13px] text-muted">
            {tables?.length ? 'Try "All" to see every table.' : 'Add your first table to start managing the floor.'}
          </p>
          {!tables?.length && (
            <button className="btn-primary mt-5" onClick={() => setAddOpen(true)}>
              Add first table
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10">
          {displayed.map((table) => (
            <TableCard
              key={table.id}
              table={table}
              onAdvance={() => void handleAdvance(table)}
              isPending={updateStatusMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Table card ───────────────────────────────────────────────────────────────

function TableCard({
  table,
  onAdvance,
  isPending,
}: {
  table: TableRecord
  onAdvance: () => void
  isPending: boolean
}) {
  const style = STATUS_STYLE[table.status]

  return (
    <button
      className={`group flex flex-col items-center justify-center gap-1 rounded-card border-2 py-4 text-center transition ${style.card} disabled:cursor-wait`}
      onClick={onAdvance}
      disabled={isPending}
      title={`${table.table_number} · ${table.capacity} seats · Click to advance to ${NEXT_STATUS[table.status]}`}
    >
      <span className="font-mono text-[14px] font-bold text-ink leading-none">{table.table_number}</span>
      <span className="text-[10px] text-muted">{table.capacity}p</span>
      <span className={`mt-1 rounded-pill px-1.5 py-0.5 font-mono text-[8px] font-medium uppercase ${style.pill}`}>
        {style.label}
      </span>
    </button>
  )
}