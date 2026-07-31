import { Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { EmptyState } from '@/components/common/EmptyState'
import { formatYearRange } from '@/utils/format'
import type { VehicleCompatibility } from '@/types/product'

interface CompatibilityTableProps {
  vehicles: VehicleCompatibility[]
}

export function CompatibilityTable({ vehicles }: CompatibilityTableProps) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return vehicles
    return vehicles.filter((vehicle) => `${vehicle.make} ${vehicle.model} ${vehicle.engine ?? ''}`.toLowerCase().includes(q))
  }, [vehicles, query])

  if (vehicles.length === 0) {
    return (
      <EmptyState
        title="No compatibility data yet"
        description="Vehicle fitment for this product hasn't been added to the catalog."
      />
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="relative max-w-xs">
        <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-subtle" aria-hidden="true" />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search compatible vehicle"
          aria-label="Search compatible vehicle"
          className="w-full rounded-lg border border-border-strong bg-surface py-2 pr-3 pl-9 text-sm text-foreground placeholder:text-subtle focus:border-accent focus:ring-2 focus:ring-accent/20 focus:outline-none"
        />
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-muted">No vehicles match &quot;{query}&quot;.</p>
      ) : (
        <>
          <div className="hidden overflow-x-auto rounded-xl border border-border sm:block">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface-2 text-xs font-semibold tracking-wide text-muted uppercase">
                <tr>
                  <th scope="col" className="px-4 py-3">
                    Make
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Model
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Engine
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Year Range
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((vehicle, index) => (
                  <tr key={`${vehicle.make}-${vehicle.model}-${index}`} className="text-foreground">
                    <td className="px-4 py-3 font-medium">{vehicle.make}</td>
                    <td className="px-4 py-3">{vehicle.model}</td>
                    <td className="px-4 py-3 font-mono text-muted">{vehicle.engine ?? '—'}</td>
                    <td className="px-4 py-3 font-mono text-muted">{formatYearRange(vehicle.yearStart, vehicle.yearEnd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col gap-3 sm:hidden">
            {filtered.map((vehicle, index) => (
              <div key={`${vehicle.make}-${vehicle.model}-${index}`} className="rounded-lg border border-border bg-surface p-4">
                <p className="text-sm font-semibold text-foreground">
                  {vehicle.make} {vehicle.model}
                </p>
                <p className="mt-1 font-mono text-xs text-muted">{vehicle.engine ?? 'Engine not specified'}</p>
                <p className="mt-1 font-mono text-xs text-muted">{formatYearRange(vehicle.yearStart, vehicle.yearEnd)}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
