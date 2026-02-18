import { useState } from 'react'
import { Send, FileText, CheckCircle, AlertCircle, RefreshCw, ChevronDown, ChevronUp, Loader2, Shield, CheckSquare, Square } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import clsx from 'clsx'

export default function Outbox() {
    const [sendMode, setSendMode] = useState('drafts') // 'drafts' | 'immediate'
    const [confirmed, setConfirmed] = useState(false)
    const [expandedLeadId, setExpandedLeadId] = useState(null)
    const [progress, setProgress] = useState({ current: 0, total: 0, status: 'idle' })
    const [notification, setNotification] = useState(null)
    const [selectedIds, setSelectedIds] = useState(new Set())
    const [initialized, setInitialized] = useState(false)

    const queryClient = useQueryClient()

    // Fetch leads ready to send
    const { data: leads = [], isLoading } = useQuery({
        queryKey: ['leads'],
        queryFn: async () => (await axios.get('/api/leads')).data
    })

    // Filter to leads with email content ready
    const readyLeads = leads.filter(l => l.email && l.email_body && l.status !== 'sent')

    // Auto-select current-session leads on first load, fall back to all
    if (!initialized && readyLeads.length > 0) {
        const stored = sessionStorage.getItem('currentSearchIds')
        if (stored) {
            try {
                const ids = JSON.parse(stored)
                const currentReady = readyLeads.filter(l => ids.includes(l.id))
                if (currentReady.length > 0) {
                    setSelectedIds(new Set(currentReady.map(l => l.id)))
                } else {
                    setSelectedIds(new Set(readyLeads.map(l => l.id)))
                }
            } catch {
                setSelectedIds(new Set(readyLeads.map(l => l.id)))
            }
        } else {
            setSelectedIds(new Set(readyLeads.map(l => l.id)))
        }
        setInitialized(true)
    }

    const selectedLeads = readyLeads.filter(l => selectedIds.has(l.id))

    const toggleLead = (id) => {
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
        setConfirmed(false)
    }

    const toggleAll = () => {
        if (selectedIds.size === readyLeads.length) {
            setSelectedIds(new Set())
        } else {
            setSelectedIds(new Set(readyLeads.map(l => l.id)))
        }
        setConfirmed(false)
    }

    // Check Gmail connection
    const { data: gmailStatus } = useQuery({
        queryKey: ['gmail-status'],
        queryFn: async () => {
            try {
                const res = await axios.get('/api/gmail/status')
                return res.data
            } catch {
                return { connected: false }
            }
        },
        retry: false
    })

    // Check OAuth status (needed to know if drafts are possible)
    const { data: oauthStatus } = useQuery({
        queryKey: ['gmail-oauth-status'],
        queryFn: async () => {
            try {
                const res = await axios.get('/api/gmail/oauth-status')
                return res.data
            } catch {
                return { status: 'needs_setup' }
            }
        },
        retry: false
    })

    const isOAuthConnected = oauthStatus?.status === 'connected'
    const isSMTPOnly = gmailStatus?.connected && !isOAuthConnected

    // Auto-switch to immediate mode if drafts aren't available
    if (sendMode === 'drafts' && isSMTPOnly) {
        setSendMode('immediate')
    }

    // Send/Draft mutation
    const sendMutation = useMutation({
        mutationFn: async () => {
            const ids = selectedLeads.map(l => l.id)
            if (sendMode === 'drafts') {
                return axios.post('/api/email/create-drafts', { lead_ids: ids })
            } else {
                return axios.post('/api/email/send-batch', { lead_ids: ids })
            }
        },
        onMutate: () => {
            setProgress({ current: 0, total: selectedLeads.length, status: 'sending' })
        },
        onSuccess: (response) => {
            const count = response.data?.sent || response.data?.created || 0
            const errors = response.data?.errors || []
            setProgress({ current: count, total: count, status: 'complete' })
            setConfirmed(false)
            queryClient.invalidateQueries(['leads'])

            if (count === 0 && errors.length > 0) {
                const firstError = errors[0]?.error || 'Unknown error'
                showNotification('error', `Failed: ${firstError}`)
            } else if (errors.length > 0) {
                showNotification('success',
                    sendMode === 'drafts'
                        ? `Created ${count} drafts (${errors.length} failed)`
                        : `Sent ${count} emails (${errors.length} failed)`
                )
            } else {
                showNotification('success',
                    sendMode === 'drafts'
                        ? `Created ${count} drafts in Gmail!`
                        : `Sent ${count} emails successfully!`
                )
            }
        },
        onError: (error) => {
            setProgress({ current: 0, total: 0, status: 'error' })
            showNotification('error', error.response?.data?.detail || 'Failed to send emails')
        }
    })

    const showNotification = (type, message) => {
        setNotification({ type, message })
        setTimeout(() => setNotification(null), 5000)
    }

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
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

            <header>
                <h2 className="text-3xl font-bold tracking-tight">Outbox</h2>
                <p className="text-zinc-400">Review and send emails to your leads.</p>
            </header>

            {/* Gmail Connection Status */}
            <div className={clsx(
                "flex items-center gap-3 p-4 rounded-xl border",
                gmailStatus?.connected
                    ? isSMTPOnly
                        ? "bg-yellow-500/10 border-yellow-500/20 text-yellow-400"
                        : "bg-green-500/10 border-green-500/20 text-green-400"
                    : "bg-red-500/10 border-red-500/20 text-red-400"
            )}>
                {gmailStatus?.connected ? (
                    isSMTPOnly ? (
                        <>
                            <AlertCircle size={20} />
                            <div>
                                <span className="font-medium">Gmail Connected (SMTP Only)</span>
                                <p className="text-sm opacity-70">"Send Immediately" works. For drafts, connect OAuth in Settings.</p>
                            </div>
                        </>
                    ) : (
                        <>
                            <CheckCircle size={20} />
                            <div>
                                <span className="font-medium">Gmail Connected (OAuth)</span>
                                <p className="text-sm opacity-70">Both drafts and direct sending are available.</p>
                            </div>
                        </>
                    )
                ) : (
                    <>
                        <AlertCircle size={20} />
                        <div>
                            <span className="font-medium">Gmail Not Connected</span>
                            <p className="text-sm opacity-70">Configure Gmail in Settings to send emails.</p>
                        </div>
                    </>
                )}
            </div>

            {/* Stats */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 flex items-center justify-between">
                <div>
                    <p className="text-4xl font-bold">{selectedLeads.length}<span className="text-lg text-zinc-500"> / {readyLeads.length}</span></p>
                    <p className="text-zinc-500">emails selected to send</p>
                </div>
                {readyLeads.length > 0 && (
                    <button
                        onClick={toggleAll}
                        className="px-4 py-2 text-sm border border-zinc-700 rounded-lg hover:bg-zinc-800 transition-colors flex items-center gap-2 text-zinc-300"
                    >
                        {selectedIds.size === readyLeads.length
                            ? <><CheckSquare size={16} /> Deselect All</>
                            : <><Square size={16} /> Select All</>}
                    </button>
                )}
            </div>

            {readyLeads.length === 0 ? (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
                    <Send size={48} className="mx-auto text-zinc-700 mb-4" />
                    <p className="text-zinc-400">No emails ready to send.</p>
                    <p className="text-sm text-zinc-600">Generate emails in Email Studio first.</p>
                </div>
            ) : (
                <>
                    {/* Review Section */}
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                        <div className="p-4 border-b border-zinc-800 bg-zinc-800/50">
                            <h3 className="font-semibold">Review Before Sending</h3>
                        </div>
                        <div className="divide-y divide-zinc-800">
                            {readyLeads.map(lead => (
                                <div key={lead.id} className={clsx("overflow-hidden", !selectedIds.has(lead.id) && "opacity-40")}>
                                    <div className="flex items-center">
                                        <button
                                            onClick={() => toggleLead(lead.id)}
                                            className="p-4 hover:bg-zinc-800/50 transition-colors flex-shrink-0"
                                        >
                                            {selectedIds.has(lead.id)
                                                ? <CheckSquare size={18} className="text-blue-400" />
                                                : <Square size={18} className="text-zinc-600" />}
                                        </button>
                                        <button
                                            onClick={() => setExpandedLeadId(expandedLeadId === lead.id ? null : lead.id)}
                                            className="flex-1 p-4 pl-0 flex items-center justify-between hover:bg-zinc-800/50 transition-colors"
                                        >
                                            <div className="text-left">
                                                <p className="font-medium text-white">{lead.business_name}</p>
                                                <p className="text-sm text-zinc-500">→ {lead.email}</p>
                                            </div>
                                            {expandedLeadId === lead.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                                        </button>
                                    </div>
                                    <AnimatePresence>
                                        {expandedLeadId === lead.id && (
                                            <motion.div
                                                initial={{ height: 0, opacity: 0 }}
                                                animate={{ height: 'auto', opacity: 1 }}
                                                exit={{ height: 0, opacity: 0 }}
                                                className="overflow-hidden"
                                            >
                                                <div className="p-4 bg-zinc-800/30 border-t border-zinc-700/50 space-y-2">
                                                    <p className="text-sm"><strong className="text-zinc-400">Subject:</strong> {lead.email_subject}</p>
                                                    <div>
                                                        <strong className="text-zinc-400 text-sm">Body:</strong>
                                                        <pre className="mt-2 text-sm text-zinc-300 whitespace-pre-wrap bg-zinc-900 p-3 rounded-lg">
                                                            {lead.email_body}
                                                        </pre>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Send Options */}
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-6">
                        <h3 className="font-semibold text-lg">Send Options</h3>

                        {/* Mode Toggle */}
                        <div className="space-y-3">
                            <label className="text-sm font-medium text-zinc-400">Send Mode</label>
                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    onClick={() => isOAuthConnected ? setSendMode('drafts') : null}
                                    className={clsx(
                                        "p-4 rounded-xl border text-left transition-all relative",
                                        !isOAuthConnected && "opacity-50 cursor-not-allowed",
                                        sendMode === 'drafts' && isOAuthConnected
                                            ? "bg-blue-500/10 border-blue-500/30"
                                            : "border-zinc-700 hover:border-zinc-600"
                                    )}
                                >
                                    <div className="flex items-center gap-3">
                                        <FileText size={20} className={sendMode === 'drafts' ? "text-blue-400" : "text-zinc-500"} />
                                        <div>
                                            <p className={clsx("font-medium", sendMode === 'drafts' ? "text-blue-400" : "text-white")}>
                                                Create Drafts Only
                                            </p>
                                            <p className="text-xs text-zinc-500">
                                                {isOAuthConnected ? "Review in Gmail before sending" : "Requires OAuth — connect in Settings"}
                                            </p>
                                        </div>
                                    </div>
                                </button>
                                <button
                                    onClick={() => setSendMode('immediate')}
                                    className={clsx(
                                        "p-4 rounded-xl border text-left transition-all",
                                        sendMode === 'immediate'
                                            ? "bg-orange-500/10 border-orange-500/30"
                                            : "border-zinc-700 hover:border-zinc-600"
                                    )}
                                >
                                    <div className="flex items-center gap-3">
                                        <Send size={20} className={sendMode === 'immediate' ? "text-orange-400" : "text-zinc-500"} />
                                        <div>
                                            <p className={clsx("font-medium", sendMode === 'immediate' ? "text-orange-400" : "text-white")}>
                                                Send Immediately
                                            </p>
                                            <p className="text-xs text-zinc-500">Emails sent right away</p>
                                        </div>
                                    </div>
                                </button>
                            </div>
                        </div>

                        {/* Confirmation */}
                        <div className={clsx(
                            "p-4 rounded-xl border",
                            sendMode === 'immediate' ? "bg-orange-500/10 border-orange-500/20" : "bg-blue-500/10 border-blue-500/20"
                        )}>
                            <div className="flex items-start gap-3">
                                <Shield size={20} className={sendMode === 'immediate' ? "text-orange-400" : "text-blue-400"} />
                                <div className="flex-1">
                                    <p className={sendMode === 'immediate' ? "text-orange-400" : "text-blue-400"}>
                                        {sendMode === 'drafts'
                                            ? `You are about to create ${selectedLeads.length} draft${selectedLeads.length !== 1 ? 's' : ''} in your Gmail account.`
                                            : `You are about to send ${selectedLeads.length} email${selectedLeads.length !== 1 ? 's' : ''} immediately!`}
                                    </p>
                                    <label className="flex items-center gap-3 mt-3 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={confirmed}
                                            onChange={e => setConfirmed(e.target.checked)}
                                            className="rounded border-zinc-600 bg-zinc-700"
                                        />
                                        <span className="text-sm text-zinc-300">
                                            I confirm I want to {sendMode === 'drafts' ? 'create drafts' : 'send emails'} for {selectedLeads.length} selected lead{selectedLeads.length !== 1 ? 's' : ''}
                                        </span>
                                    </label>
                                </div>
                            </div>
                        </div>

                        {/* Action Button */}
                        <button
                            onClick={() => sendMutation.mutate()}
                            disabled={!confirmed || sendMutation.isPending || !gmailStatus?.connected || selectedLeads.length === 0}
                            className={clsx(
                                "w-full h-14 rounded-xl font-semibold flex items-center justify-center gap-3 transition-all text-lg",
                                !confirmed || !gmailStatus?.connected || selectedLeads.length === 0
                                    ? "bg-zinc-700 text-zinc-500 cursor-not-allowed"
                                    : sendMode === 'drafts'
                                        ? "bg-blue-500 text-white hover:bg-blue-600"
                                        : "bg-orange-500 text-white hover:bg-orange-600"
                            )}
                        >
                            {sendMutation.isPending ? (
                                <><Loader2 className="animate-spin" size={20} /> Processing...</>
                            ) : sendMode === 'drafts' ? (
                                <><FileText size={20} /> Create {selectedLeads.length} Draft{selectedLeads.length !== 1 ? 's' : ''}</>
                            ) : (
                                <><Send size={20} /> Send {selectedLeads.length} Email{selectedLeads.length !== 1 ? 's' : ''}</>
                            )}
                        </button>
                    </div>

                    {/* Results */}
                    <AnimatePresence>
                        {progress.status === 'complete' && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="bg-green-500/10 border border-green-500/20 rounded-xl p-6 text-center"
                            >
                                <CheckCircle size={48} className="mx-auto text-green-500 mb-4" />
                                <h3 className="text-xl font-bold text-white">
                                    {sendMode === 'drafts' ? 'Drafts Created!' : 'Emails Sent!'}
                                </h3>
                                <p className="text-zinc-400">
                                    {sendMode === 'drafts'
                                        ? 'Open Gmail to review and send your drafts.'
                                        : `Successfully sent ${progress.total} emails.`}
                                </p>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </>
            )}
        </div>
    )
}
