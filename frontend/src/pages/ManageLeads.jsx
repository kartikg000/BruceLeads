import { useState, useMemo, useRef } from 'react'
import { Sparkles, Trash2, Download, RefreshCw, CheckCircle, AlertCircle, FileSpreadsheet, Filter, Upload } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import clsx from 'clsx'
import * as XLSX from 'xlsx'
import LeadTable from '../components/LeadTable'

export default function ManageLeads() {
    const [selectedIds, setSelectedIds] = useState([])
    const [enrichingIds, setEnrichingIds] = useState([])
    const fileInputRef = useRef(null)
    const [notification, setNotification] = useState(null)
    const [scope, setScope] = useState('current') // 'current' or 'all'
    const queryClient = useQueryClient()

    // Get current search IDs from session storage
    const currentSearchIds = useMemo(() => {
        try {
            return JSON.parse(sessionStorage.getItem('currentSearchIds') || '[]')
        } catch {
            return []
        }
    }, [])

    // Fetch leads
    const { data: allLeads = [], isLoading, refetch } = useQuery({
        queryKey: ['leads'],
        queryFn: async () => {
            const res = await axios.get('/api/leads/')
            return Array.isArray(res.data) ? res.data : []
        }
    })

    // Filter leads based on scope
    const leads = useMemo(() => {
        if (scope === 'current' && currentSearchIds.length > 0) {
            return allLeads.filter(l => currentSearchIds.includes(l.id))
        }
        return allLeads
    }, [allLeads, scope, currentSearchIds])

    // Enrich Mutation
    const enrichMutation = useMutation({
        mutationFn: async (leadIds) => {
            return axios.post('/api/leads/enrich', { lead_ids: leadIds })
        },
        onMutate: (leadIds) => {
            setEnrichingIds(leadIds)
        },
        onSuccess: (response) => {
            setEnrichingIds([])
            setSelectedIds([])
            queryClient.invalidateQueries(['leads'])
            showNotification('success', `Enriched ${response.data?.enriched || 0} leads successfully!`)
        },
        onError: () => {
            setEnrichingIds([])
            showNotification('error', 'Failed to enrich leads. Please try again.')
        }
    })

    // Delete Mutation
    const deleteMutation = useMutation({
        mutationFn: async (leadIds) => {
            return axios.post('/api/leads/delete', { lead_ids: leadIds })
        },
        onSuccess: () => {
            setSelectedIds([])
            queryClient.invalidateQueries(['leads'])
            showNotification('success', 'Leads deleted successfully!')
        },
        onError: () => {
            showNotification('error', 'Failed to delete leads.')
        }
    })

    const showNotification = (type, message) => {
        setNotification({ type, message })
        setTimeout(() => setNotification(null), 4000)
    }

    // Selection Logic
    const handleToggleSelect = (id) => {
        if (selectedIds.includes(id)) {
            setSelectedIds(selectedIds.filter(lid => lid !== id))
        } else {
            setSelectedIds([...selectedIds, id])
        }
    }

    const handleSelectAll = (checked) => {
        if (checked && leads) {
            setSelectedIds(leads.map(l => l.id))
        } else {
            setSelectedIds([])
        }
    }

    const handleEnrich = () => {
        if (selectedIds.length === 0) return
        enrichMutation.mutate(selectedIds)
    }

    const handleDelete = () => {
        if (selectedIds.length === 0) return
        if (window.confirm(`Are you sure you want to delete ${selectedIds.length} lead(s)?`)) {
            deleteMutation.mutate(selectedIds)
        }
    }

    const handleExportCSV = () => {
        // Sanitize cell value: escape double-quotes and prevent CSV formula injection
        const sanitize = (val) => {
            let s = String(val || '').replace(/"/g, '""')
            // Prefix formula-trigger characters to prevent spreadsheet injection
            if (/^[=+\-@\t\r]/.test(s)) s = "'" + s
            return `"${s}"`
        }
        const csvContent = [
            ['Business Name', 'Owner', 'Email', 'Phone', 'Website', 'Status'].join(','),
            ...leads.map(l => [
                sanitize(l.business_name),
                sanitize(l.owner_name),
                sanitize(l.email),
                sanitize(l.phone),
                sanitize(l.website),
                sanitize(l.status)
            ].join(','))
        ].join('\n')

        const blob = new Blob([csvContent], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `bruce_leads_${scope}_${new Date().toISOString().split('T')[0]}.csv`
        a.click()
        URL.revokeObjectURL(url)
        showNotification('success', `Exported ${leads.length} leads to CSV!`)
    }

    const handleExportExcel = () => {
        const data = leads.map(l => ({
            'Business Name': l.business_name || '',
            'Owner': l.owner_name || '',
            'Email': l.email || '',
            'Phone': l.phone || '',
            'Website': l.website || '',
            'Address': l.address || '',
            'Source': l.source || '',
            'Status': l.status || '',
            'Intent Score': l.intent_score || 0
        }))

        const ws = XLSX.utils.json_to_sheet(data)
        const wb = XLSX.utils.book_new()
        XLSX.utils.book_append_sheet(wb, ws, 'Leads')
        XLSX.writeFile(wb, `bruce_leads_${scope}_${new Date().toISOString().split('T')[0]}.xlsx`)
        showNotification('success', `Exported ${leads.length} leads to Excel!`)
    }

    const handleImportCSV = async (e) => {
        const file = e.target.files?.[0]
        if (!file) return
        const formData = new FormData()
        formData.append('file', file)
        try {
            const res = await axios.post('/api/leads/import/csv', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            queryClient.invalidateQueries(['leads'])
            showNotification('success', `Imported ${res.data?.imported || 0} leads from CSV!`)
        } catch (err) {
            showNotification('error', err.response?.data?.detail || 'Failed to import CSV')
        }
        // Reset file input
        if (fileInputRef.current) fileInputRef.current.value = ''
    }

    return (
        <div className="space-y-6 max-w-7xl mx-auto">
            {/* Notification Toast */}
            <AnimatePresence>
                {notification && (
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className={clsx(
                            "fixed top-4 right-4 z-50 px-4 py-3 rounded-lg flex items-center gap-3 shadow-lg",
                            notification.type === 'success' ? "bg-green-500/20 border border-green-500/30 text-green-400" : "bg-red-500/20 border border-red-500/30 text-red-400"
                        )}
                    >
                        {notification.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                        <span className="text-sm font-medium">{notification.message}</span>
                    </motion.div>
                )}
            </AnimatePresence>

            <header className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Manage Data</h2>
                    <p className="text-zinc-400">View, filter, and enrich your scraped leads.</p>
                </div>
                <div className="flex gap-2">
                    {/* Scope Filter */}
                    {currentSearchIds.length > 0 && (
                        <div className="flex gap-1 bg-zinc-900 border border-zinc-800 p-1 rounded-lg">
                            <button
                                onClick={() => setScope('current')}
                                className={clsx(
                                    "px-3 py-1.5 rounded text-sm font-medium transition-all",
                                    scope === 'current' ? "bg-blue-500 text-white" : "text-zinc-400 hover:text-white"
                                )}
                            >
                                Current ({currentSearchIds.length})
                            </button>
                            <button
                                onClick={() => setScope('all')}
                                className={clsx(
                                    "px-3 py-1.5 rounded text-sm font-medium transition-all",
                                    scope === 'all' ? "bg-blue-500 text-white" : "text-zinc-400 hover:text-white"
                                )}
                            >
                                All ({allLeads.length})
                            </button>
                        </div>
                    )}

                    <button
                        onClick={() => refetch()}
                        className="p-2 bg-zinc-800 border border-zinc-700 rounded-lg hover:bg-zinc-700 transition-colors"
                        title="Refresh"
                    >
                        <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
                    </button>

                    {/* Import CSV */}
                    <input
                        type="file"
                        ref={fileInputRef}
                        accept=".csv"
                        onChange={handleImportCSV}
                        className="hidden"
                    />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        className="px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm font-medium hover:bg-zinc-700 transition-colors flex items-center gap-2"
                    >
                        <Upload size={16} /> Import
                    </button>

                    {/* Export Dropdown */}
                    <div className="relative group">
                        <button className="px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm font-medium hover:bg-zinc-700 transition-colors flex items-center gap-2">
                            <Download size={16} /> Export
                        </button>
                        <div className="absolute right-0 top-full mt-1 bg-zinc-900 border border-zinc-700 rounded-lg overflow-hidden shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 min-w-[160px]">
                            <button
                                onClick={handleExportCSV}
                                className="w-full px-4 py-2.5 text-left text-sm hover:bg-zinc-800 flex items-center gap-2"
                            >
                                <Download size={14} /> CSV (.csv)
                            </button>
                            <button
                                onClick={handleExportExcel}
                                className="w-full px-4 py-2.5 text-left text-sm hover:bg-zinc-800 flex items-center gap-2"
                            >
                                <FileSpreadsheet size={14} /> Excel (.xlsx)
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Batch Actions Toolbar */}
            <AnimatePresence>
                {selectedIds.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="bg-zinc-900 border border-zinc-700/50 p-3 rounded-xl flex items-center gap-4"
                    >
                        <span className="text-sm font-medium text-white ml-2">{selectedIds.length} selected</span>
                        <div className="h-4 w-px bg-zinc-700" />
                        <button
                            onClick={handleEnrich}
                            disabled={enrichMutation.isPending}
                            className="text-sm text-purple-400 hover:text-purple-300 font-medium flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-purple-500/10 transition-colors disabled:opacity-50"
                        >
                            {enrichMutation.isPending ? (
                                <><RefreshCw size={16} className="animate-spin" /> Enriching...</>
                            ) : (
                                <><Sparkles size={16} /> Enrich Leads</>
                            )}
                        </button>
                        <button
                            onClick={handleDelete}
                            disabled={deleteMutation.isPending}
                            className="text-sm text-red-400 hover:text-red-300 font-medium flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-red-500/10 transition-colors ml-auto disabled:opacity-50"
                        >
                            <Trash2 size={16} /> Delete
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Stats Bar */}
            <div className="grid grid-cols-4 gap-4">
                <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-xl">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider">Showing</p>
                    <p className="text-2xl font-bold">{leads.length}</p>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-xl">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider">New</p>
                    <p className="text-2xl font-bold text-blue-400">{leads.filter(l => l.status === 'pending').length}</p>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-xl">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider">Enriched</p>
                    <p className="text-2xl font-bold text-purple-400">{leads.filter(l => l.status === 'enriched').length}</p>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-xl">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider">Sent</p>
                    <p className="text-2xl font-bold text-green-400">{leads.filter(l => l.status === 'sent').length}</p>
                </div>
            </div>

            {/* Main Table */}
            {isLoading ? (
                <div className="space-y-4">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-16 bg-zinc-900 animate-pulse rounded-xl border border-zinc-800" />
                    ))}
                </div>
            ) : (
                <LeadTable
                    leads={leads}
                    selectedIds={selectedIds}
                    enrichingIds={enrichingIds}
                    onToggleSelect={handleToggleSelect}
                    onSelectAll={handleSelectAll}
                />
            )}
        </div>
    )
}
