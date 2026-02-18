import { useState, useRef, useEffect } from 'react'
import { Key, Mail, Upload, CheckCircle, AlertCircle, ArrowRight, ArrowLeft, Loader2, Sparkles, Shield, Zap, Download, Globe } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import clsx from 'clsx'

const STEPS = [
    { id: 'welcome', label: 'Welcome' },
    { id: 'browser', label: 'Browser' },
    { id: 'gemini', label: 'AI Setup' },
    { id: 'gmail', label: 'Email Setup' },
    { id: 'done', label: 'Complete' },
]

export default function SetupWizard({ onComplete }) {
    const [step, setStep] = useState(0)
    const [geminiKey, setGeminiKey] = useState('')
    const [gmailEmail, setGmailEmail] = useState('')
    const [gmailPassword, setGmailPassword] = useState('')
    const [oauthFile, setOauthFile] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')
    const [geminiSaved, setGeminiSaved] = useState(false)
    const [gmailConfigured, setGmailConfigured] = useState(false)
    const [playwrightInstalled, setPlaywrightInstalled] = useState(null) // null = checking
    const [installingPlaywright, setInstallingPlaywright] = useState(false)
    const fileInputRef = useRef(null)

    const currentStep = STEPS[step]

    const clearMessages = () => { setError(''); setSuccess('') }

    // Check Playwright status on mount
    useEffect(() => {
        axios.get('/api/setup/playwright-status')
            .then(res => setPlaywrightInstalled(res.data.chromium_installed))
            .catch(() => setPlaywrightInstalled(false))
    }, [])

    // ── Step handlers ────────────────────────────────────────

    const handleSaveGemini = async () => {
        if (!geminiKey.trim()) { setError('Please enter your Gemini API key'); return }
        setLoading(true); clearMessages()
        try {
            const res = await axios.post('/api/setup/gemini', { api_key: geminiKey.trim() })
            if (res.data.success) {
                setGeminiSaved(true)
                setSuccess('API key validated and saved!')
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to save API key')
        }
        setLoading(false)
    }

    const handleSaveGmailSMTP = async () => {
        if (!gmailEmail.trim() || !gmailPassword.trim()) {
            setError('Email and app password are required'); return
        }
        setLoading(true); clearMessages()
        try {
            const res = await axios.post('/api/setup/gmail-smtp', {
                email: gmailEmail.trim(),
                app_password: gmailPassword.trim(),
            })
            if (res.data.success) {
                setGmailConfigured(true)
                setSuccess('Gmail SMTP credentials saved!')
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to save Gmail credentials')
        }
        setLoading(false)
    }

    const handleUploadOAuth = async () => {
        if (!oauthFile) { setError('Please select a credentials JSON file'); return }
        setLoading(true); clearMessages()
        try {
            const formData = new FormData()
            formData.append('file', oauthFile)
            const res = await axios.post('/api/setup/gmail-upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            })
            if (res.data.success) {
                setSuccess('OAuth credentials uploaded! You can connect Gmail later in Settings.')
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to upload credentials')
        }
        setLoading(false)
    }

    const handleInstallPlaywright = async () => {
        setInstallingPlaywright(true); clearMessages()
        try {
            const res = await axios.post('/api/setup/install-playwright', null, { timeout: 300000 })
            if (res.data.success) {
                setPlaywrightInstalled(true)
                setSuccess(res.data.message)
            } else {
                setError(res.data.message)
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Installation failed. Try running "playwright install chromium" manually.')
        }
        setInstallingPlaywright(false)
    }

    const handleComplete = async () => {
        setLoading(true)
        try {
            await axios.post('/api/setup/complete')
        } catch { /* ignore */ }
        setLoading(false)
        onComplete()
    }

    const nextStep = () => { clearMessages(); setStep(s => Math.min(s + 1, STEPS.length - 1)) }
    const prevStep = () => { clearMessages(); setStep(s => Math.max(s - 1, 0)) }

    // ── Render ───────────────────────────────────────────────

    return (
        <div className="fixed inset-0 z-[100] bg-zinc-950 flex items-center justify-center p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="w-full max-w-xl bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl"
            >
                {/* Progress Bar */}
                <div className="flex gap-1 p-4 pb-0">
                    {STEPS.map((s, i) => (
                        <div key={s.id} className={clsx(
                            "h-1 flex-1 rounded-full transition-colors duration-300",
                            i <= step ? "bg-white" : "bg-zinc-800"
                        )} />
                    ))}
                </div>

                {/* Content */}
                <div className="p-8">
                    <AnimatePresence mode="wait">
                        {currentStep.id === 'welcome' && (
                            <StepContainer key="welcome">
                                <div className="text-center space-y-6">
                                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-white/5 border border-zinc-800">
                                        <Zap size={36} className="text-white" />
                                    </div>
                                    <div>
                                        <h2 className="text-3xl font-bold tracking-tight">Welcome to BruceLeads</h2>
                                        <p className="text-zinc-400 mt-2 text-lg">Let's get you set up in under 2 minutes.</p>
                                    </div>
                                    <div className="grid grid-cols-3 gap-4 text-sm">
                                        <FeatureCard icon={Sparkles} label="AI Emails" desc="Gemini-powered" />
                                        <FeatureCard icon={Mail} label="Gmail" desc="Send & draft" />
                                        <FeatureCard icon={Shield} label="Scraping" desc="Maps & Social" />
                                    </div>
                                    <button onClick={nextStep}
                                        className="px-8 py-3 bg-white text-black font-semibold rounded-xl hover:bg-zinc-200 transition-colors flex items-center gap-2 mx-auto">
                                        Get Started <ArrowRight size={18} />
                                    </button>
                                </div>
                            </StepContainer>
                        )}

                        {currentStep.id === 'browser' && (
                            <StepContainer key="browser">
                                <div className="space-y-6">
                                    <div>
                                        <h2 className="text-2xl font-bold flex items-center gap-3">
                                            <Globe size={24} /> Browser Setup
                                        </h2>
                                        <p className="text-zinc-400 mt-1">BruceLeads needs Chromium to scrape leads from Google Maps and social media.</p>
                                    </div>

                                    <div className={clsx(
                                        "flex items-center gap-3 p-4 rounded-xl border",
                                        playwrightInstalled === true
                                            ? "bg-green-500/10 border-green-500/20 text-green-400"
                                            : playwrightInstalled === false
                                                ? "bg-yellow-500/10 border-yellow-500/20 text-yellow-400"
                                                : "bg-zinc-800/50 border-zinc-700 text-zinc-400"
                                    )}>
                                        {playwrightInstalled === null ? (
                                            <><Loader2 size={20} className="animate-spin" /> <span>Checking browser status...</span></>
                                        ) : playwrightInstalled ? (
                                            <><CheckCircle size={20} /> <span className="font-medium">Chromium is installed and ready!</span></>
                                        ) : (
                                            <><AlertCircle size={20} /> <span>Chromium browser not found — click below to install it.</span></>
                                        )}
                                    </div>

                                    {!playwrightInstalled && (
                                        <button
                                            onClick={handleInstallPlaywright}
                                            disabled={installingPlaywright}
                                            className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
                                        >
                                            {installingPlaywright ? (
                                                <><Loader2 size={18} className="animate-spin" /> Installing Chromium... (this may take a minute)</>
                                            ) : (
                                                <><Download size={18} /> Install Chromium Browser</>
                                            )}
                                        </button>
                                    )}

                                    {installingPlaywright && (
                                        <div className="text-xs text-zinc-500 text-center">
                                            Downloading ~150 MB. Please don't close the app.
                                        </div>
                                    )}

                                    <MessageDisplay error={error} success={success} />

                                    <div className="flex justify-between pt-4">
                                        <button onClick={prevStep} className="px-4 py-2 text-zinc-400 hover:text-white flex items-center gap-1">
                                            <ArrowLeft size={16} /> Back
                                        </button>
                                        <button onClick={nextStep}
                                            className={clsx(
                                                "px-6 py-2.5 rounded-xl font-semibold flex items-center gap-2 transition-colors",
                                                playwrightInstalled ? "bg-white text-black hover:bg-zinc-200" : "bg-zinc-800 text-zinc-400 hover:text-white"
                                            )}>
                                            {playwrightInstalled ? 'Continue' : 'Skip for now'} <ArrowRight size={16} />
                                        </button>
                                    </div>
                                </div>
                            </StepContainer>
                        )}

                        {currentStep.id === 'gemini' && (
                            <StepContainer key="gemini">
                                <div className="space-y-6">
                                    <div>
                                        <h2 className="text-2xl font-bold flex items-center gap-3">
                                            <Key size={24} /> Gemini AI Setup
                                        </h2>
                                        <p className="text-zinc-400 mt-1">Powers AI-generated cold emails for your leads.</p>
                                    </div>

                                    <div className="space-y-3">
                                        <label className="text-sm font-medium text-zinc-300">Gemini API Key</label>
                                        <input
                                            type="password"
                                            value={geminiKey}
                                            onChange={e => setGeminiKey(e.target.value)}
                                            placeholder="AIza..."
                                            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-zinc-500 transition-all"
                                            disabled={geminiSaved}
                                        />
                                        <p className="text-xs text-zinc-500">
                                            Get your free key at{' '}
                                            <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer"
                                                className="text-blue-400 hover:underline">aistudio.google.com/apikey</a>
                                        </p>
                                    </div>

                                    {!geminiSaved && (
                                        <button onClick={handleSaveGemini} disabled={loading}
                                            className="px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-zinc-200 transition-colors flex items-center gap-2 disabled:opacity-50">
                                            {loading ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
                                            Validate & Save
                                        </button>
                                    )}

                                    <MessageDisplay error={error} success={success} />

                                    <div className="flex justify-between pt-4">
                                        <button onClick={prevStep} className="px-4 py-2 text-zinc-400 hover:text-white flex items-center gap-1">
                                            <ArrowLeft size={16} /> Back
                                        </button>
                                        <button onClick={nextStep}
                                            className={clsx(
                                                "px-6 py-2.5 rounded-xl font-semibold flex items-center gap-2 transition-colors",
                                                geminiSaved ? "bg-white text-black hover:bg-zinc-200" : "bg-zinc-800 text-zinc-400 hover:text-white"
                                            )}>
                                            {geminiSaved ? 'Continue' : 'Skip for now'} <ArrowRight size={16} />
                                        </button>
                                    </div>
                                </div>
                            </StepContainer>
                        )}

                        {currentStep.id === 'gmail' && (
                            <StepContainer key="gmail">
                                <div className="space-y-6">
                                    <div>
                                        <h2 className="text-2xl font-bold flex items-center gap-3">
                                            <Mail size={24} /> Email Setup
                                        </h2>
                                        <p className="text-zinc-400 mt-1">Connect Gmail to send emails and create drafts.</p>
                                    </div>

                                    {/* SMTP Option */}
                                    <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-5 space-y-4">
                                        <h3 className="font-semibold text-sm uppercase tracking-wider text-zinc-300">Option 1: Gmail App Password (Easiest)</h3>
                                        <div className="space-y-3">
                                            <input type="email" value={gmailEmail} onChange={e => setGmailEmail(e.target.value)}
                                                placeholder="your.email@gmail.com"
                                                className="w-full px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-white/20 text-sm"
                                                disabled={gmailConfigured} />
                                            <input type="password" value={gmailPassword} onChange={e => setGmailPassword(e.target.value)}
                                                placeholder="App password (16 chars)"
                                                className="w-full px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-white/20 text-sm"
                                                disabled={gmailConfigured} />
                                        </div>
                                        <p className="text-xs text-zinc-500">
                                            Create an app password at{' '}
                                            <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer"
                                                className="text-blue-400 hover:underline">myaccount.google.com/apppasswords</a>
                                        </p>
                                        {!gmailConfigured && (
                                            <button onClick={handleSaveGmailSMTP} disabled={loading}
                                                className="px-5 py-2 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-500/30 transition-colors flex items-center gap-2 disabled:opacity-50 text-sm font-medium">
                                                {loading ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                                                Save SMTP Credentials
                                            </button>
                                        )}
                                    </div>

                                    {/* OAuth Option */}
                                    <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-5 space-y-4">
                                        <h3 className="font-semibold text-sm uppercase tracking-wider text-zinc-300">Option 2: Gmail OAuth (Advanced — for drafts)</h3>
                                        <p className="text-xs text-zinc-500">Upload your Google Cloud OAuth credentials JSON to enable creating drafts directly in Gmail.</p>
                                        <div className="flex items-center gap-3">
                                            <input ref={fileInputRef} type="file" accept=".json" className="hidden"
                                                onChange={e => setOauthFile(e.target.files?.[0] || null)} />
                                            <button onClick={() => fileInputRef.current?.click()}
                                                className="px-4 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-zinc-300 hover:border-zinc-500 transition-colors flex items-center gap-2">
                                                <Upload size={14} /> {oauthFile ? oauthFile.name : 'Choose JSON File'}
                                            </button>
                                            {oauthFile && (
                                                <button onClick={handleUploadOAuth} disabled={loading}
                                                    className="px-4 py-2 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded-lg hover:bg-purple-500/30 transition-colors text-sm font-medium disabled:opacity-50">
                                                    {loading ? <Loader2 size={14} className="animate-spin" /> : 'Upload'}
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    <MessageDisplay error={error} success={success} />

                                    <div className="flex justify-between pt-2">
                                        <button onClick={prevStep} className="px-4 py-2 text-zinc-400 hover:text-white flex items-center gap-1">
                                            <ArrowLeft size={16} /> Back
                                        </button>
                                        <button onClick={nextStep}
                                            className={clsx(
                                                "px-6 py-2.5 rounded-xl font-semibold flex items-center gap-2 transition-colors",
                                                gmailConfigured ? "bg-white text-black hover:bg-zinc-200" : "bg-zinc-800 text-zinc-400 hover:text-white"
                                            )}>
                                            {gmailConfigured ? 'Continue' : 'Skip for now'} <ArrowRight size={16} />
                                        </button>
                                    </div>
                                </div>
                            </StepContainer>
                        )}

                        {currentStep.id === 'done' && (
                            <StepContainer key="done">
                                <div className="text-center space-y-6">
                                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-500/10 border border-green-500/20">
                                        <CheckCircle size={40} className="text-green-400" />
                                    </div>
                                    <div>
                                        <h2 className="text-3xl font-bold">You're All Set!</h2>
                                        <p className="text-zinc-400 mt-2">BruceLeads is ready. You can always update settings later.</p>
                                    </div>
                                    <div className="space-y-2 text-sm text-left bg-zinc-800/50 rounded-xl p-4 max-w-sm mx-auto">
                                        <StatusRow label="Chromium Browser" ok={playwrightInstalled} />
                                        <StatusRow label="Gemini AI" ok={geminiSaved} />
                                        <StatusRow label="Gmail SMTP" ok={gmailConfigured} />
                                        <StatusRow label="Gmail OAuth" ok={!!oauthFile} optional />
                                    </div>
                                    <button onClick={handleComplete} disabled={loading}
                                        className="px-8 py-3 bg-white text-black font-semibold rounded-xl hover:bg-zinc-200 transition-colors flex items-center gap-2 mx-auto disabled:opacity-50">
                                        {loading ? <Loader2 size={18} className="animate-spin" /> : <Zap size={18} />}
                                        Launch BruceLeads
                                    </button>
                                </div>
                            </StepContainer>
                        )}
                    </AnimatePresence>
                </div>
            </motion.div>
        </div>
    )
}


// ── Sub-components ───────────────────────────────────────────

function StepContainer({ children }) {
    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
        >
            {children}
        </motion.div>
    )
}

function FeatureCard({ icon: Icon, label, desc }) {
    return (
        <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-4 text-center">
            <Icon size={24} className="mx-auto mb-2 text-zinc-300" />
            <p className="font-semibold text-sm">{label}</p>
            <p className="text-xs text-zinc-500">{desc}</p>
        </div>
    )
}

function MessageDisplay({ error, success }) {
    if (!error && !success) return null
    return (
        <div className={clsx(
            "flex items-center gap-2 px-4 py-3 rounded-lg text-sm",
            error ? "bg-red-500/10 border border-red-500/20 text-red-400" : "bg-green-500/10 border border-green-500/20 text-green-400"
        )}>
            {error ? <AlertCircle size={16} /> : <CheckCircle size={16} />}
            {error || success}
        </div>
    )
}

function StatusRow({ label, ok, optional }) {
    return (
        <div className="flex items-center justify-between py-1">
            <span className="text-zinc-400">{label}</span>
            {ok ? (
                <span className="text-green-400 flex items-center gap-1 text-xs"><CheckCircle size={14} /> Configured</span>
            ) : (
                <span className="text-zinc-600 text-xs">{optional ? 'Optional' : 'Skipped'}</span>
            )}
        </div>
    )
}
