import { useState, useEffect } from 'react'
import { Trash2, RefreshCw, CheckCircle, AlertCircle, Mail, Key, Database, Loader2, Unlink, Zap, Save, Eye, EyeOff, Cpu, Thermometer, FileText, Upload, Info, Download } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import clsx from 'clsx'

export default function Settings() {
    const [notification, setNotification] = useState(null)
    const [connecting, setConnecting] = useState(false)
    const [disconnecting, setDisconnecting] = useState(false)
    const queryClient = useQueryClient()

    // Editable settings state
    const [geminiKey, setGeminiKey] = useState('')
    const [showGeminiKey, setShowGeminiKey] = useState(false)
    const [concurrency, setConcurrency] = useState(3)
    const [temperature, setTemperature] = useState(0.7)
    const [maxWords, setMaxWords] = useState(150)
    const [scrapingDelay, setScrapingDelay] = useState(2.0)
    const [savingKeys, setSavingKeys] = useState(false)
    const [savingSettings, setSavingSettings] = useState(false)
    const [uploadingOAuth, setUploadingOAuth] = useState(false)
    const [checkingUpdate, setCheckingUpdate] = useState(false)
    const [applyingUpdate, setApplyingUpdate] = useState(false)
    const [updateInfo, setUpdateInfo] = useState(null)
    const [appVersion, setAppVersion] = useState(null)

    // Fetch settings from setup API
    const { data: setupSettings, refetch: refetchSettings } = useQuery({
        queryKey: ['setup-settings'],
        queryFn: async () => {
            try {
                const res = await axios.get('/api/setup/settings')
                return res.data
            } catch {
                return null
            }
        }
    })

    // Populate form from fetched settings
    useEffect(() => {
        if (setupSettings?.settings) {
            const s = setupSettings.settings
            setGeminiKey(s.gemini_api_key || '')
            setConcurrency(s.max_concurrent_browsers || 3)
            setTemperature(s.gemini_temperature ?? 0.7)
            setMaxWords(s.max_email_words || 150)
            setScrapingDelay(s.scrape_min_delay ?? 2.0)
        }
    }, [setupSettings])

    // Fetch Gmail OAuth status
    const { data: oauthStatus, refetch: refetchOAuth } = useQuery({
        queryKey: ['gmail-oauth-status'],
        queryFn: async () => {
            try {
                const res = await axios.get('/api/gmail/oauth-status')
                return res.data
            } catch {
                return { status: 'needs_setup' }
            }
        }
    })

    // Fetch Gmail simple status
    const { data: gmailStatus, refetch: refetchGmail } = useQuery({
        queryKey: ['gmail-status'],
        queryFn: async () => {
            try {
                const res = await axios.get('/api/gmail/status')
                return res.data
            } catch {
                return { connected: false, message: 'Could not reach backend' }
            }
        }
    })

    // Fetch stats
    const { data: stats } = useQuery({
        queryKey: ['stats'],
        queryFn: async () => {
            try {
                const res = await axios.get('/stats')
                return res.data
            } catch {
                return {}
            }
        }
    })

    // Delete all leads mutation
    const deleteAllMutation = useMutation({
        mutationFn: async () => axios.post('/api/leads/clear'),
        onSuccess: () => {
            queryClient.invalidateQueries(['leads', 'stats'])
            showNotification('success', 'All leads deleted successfully')
        },
        onError: () => showNotification('error', 'Failed to delete leads')
    })

    const showNotification = (type, message) => {
        setNotification({ type, message })
        setTimeout(() => setNotification(null), 4000)
    }

    const handleDeleteAll = () => {
        if (window.confirm('Are you sure you want to delete ALL leads? This cannot be undone.')) {
            deleteAllMutation.mutate()
        }
    }

    const handleConnectGmail = async () => {
        setConnecting(true)
        try {
            const res = await axios.post('/api/gmail/connect')
            if (res.data?.success) showNotification('success', res.data.message || 'Gmail connected!')
            else showNotification('error', res.data.message || 'Connection failed')
            refetchOAuth(); refetchGmail()
        } catch (err) {
            showNotification('error', err.response?.data?.detail || 'Failed to connect Gmail')
        }
        setConnecting(false)
    }

    const handleDisconnectGmail = async () => {
        setDisconnecting(true)
        try {
            await axios.post('/api/gmail/disconnect')
            showNotification('success', 'Gmail disconnected')
            refetchOAuth(); refetchGmail()
        } catch (err) {
            showNotification('error', 'Failed to disconnect Gmail')
        }
        setDisconnecting(false)
    }

    // Save API keys
    const handleSaveKeys = async () => {
        setSavingKeys(true)
        try {
            const updates = {}
            if (geminiKey && !geminiKey.includes('•')) updates.gemini_api_key = geminiKey

            if (Object.keys(updates).length === 0) {
                showNotification('error', 'No changes to save')
                setSavingKeys(false)
                return
            }

            await axios.post('/api/setup/settings', updates)
            showNotification('success', 'API keys saved successfully')
            refetchSettings()
        } catch (err) {
            showNotification('error', err.response?.data?.detail || 'Failed to save keys')
        }
        setSavingKeys(false)
    }

    // Save performance settings
    const handleSavePerformance = async () => {
        setSavingSettings(true)
        try {
            await axios.post('/api/setup/settings', {
                max_concurrent_browsers: concurrency,
                gemini_temperature: temperature,
                max_email_words: maxWords,
                scraping_delay: scrapingDelay
            })
            showNotification('success', 'Performance settings saved')
            refetchSettings()
        } catch (err) {
            showNotification('error', err.response?.data?.detail || 'Failed to save settings')
        }
        setSavingSettings(false)
    }

    // Upload OAuth JSON
    const handleOAuthUpload = async (e) => {
        const file = e.target.files?.[0]
        if (!file) return
        setUploadingOAuth(true)
        try {
            const formData = new FormData()
            formData.append('file', file)
            const res = await axios.post('/api/setup/gmail-upload', formData)
            showNotification('success', res.data.message || 'OAuth credentials uploaded')
            refetchOAuth(); refetchGmail()
        } catch (err) {
            showNotification('error', err.response?.data?.detail || 'Failed to upload credentials')
        }
        setUploadingOAuth(false)
        e.target.value = ''
    }

    const isConnected = oauthStatus?.status === 'connected'
    const isDisconnected = oauthStatus?.status === 'disconnected'
    const needsSetup = oauthStatus?.status === 'needs_setup'

    // Check for updates
    const handleCheckUpdate = async () => {
        setCheckingUpdate(true)
        try {
            const res = await axios.get('/api/update/check')
            setUpdateInfo(res.data)
            if (res.data.message) {
                showNotification('info', res.data.message)
            } else if (!res.data.update_available) {
                showNotification('success', `You're on the latest version (v${res.data.current_version})`)
            }
        } catch (err) {
            showNotification('error', 'Could not check for updates')
        }
        setCheckingUpdate(false)
    }

    // Apply update
    const handleApplyUpdate = async () => {
        if (!window.confirm('This will download and apply the update, then restart the app. Continue?')) return
        setApplyingUpdate(true)
        try {
            const res = await axios.post('/api/update/apply')
            if (res.data?.status === 'already_up_to_date') {
                showNotification('success', 'Already up to date!')
            } else {
                showNotification('success', 'Update applied! The app will restart shortly.')
            }
        } catch (err) {
            showNotification('error', err.response?.data?.detail || 'Failed to apply update')
        }
        setApplyingUpdate(false)
    }

    // Fetch local version on mount (no network call)
    useEffect(() => {
        axios.get('/api/update/version').then(res => setAppVersion(res.data.version)).catch(() => { })
    }, [])

    // Section card wrapper
    const Section = ({ icon: Icon, title, badge, children, variant }) => (
        <div className={clsx(
            "rounded-xl overflow-hidden border",
            variant === 'danger' ? "bg-red-950/20 border-red-500/20" : "bg-zinc-900 border-zinc-800"
        )}>
            <div className={clsx(
                "p-4 border-b flex items-center justify-between",
                variant === 'danger' ? "border-red-500/20 bg-red-500/10" : "border-zinc-800 bg-zinc-800/50"
            )}>
                <h3 className={clsx("font-semibold flex items-center gap-2", variant === 'danger' && "text-red-400")}>
                    <Icon size={18} /> {title}
                </h3>
                {badge}
            </div>
            <div className="p-6">{children}</div>
        </div>
    )

    return (
        <div className="space-y-6 max-w-2xl mx-auto pb-12">
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
                <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
                <p className="text-zinc-400">Configure API keys, performance, and email integration.</p>
            </header>

            {/* ─── API Keys & Credentials ─── */}
            <Section icon={Key} title="API Keys & Credentials">
                <div className="space-y-5">
                    {/* Gemini API Key */}
                    <div>
                        <label className="block text-sm font-medium text-zinc-300 mb-1.5">Gemini API Key</label>
                        <p className="text-xs text-zinc-500 mb-2">Required for AI-powered email generation</p>
                        <div className="relative">
                            <input
                                type={showGeminiKey ? "text" : "password"}
                                value={geminiKey}
                                onChange={e => setGeminiKey(e.target.value)}
                                placeholder="AIza..."
                                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2.5 pr-10 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-colors"
                            />
                            <button
                                onClick={() => setShowGeminiKey(!showGeminiKey)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                            >
                                {showGeminiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                        </div>
                    </div>

                    <div className="border-t border-zinc-800" />

                    <div className="text-sm text-zinc-400 p-3 bg-zinc-800/50 rounded-lg flex items-center gap-2">
                        <Mail size={16} className="text-blue-400 shrink-0" />
                        <span>To send emails, connect your Gmail account via <strong className="text-zinc-200">Sign in with Google</strong> in the Gmail section below.</span>
                    </div>

                    <button
                        onClick={handleSaveKeys}
                        disabled={savingKeys}
                        className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-sm transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                        {savingKeys ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                        Save Credentials
                    </button>
                </div>
            </Section>

            {/* ─── Gmail Connection (Sign in with Google) ─── */}
            <Section
                icon={Mail}
                title="Gmail Connection"
                badge={
                    <button
                        onClick={() => { refetchOAuth(); refetchGmail(); }}
                        className="p-2 text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-700 transition-colors"
                    >
                        <RefreshCw size={16} />
                    </button>
                }
            >
                <div className="space-y-4">
                    {/* Status */}
                    <div className={clsx(
                        "flex items-center gap-3 p-4 rounded-xl border",
                        isConnected
                            ? "bg-green-500/10 border-green-500/20 text-green-400"
                            : "bg-yellow-500/10 border-yellow-500/20 text-yellow-400"
                    )}>
                        {isConnected ? (
                            <>
                                <CheckCircle size={20} />
                                <div>
                                    <span className="font-medium">Gmail Connected</span>
                                    {oauthStatus?.email && <p className="text-sm text-green-400/70">{oauthStatus.email}</p>}
                                </div>
                            </>
                        ) : (
                            <>
                                <AlertCircle size={20} />
                                <span>{gmailStatus?.message || 'Gmail not configured'}</span>
                            </>
                        )}
                    </div>

                    {/* Actions */}
                    <div className="flex flex-wrap gap-3">
                        {isConnected ? (
                            <button
                                onClick={handleDisconnectGmail}
                                disabled={disconnecting}
                                className="px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/30 transition-colors flex items-center gap-2 disabled:opacity-50"
                            >
                                {disconnecting ? <Loader2 size={16} className="animate-spin" /> : <Unlink size={16} />}
                                Disconnect Gmail
                            </button>
                        ) : (
                            <>
                                {(isDisconnected || needsSetup) && (
                                    <button
                                        onClick={handleConnectGmail}
                                        disabled={connecting}
                                        className="px-5 py-2.5 bg-white text-zinc-800 rounded-lg font-medium text-sm transition-all hover:bg-zinc-100 flex items-center gap-3 disabled:opacity-50 shadow-md"
                                    >
                                        {connecting ? (
                                            <Loader2 size={18} className="animate-spin" />
                                        ) : (
                                            <svg width="18" height="18" viewBox="0 0 24 24">
                                                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                                                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                                            </svg>
                                        )}
                                        Sign in with Google
                                    </button>
                                )}
                            </>
                        )}

                        {/* Upload OAuth JSON */}
                        {(needsSetup || isDisconnected) && (
                            <label className="px-4 py-2 bg-zinc-800 text-zinc-300 border border-zinc-700 rounded-lg hover:bg-zinc-700 transition-colors flex items-center gap-2 cursor-pointer text-sm">
                                {uploadingOAuth ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                                Upload OAuth JSON
                                <input type="file" accept=".json" onChange={handleOAuthUpload} className="hidden" />
                            </label>
                        )}
                    </div>

                    {/* Setup instructions */}
                    {needsSetup && (
                        <div className="text-sm text-zinc-500 space-y-2 mt-2">
                            <p className="font-medium text-zinc-300">Gmail OAuth Setup:</p>
                            <ol className="list-decimal list-inside space-y-1 text-zinc-400">
                                <li>Go to <a href="https://console.cloud.google.com" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">Google Cloud Console</a></li>
                                <li>Create a project & enable <strong>Gmail API</strong></li>
                                <li>Create OAuth credentials (Desktop app)</li>
                                <li>Download JSON & upload it above, or save to <code className="bg-zinc-800 px-1 rounded">credentials/gmail_credentials.json</code></li>
                                <li>Click <strong>Sign in with Google</strong></li>
                            </ol>
                        </div>
                    )}

                </div>
            </Section>

            {/* ─── Performance & Scraping ─── */}
            <Section icon={Zap} title="Performance">
                <div className="space-y-6">
                    {/* Browser Concurrency */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <Cpu size={16} className="text-purple-400" />
                                <label className="text-sm font-medium text-zinc-300">Browser Concurrency</label>
                            </div>
                            <span className="text-sm font-mono text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded">{concurrency}</span>
                        </div>
                        <p className="text-xs text-zinc-500 mb-3">Number of parallel browser tabs during enrichment. Higher = faster but uses more RAM.</p>
                        <input
                            type="range"
                            min={1}
                            max={10}
                            value={concurrency}
                            onChange={e => setConcurrency(parseInt(e.target.value))}
                            className="w-full accent-purple-500"
                        />
                        <div className="flex justify-between text-xs text-zinc-600 mt-1">
                            <span>1 (Low)</span>
                            <span>5 (Medium)</span>
                            <span>10 (Max)</span>
                        </div>
                    </div>

                    <div className="border-t border-zinc-800" />

                    {/* Scraping Delay */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <label className="text-sm font-medium text-zinc-300">Scraping Delay (seconds)</label>
                            <span className="text-sm font-mono text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded">{scrapingDelay.toFixed(1)}s</span>
                        </div>
                        <p className="text-xs text-zinc-500 mb-3">Delay between requests. Lower = faster but higher risk of rate limiting.</p>
                        <input
                            type="range"
                            min={0.5}
                            max={5.0}
                            step={0.5}
                            value={scrapingDelay}
                            onChange={e => setScrapingDelay(parseFloat(e.target.value))}
                            className="w-full accent-zinc-400"
                        />
                    </div>

                    <div className="border-t border-zinc-800" />

                    {/* AI Temperature */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <Thermometer size={16} className="text-orange-400" />
                                <label className="text-sm font-medium text-zinc-300">AI Temperature</label>
                            </div>
                            <span className="text-sm font-mono text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded">{temperature.toFixed(1)}</span>
                        </div>
                        <p className="text-xs text-zinc-500 mb-3">Controls creativity of generated emails. 0 = focused, 2 = very creative.</p>
                        <input
                            type="range"
                            min={0}
                            max={2.0}
                            step={0.1}
                            value={temperature}
                            onChange={e => setTemperature(parseFloat(e.target.value))}
                            className="w-full accent-orange-500"
                        />
                    </div>

                    <div className="border-t border-zinc-800" />

                    {/* Max Email Words */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <FileText size={16} className="text-blue-400" />
                                <label className="text-sm font-medium text-zinc-300">Max Email Length</label>
                            </div>
                            <span className="text-sm font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">{maxWords} words</span>
                        </div>
                        <p className="text-xs text-zinc-500 mb-3">Maximum word count per generated email.</p>
                        <input
                            type="range"
                            min={50}
                            max={500}
                            step={25}
                            value={maxWords}
                            onChange={e => setMaxWords(parseInt(e.target.value))}
                            className="w-full accent-blue-500"
                        />
                    </div>

                    <button
                        onClick={handleSavePerformance}
                        disabled={savingSettings}
                        className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium text-sm transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                        {savingSettings ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                        Save Performance Settings
                    </button>
                </div>
            </Section>

            {/* ─── Database ─── */}
            <Section icon={Database} title="Database">
                <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="bg-zinc-800 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold">{stats?.total || 0}</p>
                        <p className="text-sm text-zinc-500">Total Leads</p>
                    </div>
                    <div className="bg-zinc-800 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-purple-400">{stats?.enriched || 0}</p>
                        <p className="text-sm text-zinc-500">Enriched</p>
                    </div>
                    <div className="bg-zinc-800 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-green-400">{stats?.sent || 0}</p>
                        <p className="text-sm text-zinc-500">Emails Sent</p>
                    </div>
                </div>
                <p className="text-sm text-zinc-500">Data stored in <code className="bg-zinc-800 px-1 rounded">data/leads.json</code></p>
            </Section>

            {/* ─── About & Updates ─── */}
            <Section icon={Info} title="About & Updates">
                <div className="space-y-5">
                    {/* Version Info */}
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="font-medium text-white">BruceLeads</p>
                            <p className="text-sm text-zinc-500">
                                Version <span className="text-zinc-300 font-mono">{appVersion || '...'}</span>
                            </p>
                        </div>
                        <button
                            onClick={handleCheckUpdate}
                            disabled={checkingUpdate}
                            className="px-4 py-2 bg-zinc-800 text-zinc-300 border border-zinc-700 rounded-lg hover:bg-zinc-700 transition-colors flex items-center gap-2 text-sm disabled:opacity-50"
                        >
                            {checkingUpdate ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                            Check for Updates
                        </button>
                    </div>

                    {/* Update Available */}
                    {updateInfo?.update_available && (
                        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 space-y-3">
                            <div className="flex items-center gap-2 text-blue-400">
                                <Download size={18} />
                                <span className="font-medium">Update Available: v{updateInfo.latest_version}</span>
                            </div>
                            {updateInfo.release_notes && (
                                <p className="text-sm text-zinc-400 whitespace-pre-line">{updateInfo.release_notes}</p>
                            )}
                            <button
                                onClick={handleApplyUpdate}
                                disabled={applyingUpdate}
                                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-sm transition-colors flex items-center gap-2 disabled:opacity-50"
                            >
                                {applyingUpdate ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                                {applyingUpdate ? 'Applying Update...' : 'Download & Apply Update'}
                            </button>
                        </div>
                    )}

                    {/* Up to date */}
                    {updateInfo && !updateInfo.update_available && (
                        <div className="flex items-center gap-2 text-green-400 text-sm">
                            <CheckCircle size={16} />
                            <span>You're on the latest version</span>
                        </div>
                    )}
                </div>
            </Section>

            {/* ─── Danger Zone ─── */}
            <Section icon={AlertCircle} title="Danger Zone" variant="danger">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="font-medium">Delete All Leads</p>
                        <p className="text-sm text-zinc-500">Permanently delete all leads from the database</p>
                    </div>
                    <button
                        onClick={handleDeleteAll}
                        disabled={deleteAllMutation.isPending}
                        className="px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/30 transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                        {deleteAllMutation.isPending ? (
                            <><Loader2 className="animate-spin" size={16} /> Deleting...</>
                        ) : (
                            <><Trash2 size={16} /> Delete All</>
                        )}
                    </button>
                </div>
            </Section>
        </div>
    )
}
