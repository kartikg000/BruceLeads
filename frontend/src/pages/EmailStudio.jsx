import { useState, useMemo } from 'react'
import { Mail, Sparkles, Send, Save, RefreshCw, CheckCircle, AlertCircle, Copy, Users, Zap, ChevronRight, Filter, Settings2, Loader2 } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import clsx from 'clsx'

export default function EmailStudio() {
    const [selectedLeadIds, setSelectedLeadIds] = useState([])
    const [mode, setMode] = useState('single') // 'single' or 'batch'
    const [scope, setScope] = useState('current') // 'current' or 'all'
    const [framework, setFramework] = useState('AIDA')
    const [instructions, setInstructions] = useState('')
    const [editedSubject, setEditedSubject] = useState('')
    const [editedBody, setEditedBody] = useState('')
    const [notification, setNotification] = useState(null)
    const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0, status: 'idle' })
    const [showSettings, setShowSettings] = useState(false)

    // AI customization params
    const [senderName, setSenderName] = useState('')
    const [serviceDescription, setServiceDescription] = useState('')
    const [tone, setTone] = useState('')
    const [temperature, setTemperature] = useState(0.8)
    const [maxWords, setMaxWords] = useState(120)

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
    const { data: allLeads = [] } = useQuery({
        queryKey: ['leads'],
        queryFn: async () => (await axios.get('/api/leads')).data
    })

    // Filter for leads with email based on scope
    const emailableLeads = useMemo(() => {
        let filtered = allLeads.filter(l => l.email && l.status !== 'sent')
        if (scope === 'current' && currentSearchIds.length > 0) {
            filtered = filtered.filter(l => currentSearchIds.includes(l.id))
        }
        return filtered
    }, [allLeads, scope, currentSearchIds])

    const selectedLead = mode === 'single' ? allLeads.find(l => l.id === selectedLeadIds[0]) : null

    // Handle lead selection
    const handleSelectLead = (id) => {
        if (mode === 'single') {
            setSelectedLeadIds([id])
            const lead = allLeads.find(l => l.id === id)
            if (lead) {
                setEditedSubject(lead.email_subject || '')
                setEditedBody(lead.email_body || '')
            }
        } else {
            if (selectedLeadIds.includes(id)) {
                setSelectedLeadIds(selectedLeadIds.filter(lid => lid !== id))
            } else {
                setSelectedLeadIds([...selectedLeadIds, id])
            }
        }
    }

    const handleSelectAll = () => {
        if (selectedLeadIds.length === emailableLeads.length) {
            setSelectedLeadIds([])
        } else {
            setSelectedLeadIds(emailableLeads.map(l => l.id))
        }
    }

    // Generate Mutation (works for both single and batch)
    const generateMutation = useMutation({
        mutationFn: async () => {
            const payload = {
                lead_ids: selectedLeadIds,
                framework,
                custom_instructions: instructions || undefined,
                sender_name: senderName || undefined,
                service_description: serviceDescription || undefined,
                tone: tone || undefined,
                temperature,
                max_words: maxWords,
            }
            return axios.post('/api/email/generate', payload)
        },
        onMutate: () => {
            if (mode === 'batch') {
                setBatchProgress({ current: 0, total: selectedLeadIds.length, status: 'generating' })
            }
        },
        onSuccess: (response) => {
            queryClient.invalidateQueries(['leads'])
            if (mode === 'single' && response.data?.generated?.[0]) {
                const generated = response.data.generated[0]
                setEditedSubject(generated.subject || '')
                setEditedBody(generated.body || '')
            }
            setBatchProgress({ current: 0, total: 0, status: 'idle' })
            showNotification('success', `Generated ${response.data?.generated?.length || 0} email(s)!`)
        },
        onError: () => {
            setBatchProgress({ current: 0, total: 0, status: 'idle' })
            showNotification('error', 'Failed to generate emails. Check your API key.')
        }
    })

    // Save Mutation (single mode only)
    const saveMutation = useMutation({
        mutationFn: async () => {
            return axios.post('/api/email/save', {
                lead_id: selectedLeadIds[0],
                subject: editedSubject,
                body: editedBody
            })
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['leads'])
            showNotification('success', 'Draft saved!')
        }
    })

    // Send Mutation (works for both single and batch)
    const sendMutation = useMutation({
        mutationFn: async () => {
            if (mode === 'single') {
                return axios.post('/api/email/send', {
                    lead_id: selectedLeadIds[0],
                    subject: editedSubject,
                    body: editedBody
                })
            } else {
                return axios.post('/api/email/send-batch', {
                    lead_ids: selectedLeadIds
                })
            }
        },
        onMutate: () => {
            if (mode === 'batch') {
                setBatchProgress({ current: 0, total: selectedLeadIds.length, status: 'sending' })
            }
        },
        onSuccess: (response) => {
            queryClient.invalidateQueries(['leads'])
            setBatchProgress({ current: 0, total: 0, status: 'idle' })
            const count = mode === 'batch' ? response.data?.sent : 1
            showNotification('success', `Sent ${count} email(s) successfully!`)
            setSelectedLeadIds([])
        },
        onError: () => {
            setBatchProgress({ current: 0, total: 0, status: 'idle' })
            showNotification('error', 'Failed to send email(s). Check Gmail configuration.')
        }
    })

    const showNotification = (type, message) => {
        setNotification({ type, message })
        setTimeout(() => setNotification(null), 4000)
    }

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text)
        showNotification('success', 'Copied to clipboard!')
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

            {/* Header with Mode and Scope */}
            <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Email Studio</h2>
                    <p className="text-zinc-400">Compose and send personalized emails to your leads.</p>
                </div>

                <div className="flex gap-2">
                    {/* Scope Filter */}
                    {currentSearchIds.length > 0 && (
                        <div className="flex gap-1 bg-zinc-900 border border-zinc-800 p-1 rounded-xl">
                            <button
                                onClick={() => setScope('current')}
                                className={clsx(
                                    "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                                    scope === 'current' ? "bg-blue-500 text-white" : "text-zinc-400 hover:text-white"
                                )}
                            >
                                Current ({currentSearchIds.length})
                            </button>
                            <button
                                onClick={() => setScope('all')}
                                className={clsx(
                                    "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                                    scope === 'all' ? "bg-blue-500 text-white" : "text-zinc-400 hover:text-white"
                                )}
                            >
                                All
                            </button>
                        </div>
                    )}

                    {/* Mode Toggle */}
                    <div className="flex gap-1 bg-zinc-900 border border-zinc-800 p-1 rounded-xl">
                        <button
                            onClick={() => { setMode('single'); setSelectedLeadIds([]); }}
                            className={clsx(
                                "px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all",
                                mode === 'single' ? "bg-white text-black" : "text-zinc-400 hover:text-white"
                            )}
                        >
                            <Users size={14} /> Single
                        </button>
                        <button
                            onClick={() => { setMode('batch'); setSelectedLeadIds([]); }}
                            className={clsx(
                                "px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all",
                                mode === 'batch' ? "bg-purple-500 text-white" : "text-zinc-400 hover:text-white"
                            )}
                        >
                            <Zap size={14} /> Batch
                        </button>
                    </div>
                </div>
            </header>

            {/* Batch Progress */}
            <AnimatePresence>
                {batchProgress.status !== 'idle' && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="bg-zinc-900 border border-zinc-800 rounded-xl p-6"
                    >
                        <div className="flex items-center gap-4">
                            <RefreshCw size={24} className="animate-spin text-purple-400" />
                            <div className="flex-1">
                                <p className="font-medium text-white">
                                    {batchProgress.status === 'generating' ? 'Generating emails...' : 'Sending emails...'}
                                </p>
                                <p className="text-sm text-zinc-500">Processing {batchProgress.total} leads</p>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className="flex h-[calc(100vh-16rem)] gap-6">
                {/* LEFT: Lead List */}
                <div className="w-1/3 flex flex-col bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                    <div className="p-4 border-b border-zinc-800 bg-zinc-800/50 flex items-center justify-between">
                        <h3 className="font-semibold flex items-center gap-2">
                            <Mail size={18} /> Ready ({emailableLeads.length})
                        </h3>
                        {mode === 'batch' && emailableLeads.length > 0 && (
                            <button
                                onClick={handleSelectAll}
                                className="text-xs text-blue-400 hover:text-blue-300"
                            >
                                {selectedLeadIds.length === emailableLeads.length ? 'Deselect All' : 'Select All'}
                            </button>
                        )}
                    </div>
                    <div className="flex-1 overflow-y-auto p-2 space-y-1">
                        {emailableLeads.length === 0 ? (
                            <div className="text-center p-8 text-zinc-500">
                                <Mail size={32} className="mx-auto mb-2 opacity-30" />
                                <p className="text-sm">No leads ready for email.</p>
                                <p className="text-xs text-zinc-600">Enrich leads first to find their email addresses.</p>
                            </div>
                        ) : (
                            emailableLeads.map(lead => (
                                <button
                                    key={lead.id}
                                    onClick={() => handleSelectLead(lead.id)}
                                    className={clsx(
                                        "w-full text-left p-3 rounded-lg border transition-all text-sm flex items-center gap-3",
                                        selectedLeadIds.includes(lead.id)
                                            ? "bg-zinc-800 border-zinc-700 text-white"
                                            : "border-transparent hover:bg-zinc-800/50 text-zinc-400"
                                    )}
                                >
                                    {mode === 'batch' && (
                                        <div className={clsx(
                                            "w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 transition-colors",
                                            selectedLeadIds.includes(lead.id)
                                                ? "bg-purple-500 border-purple-500"
                                                : "border-zinc-600"
                                        )}>
                                            {selectedLeadIds.includes(lead.id) && <CheckCircle size={14} />}
                                        </div>
                                    )}
                                    <div className="flex-1 min-w-0">
                                        <div className="font-medium truncate">{lead.business_name}</div>
                                        <div className="flex items-center justify-between mt-1">
                                            <span className="text-xs opacity-70 truncate">{lead.email}</span>
                                            {lead.email_body && <Sparkles size={12} className="text-purple-400 flex-shrink-0" />}
                                        </div>
                                    </div>
                                    {mode === 'single' && selectedLeadIds.includes(lead.id) && (
                                        <ChevronRight size={16} className="text-zinc-500" />
                                    )}
                                </button>
                            ))
                        )}
                    </div>

                    {/* Batch Actions Footer */}
                    {mode === 'batch' && selectedLeadIds.length > 0 && (
                        <div className="p-4 border-t border-zinc-800 bg-zinc-800/50 space-y-3">
                            <p className="text-sm text-zinc-400">{selectedLeadIds.length} leads selected</p>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => generateMutation.mutate()}
                                    disabled={generateMutation.isPending}
                                    className="flex-1 py-2 bg-purple-500/20 text-purple-400 rounded-lg text-sm font-medium hover:bg-purple-500/30 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    {generateMutation.isPending ? <RefreshCw size={16} className="animate-spin" /> : <Sparkles size={16} />}
                                    Generate All
                                </button>
                                <button
                                    onClick={() => sendMutation.mutate()}
                                    disabled={sendMutation.isPending}
                                    className="flex-1 py-2 bg-white text-black rounded-lg text-sm font-medium hover:bg-zinc-200 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    {sendMutation.isPending ? <RefreshCw size={16} className="animate-spin" /> : <Send size={16} />}
                                    Send All
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* RIGHT: Editor (Single Mode Only) */}
                <div className="w-2/3 flex flex-col bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                    {mode === 'single' && selectedLead ? (
                        <>
                            {/* Toolbar */}
                            <div className="p-4 border-b border-zinc-800 bg-zinc-800/50 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <select
                                        value={framework}
                                        onChange={e => setFramework(e.target.value)}
                                        className="bg-zinc-700 border-zinc-600 rounded-lg text-sm px-3 py-1.5 focus:ring-blue-500"
                                    >
                                        <option value="AIDA">AIDA Framework</option>
                                        <option value="PAS">PAS Framework</option>
                                    </select>
                                    <div className="h-4 w-px bg-zinc-700" />
                                    <button
                                        onClick={() => setShowSettings(!showSettings)}
                                        className={clsx(
                                            "flex items-center gap-2 text-sm px-3 py-1.5 rounded-lg transition-colors",
                                            showSettings
                                                ? "bg-blue-500/20 text-blue-400"
                                                : "text-zinc-400 hover:text-white hover:bg-zinc-700"
                                        )}
                                    >
                                        <Settings2 size={16} /> AI Settings
                                    </button>
                                    <div className="h-4 w-px bg-zinc-700" />
                                    <button
                                        onClick={() => generateMutation.mutate()}
                                        disabled={generateMutation.isPending}
                                        className="flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300 transition-colors px-3 py-1.5 rounded-lg hover:bg-purple-500/10 disabled:opacity-50"
                                    >
                                        {generateMutation.isPending ? (
                                            <><Loader2 className="animate-spin" size={16} /> Generating...</>
                                        ) : (
                                            <><Sparkles size={16} /> {editedBody ? 'Regenerate' : 'Generate'}</>
                                        )}
                                    </button>
                                </div>

                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => saveMutation.mutate()}
                                        disabled={saveMutation.isPending || !editedBody}
                                        className="px-4 py-1.5 bg-zinc-700 text-white text-sm font-medium rounded-lg hover:bg-zinc-600 transition-colors flex items-center gap-2 disabled:opacity-50"
                                    >
                                        {saveMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Save
                                    </button>
                                    <button
                                        onClick={() => sendMutation.mutate()}
                                        disabled={sendMutation.isPending || !editedBody || !selectedLead.email}
                                        className="px-4 py-1.5 bg-white text-black text-sm font-medium rounded-lg hover:bg-zinc-200 transition-colors flex items-center gap-2 disabled:opacity-50"
                                    >
                                        {sendMutation.isPending ? (
                                            <><Loader2 className="animate-spin" size={16} /> Sending...</>
                                        ) : (
                                            <><Send size={16} /> Send</>
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* AI Settings Panel (collapsible) */}
                            <AnimatePresence>
                                {showSettings && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: 'auto', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        className="overflow-hidden border-b border-zinc-800"
                                    >
                                        <div className="p-4 bg-zinc-800/30 space-y-4">
                                            <div className="grid grid-cols-2 gap-4">
                                                <div className="space-y-1">
                                                    <label className="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Your Name</label>
                                                    <input
                                                        type="text"
                                                        value={senderName}
                                                        onChange={e => setSenderName(e.target.value)}
                                                        placeholder="e.g. Kartik Gupta"
                                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
                                                    />
                                                </div>
                                                <div className="space-y-1">
                                                    <label className="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Tone</label>
                                                    <select
                                                        value={tone}
                                                        onChange={e => setTone(e.target.value)}
                                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:ring-blue-500"
                                                    >
                                                        <option value="">Default (Professional)</option>
                                                        <option value="professional and friendly">Professional & Friendly</option>
                                                        <option value="casual and witty">Casual & Witty</option>
                                                        <option value="formal and authoritative">Formal & Authoritative</option>
                                                        <option value="warm and empathetic">Warm & Empathetic</option>
                                                        <option value="bold and direct">Bold & Direct</option>
                                                    </select>
                                                </div>
                                            </div>
                                            <div className="space-y-1">
                                                <label className="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Your Service / Offer</label>
                                                <textarea
                                                    value={serviceDescription}
                                                    onChange={e => setServiceDescription(e.target.value)}
                                                    placeholder="Describe what you offer, e.g. 'We build high-converting websites for local businesses...'"
                                                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm h-16 resize-none focus:ring-blue-500 focus:border-blue-500"
                                                />
                                            </div>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div className="space-y-1">
                                                    <label className="text-xs uppercase tracking-wider text-zinc-500 font-semibold">
                                                        Creativity ({temperature.toFixed(1)})
                                                    </label>
                                                    <input
                                                        type="range"
                                                        min="0"
                                                        max="1"
                                                        step="0.1"
                                                        value={temperature}
                                                        onChange={e => setTemperature(parseFloat(e.target.value))}
                                                        className="w-full accent-purple-500"
                                                    />
                                                    <div className="flex justify-between text-xs text-zinc-600">
                                                        <span>Focused</span>
                                                        <span>Creative</span>
                                                    </div>
                                                </div>
                                                <div className="space-y-1">
                                                    <label className="text-xs uppercase tracking-wider text-zinc-500 font-semibold">
                                                        Max Words ({maxWords})
                                                    </label>
                                                    <input
                                                        type="range"
                                                        min="50"
                                                        max="300"
                                                        step="10"
                                                        value={maxWords}
                                                        onChange={e => setMaxWords(parseInt(e.target.value))}
                                                        className="w-full accent-purple-500"
                                                    />
                                                    <div className="flex justify-between text-xs text-zinc-600">
                                                        <span>Short</span>
                                                        <span>Long</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="space-y-1">
                                                <label className="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Custom Instructions</label>
                                                <textarea
                                                    value={instructions}
                                                    onChange={e => setInstructions(e.target.value)}
                                                    placeholder="e.g. 'Mention that we are a local business', 'Include a case study reference', 'Add urgency about limited slots'..."
                                                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm h-16 resize-none focus:ring-blue-500 focus:border-blue-500"
                                                />
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Content Area */}
                            <div className="flex-1 p-6 overflow-y-auto space-y-6">
                                {/* Recipient Info */}
                                <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Sending to</p>
                                            <p className="font-medium text-white">{selectedLead.business_name}</p>
                                            <p className="text-sm text-zinc-400">{selectedLead.email}</p>
                                        </div>
                                        <button
                                            onClick={() => copyToClipboard(selectedLead.email)}
                                            className="p-2 hover:bg-zinc-700 rounded-lg transition-colors"
                                            title="Copy email"
                                        >
                                            <Copy size={16} className="text-zinc-400" />
                                        </button>
                                    </div>
                                </div>

                                {editedBody || generateMutation.isPending ? (
                                    <div className="space-y-4">
                                        <div className="space-y-2">
                                            <label className="text-xs uppercase tracking-wider text-zinc-400 font-semibold">Subject</label>
                                            <input
                                                type="text"
                                                value={editedSubject}
                                                onChange={e => setEditedSubject(e.target.value)}
                                                placeholder="Email subject..."
                                                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 focus:ring-blue-500 focus:border-blue-500"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <div className="flex items-center justify-between">
                                                <label className="text-xs uppercase tracking-wider text-zinc-400 font-semibold">Body</label>
                                                <span className="text-xs text-zinc-500">{editedBody.split(/\s+/).filter(Boolean).length} words &middot; {editedBody.length} chars</span>
                                            </div>
                                            <textarea
                                                value={editedBody}
                                                onChange={e => setEditedBody(e.target.value)}
                                                placeholder="Email body..."
                                                className="w-full h-64 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-4 focus:ring-blue-500 focus:border-blue-500 text-sm leading-relaxed resize-y"
                                            />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center justify-center h-full text-zinc-500 gap-4 py-12">
                                        <Sparkles size={48} className="text-zinc-700" />
                                        <div className="text-center">
                                            <p className="text-lg font-medium text-white">No draft generated</p>
                                            <p className="text-sm">Open <strong>AI Settings</strong> to customize, then click <strong>Generate</strong>.</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </>
                    ) : mode === 'batch' ? (
                        <div className="flex flex-col items-center justify-center h-full text-zinc-500 gap-4 p-8">
                            <Zap size={48} className="text-purple-400/30" />
                            <div className="text-center">
                                <p className="text-lg font-medium text-white">Batch Mode Active</p>
                                <p className="text-sm">Select leads from the list, then use Generate All or Send All.</p>
                            </div>
                            <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-4 w-full max-w-md space-y-3">
                                <div>
                                    <label className="text-xs uppercase tracking-wider text-zinc-400 font-semibold block mb-2">Framework</label>
                                    <select
                                        value={framework}
                                        onChange={e => setFramework(e.target.value)}
                                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg text-sm px-3 py-2"
                                    >
                                        <option value="AIDA">AIDA Framework</option>
                                        <option value="PAS">PAS Framework</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs uppercase tracking-wider text-zinc-400 font-semibold block mb-2">Your Name</label>
                                    <input
                                        type="text"
                                        value={senderName}
                                        onChange={e => setSenderName(e.target.value)}
                                        placeholder="e.g. Kartik Gupta"
                                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg text-sm px-3 py-2"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs uppercase tracking-wider text-zinc-400 font-semibold block mb-2">Your Service / Offer</label>
                                    <textarea
                                        value={serviceDescription}
                                        onChange={e => setServiceDescription(e.target.value)}
                                        placeholder="Describe what you offer..."
                                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm h-16 resize-none"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs uppercase tracking-wider text-zinc-400 font-semibold block mb-2">Tone</label>
                                    <select
                                        value={tone}
                                        onChange={e => setTone(e.target.value)}
                                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg text-sm px-3 py-2"
                                    >
                                        <option value="">Default (Professional)</option>
                                        <option value="professional and friendly">Professional & Friendly</option>
                                        <option value="casual and witty">Casual & Witty</option>
                                        <option value="formal and authoritative">Formal & Authoritative</option>
                                        <option value="warm and empathetic">Warm & Empathetic</option>
                                        <option value="bold and direct">Bold & Direct</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs uppercase tracking-wider text-zinc-400 font-semibold block mb-2">Custom Instructions</label>
                                    <textarea
                                        placeholder="e.g. 'Mention we are a local business'"
                                        value={instructions}
                                        onChange={e => setInstructions(e.target.value)}
                                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm h-20 resize-none"
                                    />
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                            <Mail size={48} className="opacity-20 mb-4" />
                            <p>Select a lead to compose an email</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
