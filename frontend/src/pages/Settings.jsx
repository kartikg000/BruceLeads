import { useState, useEffect } from 'react'
import { Trash2, RefreshCw, CheckCircle, AlertCircle, Mail, Key, Database, Loader2, Link, Unlink, Settings as SettingsIcon, Zap, Save, Eye, EyeOff, Cpu, Thermometer, FileText, Upload } from 'lucide-react'
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
    const [smtpEmail, setSmtpEmail] = useState('')
    const [smtpPassword, setSmtpPassword] = useState('')
    const [showSmtpPassword, setShowSmtpPassword] = useState(false)
    const [concurrency, setConcurrency] = useState(3)
    const [temperature, setTemperature] = useState(0.7)
    const [maxWords, setMaxWords] = useState(150)
    const [scrapingDelay, setScrapingDelay] = useState(2.0)
    const [savingKeys, setSavingKeys] = useState(false)
    const [savingSettings, setSavingSettings] = useState(false)
    const [uploadingOAuth, setUploadingOAuth] = useState(false)

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
            setSmtpEmail(s.gmail_user || '')
            setSmtpPassword(s.gmail_app_password || '')
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
            if (smtpEmail) updates.gmail_address = smtpEmail
            if (smtpPassword && !smtpPassword.includes('•')) updates.gmail_app_password = smtpPassword

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

                    {/* Gmail SMTP */}
                    <div>
                        <label className="block text-sm font-medium text-zinc-300 mb-1.5">Gmail SMTP (Fallback)</label>
                        <p className="text-xs text-zinc-500 mb-2">Used when OAuth is not connected. Requires a Google App Password.</p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <input
                                type="email"
                                value={smtpEmail}
                                onChange={e => setSmtpEmail(e.target.value)}
                                placeholder="you@gmail.com"
                                className="bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-colors"
                            />
                            <div className="relative">
                                <input
                                    type={showSmtpPassword ? "text" : "password"}
                                    value={smtpPassword}
                                    onChange={e => setSmtpPassword(e.target.value)}
                                    placeholder="App Password"
                                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2.5 pr-10 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-colors"
                                />
                                <button
                                    onClick={() => setShowSmtpPassword(!showSmtpPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                                >
                                    {showSmtpPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                            </div>
                        </div>
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

            {/* ─── Gmail OAuth Connection ─── */}
            <Section
                icon={Mail}
                title="Gmail OAuth"
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
                        ) : isDisconnected ? (
                            <button
                                onClick={handleConnectGmail}
                                disabled={connecting}
                                className="px-4 py-2 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-500/30 transition-colors flex items-center gap-2 disabled:opacity-50"
                            >
                                {connecting ? <Loader2 size={16} className="animate-spin" /> : <Link size={16} />}
                                Connect Gmail
                            </button>
                        ) : null}

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
                                <li>Click <strong>Connect Gmail</strong></li>
                            </ol>
                        </div>
                    )}

                    {!isConnected && gmailStatus?.connected && (
                        <div className="text-xs text-zinc-500 p-3 bg-zinc-800/50 rounded-lg">
                            SMTP fallback is active. Configure OAuth above for draft creation support.
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
