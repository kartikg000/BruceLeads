import { useState } from 'react'
import { MoreHorizontal, Trash2, Mail, CheckCircle, AlertCircle, RefreshCw, ExternalLink } from 'lucide-react'
import clsx from 'clsx'

export default function LeadTable({ leads, selectedIds, enrichingIds = [], onToggleSelect, onSelectAll }) {
    if (!leads || leads.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-20 text-center border border-dashed border-zinc-800 rounded-xl">
                <p className="text-zinc-500 mb-2">No leads found.</p>
                <p className="text-zinc-600 text-sm">Use the 'Find Leads' page to scrape some data.</p>
            </div>
        )
    }

    const allSelected = leads.length > 0 && selectedIds.length === leads.length

    return (
        <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900">
            <table className="w-full text-left text-sm">
                <thead className="bg-zinc-800/50 text-zinc-400 uppercase tracking-wider text-xs font-medium">
                    <tr>
                        <th className="p-4 w-10">
                            <input
                                type="checkbox"
                                className="rounded border-zinc-600 bg-zinc-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                                checked={allSelected}
                                onChange={(e) => onSelectAll(e.target.checked)}
                            />
                        </th>
                        <th className="p-4">Business</th>
                        <th className="p-4">Contact</th>
                        <th className="p-4">Status</th>
                        <th className="p-4">Intent</th>
                        <th className="p-4 text-right">Actions</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                    {leads.map((lead) => {
                        const isEnriching = enrichingIds.includes(lead.id)
                        return (
                            <tr
                                key={lead.id}
                                className={clsx(
                                    "transition-colors group",
                                    selectedIds.includes(lead.id) && "bg-zinc-800/50",
                                    isEnriching && "opacity-60",
                                    !isEnriching && "hover:bg-zinc-800/30"
                                )}
                            >
                                <td className="p-4">
                                    <input
                                        type="checkbox"
                                        className="rounded border-zinc-600 bg-zinc-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                                        checked={selectedIds.includes(lead.id)}
                                        onChange={() => onToggleSelect(lead.id)}
                                    />
                                </td>
                                <td className="p-4">
                                    <div className="flex items-center gap-3">
                                        {isEnriching && <RefreshCw size={16} className="animate-spin text-purple-400" />}
                                        <div>
                                            <div className="font-medium text-white">{lead.business_name}</div>
                                            <div className="text-zinc-500 text-xs">{lead.owner_name || "Owner Unknown"}</div>
                                        </div>
                                    </div>
                                </td>
                                <td className="p-4">
                                    {lead.email ? (
                                        <div className="space-y-1">
                                            <div className="flex items-center gap-2 text-zinc-300">
                                                <Mail size={14} className="text-zinc-500" />
                                                {lead.email}
                                            </div>
                                            {lead.phone && (
                                                <div className="text-xs text-zinc-500">{lead.phone}</div>
                                            )}
                                        </div>
                                    ) : (
                                        <span className="text-zinc-600 italic">Not enriched</span>
                                    )}
                                </td>
                                <td className="p-4">
                                    <StatusBadge status={lead.status} />
                                </td>
                                <td className="p-4">
                                    {lead.intent_score > 0 ? (
                                        <div className="flex items-center gap-1 text-emerald-400">
                                            <span className="font-bold">{lead.intent_score}</span>/10
                                        </div>
                                    ) : (
                                        <span className="text-zinc-600">-</span>
                                    )}
                                </td>
                                <td className="p-4 text-right">
                                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        {lead.website && (
                                            <a
                                                href={lead.website}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="p-2 text-zinc-500 hover:text-white rounded-lg hover:bg-zinc-700/50 transition-colors"
                                                title="Visit Website"
                                            >
                                                <ExternalLink size={16} />
                                            </a>
                                        )}
                                        <button className="p-2 text-zinc-500 hover:text-white rounded-lg hover:bg-zinc-700/50 transition-colors">
                                            <MoreHorizontal size={16} />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

function StatusBadge({ status }) {
    const styles = {
        'pending': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
        'enriched': 'bg-purple-500/10 text-purple-400 border-purple-500/20',
        'generated': 'bg-orange-500/10 text-orange-400 border-orange-500/20',
        'draft': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
        'sent': 'bg-green-500/10 text-green-400 border-green-500/20',
        'failed': 'bg-red-500/10 text-red-400 border-red-500/20',
    }

    const displayNames = {
        'pending': 'NEW',
        'enriched': 'ENRICHED',
        'generated': 'EMAIL READY',
        'draft': 'DRAFT',
        'sent': 'SENT',
        'failed': 'FAILED',
    }

    const style = styles[status] || 'bg-zinc-800 text-zinc-400 border-zinc-700'
    const displayStatus = displayNames[status] || status?.toUpperCase() || 'UNKNOWN'

    return (
        <span className={clsx("inline-flex px-2.5 py-1 rounded-md border text-xs font-medium uppercase tracking-wider", style)}>
            {displayStatus}
        </span>
    )
}
