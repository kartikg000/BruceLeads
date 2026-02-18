import { useState } from 'react'
import { Search, MapPin, Loader2, Play, Users, Zap, CheckCircle, Globe, Plus, LayoutGrid, KeyRound, LogOut } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'
import axios from 'axios'

export default function FindLeads() {
    const [activeTab, setActiveTab] = useState('maps') // 'maps' | 'social' | 'manual'
    const queryClient = useQueryClient()

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            <header>
                <h2 className="text-3xl font-bold tracking-tight">Find Leads</h2>
                <p className="text-zinc-400">Scrape Google Maps, social media, or add leads manually.</p>
            </header>

            {/* Tab Navigation */}
            <div className="flex gap-2 bg-zinc-900 border border-zinc-800 p-1 rounded-xl w-fit">
                <button
                    onClick={() => setActiveTab('maps')}
                    className={clsx(
                        "px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all",
                        activeTab === 'maps' ? "bg-white text-black" : "text-zinc-400 hover:text-white"
                    )}
                >
                    <MapPin size={16} /> Google Maps
                </button>
                <button
                    onClick={() => setActiveTab('social')}
                    className={clsx(
                        "px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all",
                        activeTab === 'social' ? "bg-purple-500 text-white" : "text-zinc-400 hover:text-white"
                    )}
                >
                    <Globe size={16} /> Social Media
                </button>
                <button
                    onClick={() => setActiveTab('manual')}
                    className={clsx(
                        "px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all",
                        activeTab === 'manual' ? "bg-blue-500 text-white" : "text-zinc-400 hover:text-white"
                    )}
                >
                    <Plus size={16} /> Add Manually
                </button>
            </div>

            {/* Tab Content */}
            <AnimatePresence mode="wait">
                {activeTab === 'maps' && <GoogleMapsTab key="maps" queryClient={queryClient} />}
                {activeTab === 'social' && <SocialMediaTab key="social" queryClient={queryClient} />}
                {activeTab === 'manual' && <ManualAddTab key="manual" queryClient={queryClient} />}
            </AnimatePresence>
        </div>
    )
}

function GoogleMapsTab({ queryClient }) {
    const [query, setQuery] = useState('')
    const [location, setLocation] = useState('')
    const [maxLeads, setMaxLeads] = useState(20)
    const [headless, setHeadless] = useState(true)
    const [autoEnrich, setAutoEnrich] = useState(true)
    const [useGoogle, setUseGoogle] = useState(true)
    const [isScrapingActive, setIsScrapingActive] = useState(false)
    const [scrapeProgress, setScrapeProgress] = useState({ current: 0, total: 0, status: 'idle', message: '' })

    const scrapeMutation = useMutation({
        mutationFn: async (data) => {
            const response = await axios.post('/api/scrape/start', data)
            return response.data
        },
        onMutate: () => {
            setIsScrapingActive(true)
            setScrapeProgress({ current: 0, total: maxLeads, status: 'scraping', message: 'Starting scraper...' })
        },
        onSuccess: (response) => {
            setScrapeProgress({
                current: response.leads_found || 0,
                total: response.leads_found || 0,
                status: 'complete',
                message: `Found ${response.leads_found} leads!`
            })
            setIsScrapingActive(false)
            queryClient.invalidateQueries(['leads'])

            // Save current search IDs to sessionStorage for scope filtering
            if (response.lead_ids && response.lead_ids.length > 0) {
                sessionStorage.setItem('currentSearchIds', JSON.stringify(response.lead_ids))
            }
        },
        onError: (error) => {
            setScrapeProgress({ current: 0, total: 0, status: 'error', message: error.message })
            setIsScrapingActive(false)
        }
    })

    const handleSearch = (e) => {
        e.preventDefault()
        if (!query || !location) return

        scrapeMutation.mutate({
            query,
            location,
            max_results: maxLeads,
            headless,
            auto_enrich: autoEnrich,
            use_google_search: useGoogle
        })
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-zinc-900 border border-zinc-800 p-6 rounded-2xl space-y-6"
        >
            <form onSubmit={handleSearch} className="space-y-4">
                {/* Search Inputs */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">Keywords</label>
                        <div className="flex items-center px-4 bg-zinc-800 rounded-xl border border-zinc-700 focus-within:border-blue-500 transition-colors">
                            <Search className="text-zinc-500 mr-3" size={18} />
                            <input
                                type="text"
                                placeholder="e.g. Plumbers, SEO Agency"
                                className="bg-transparent border-none outline-none text-white w-full h-12 placeholder:text-zinc-600"
                                value={query}
                                onChange={e => setQuery(e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">Location</label>
                        <div className="flex items-center px-4 bg-zinc-800 rounded-xl border border-zinc-700 focus-within:border-blue-500 transition-colors">
                            <MapPin className="text-zinc-500 mr-3" size={18} />
                            <input
                                type="text"
                                placeholder="e.g. Austin TX, New York"
                                className="bg-transparent border-none outline-none text-white w-full h-12 placeholder:text-zinc-600"
                                value={location}
                                onChange={e => setLocation(e.target.value)}
                            />
                        </div>
                    </div>
                </div>

                {/* Options Row */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-zinc-800">
                    {/* Lead Count */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400 flex items-center justify-between">
                            <span>Maximum Results</span>
                            <span className="text-white font-bold">{maxLeads}</span>
                        </label>
                        <input
                            type="range"
                            min="5"
                            max="50"
                            step="5"
                            value={maxLeads}
                            onChange={e => setMaxLeads(parseInt(e.target.value))}
                            className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        />
                    </div>

                    {/* Checkboxes */}
                    <div className="space-y-3">
                        <label className="flex items-center gap-3 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={headless}
                                onChange={e => setHeadless(e.target.checked)}
                                className="rounded border-zinc-600 bg-zinc-700 text-blue-500"
                            />
                            <span className="text-sm text-zinc-400 group-hover:text-white transition-colors">Run in background (headless)</span>
                        </label>
                        <label className="flex items-center gap-3 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={autoEnrich}
                                onChange={e => setAutoEnrich(e.target.checked)}
                                className="rounded border-zinc-600 bg-zinc-700 text-purple-500"
                            />
                            <span className="text-sm text-zinc-400 group-hover:text-white transition-colors">Auto-find emails after scraping</span>
                        </label>
                        <label className="flex items-center gap-3 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={useGoogle}
                                onChange={e => setUseGoogle(e.target.checked)}
                                className="rounded border-zinc-600 bg-zinc-700 text-green-500"
                            />
                            <span className="text-sm text-zinc-400 group-hover:text-white transition-colors">Search Google for emails</span>
                        </label>
                    </div>
                </div>

                {/* Submit Button */}
                <button
                    type="submit"
                    disabled={isScrapingActive || !query || !location}
                    className={clsx(
                        "w-full h-12 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all",
                        isScrapingActive
                            ? "bg-zinc-700 text-zinc-400 cursor-not-allowed"
                            : "bg-white text-black hover:bg-zinc-200"
                    )}
                >
                    {isScrapingActive ? (
                        <><Loader2 className="animate-spin" size={18} /> Scraping...</>
                    ) : (
                        <><Play size={18} fill="currentColor" /> Start Scraping</>
                    )}
                </button>
            </form>

            {/* Progress Display */}
            <AnimatePresence>
                {scrapeProgress.status !== 'idle' && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="border-t border-zinc-800 pt-6"
                    >
                        {scrapeProgress.status === 'complete' ? (
                            <div className="flex items-center gap-4 text-green-400">
                                <CheckCircle size={24} />
                                <div>
                                    <p className="font-medium">{scrapeProgress.message}</p>
                                    <p className="text-sm text-zinc-500">Check Manage Data to view your leads.</p>
                                </div>
                            </div>
                        ) : scrapeProgress.status === 'error' ? (
                            <div className="text-red-400">
                                <p className="font-medium">Error: {scrapeProgress.message}</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <div className="flex items-center gap-3">
                                    <Loader2 className="animate-spin text-blue-500" size={20} />
                                    <span className="text-zinc-300">{scrapeProgress.message}</span>
                                </div>
                                <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                                    <div className="h-full bg-blue-500 transition-all duration-500 animate-pulse" style={{ width: '100%' }} />
                                </div>
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )
}

function SocialMediaTab({ queryClient }) {
    const [query, setQuery] = useState('')
    const [platforms, setPlatforms] = useState(['LinkedIn', 'Twitter', 'Reddit'])
    const [maxResults, setMaxResults] = useState(10)
    const [headless, setHeadless] = useState(true)
    const [isSearching, setIsSearching] = useState(false)
    const [showLogins, setShowLogins] = useState(false)
    const [selectedBrowser, setSelectedBrowser] = useState('chrome')
    const [loggingIn, setLoggingIn] = useState(null)

    const allPlatforms = ['LinkedIn', 'Twitter', 'Reddit', 'Instagram', 'Facebook']

    // Fetch platform session statuses
    const { data: sessionStatuses = {}, refetch: refetchSessions } = useQuery({
        queryKey: ['session-statuses'],
        queryFn: async () => {
            try {
                const res = await axios.get('/api/sessions/status')
                return res.data
            } catch {
                return {}
            }
        }
    })

    const togglePlatform = (platform) => {
        if (platforms.includes(platform)) {
            setPlatforms(platforms.filter(p => p !== platform))
        } else {
            setPlatforms([...platforms, platform])
        }
    }

    const handleLogin = async (platform) => {
        setLoggingIn(platform)
        try {
            await axios.post('/api/sessions/login', {
                platform: platform.toLowerCase(),
                browser: selectedBrowser
            })
            refetchSessions()
        } catch (err) {
            console.error('Login error:', err)
        }
        setLoggingIn(null)
    }

    const handleLogout = async (platform) => {
        try {
            await axios.post('/api/sessions/logout', {
                platform: platform.toLowerCase()
            })
            refetchSessions()
        } catch (err) {
            console.error('Logout error:', err)
        }
    }

    const searchMutation = useMutation({
        mutationFn: async (data) => {
            const response = await axios.post('/api/scrape/social', data)
            return response.data
        },
        onMutate: () => setIsSearching(true),
        onSuccess: (response) => {
            setIsSearching(false)
            queryClient.invalidateQueries(['leads'])
            if (response.lead_ids && response.lead_ids.length > 0) {
                sessionStorage.setItem('currentSearchIds', JSON.stringify(response.lead_ids))
            }
        },
        onError: () => setIsSearching(false)
    })

    const handleSearch = (e) => {
        e.preventDefault()
        if (!query || platforms.length === 0) return
        searchMutation.mutate({ query, platforms, max_results: maxResults, headless })
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-zinc-900 border border-zinc-800 p-6 rounded-2xl space-y-6"
        >
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4 text-sm text-purple-300">
                Find leads by searching for intent on social platforms (e.g. "looking for plumber" on Reddit)
            </div>

            {/* Platform Logins Section */}
            <div className="border border-zinc-800 rounded-xl overflow-hidden">
                <button
                    onClick={() => setShowLogins(!showLogins)}
                    className="w-full p-4 flex items-center justify-between bg-zinc-800/50 hover:bg-zinc-800 transition-colors"
                >
                    <span className="flex items-center gap-2 text-sm font-medium">
                        <KeyRound size={16} className="text-zinc-400" />
                        Platform Logins — Log in to avoid CAPTCHAs
                    </span>
                    <span className="text-xs text-zinc-500">{showLogins ? '▲' : '▼'}</span>
                </button>
                <AnimatePresence>
                    {showLogins && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                        >
                            <div className="p-4 space-y-4">
                                <p className="text-xs text-zinc-500">Log in to your social accounts once. Your session is saved and reused.</p>
                                <div className="flex items-center gap-2">
                                    <label className="text-xs text-zinc-400">Browser:</label>
                                    <select
                                        value={selectedBrowser}
                                        onChange={e => setSelectedBrowser(e.target.value)}
                                        className="bg-zinc-800 border border-zinc-700 rounded-lg text-xs px-2 py-1"
                                    >
                                        <option value="chrome">Chrome</option>
                                        <option value="msedge">Edge</option>
                                        <option value="chromium">Chromium (built-in)</option>
                                    </select>
                                </div>
                                <div className="grid grid-cols-3 gap-3">
                                    {allPlatforms.map(plat => {
                                        const key = plat.toLowerCase()
                                        const status = sessionStatuses[key]?.status || 'not_logged_in'
                                        const isLoggedIn = status === 'logged_in'
                                        const isLogging = loggingIn === plat
                                        return (
                                            <div key={plat} className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-3">
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="text-sm font-medium">{plat}</span>
                                                    <span className={clsx("text-xs", isLoggedIn ? "text-green-400" : "text-zinc-500")}>
                                                        {isLoggedIn ? '● Connected' : '○ Not logged in'}
                                                    </span>
                                                </div>
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => handleLogin(plat)}
                                                        disabled={isLogging}
                                                        className="flex-1 px-2 py-1.5 bg-zinc-700 text-xs rounded-lg hover:bg-zinc-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
                                                    >
                                                        {isLogging ? <Loader2 size={12} className="animate-spin" /> : <KeyRound size={12} />}
                                                        Login
                                                    </button>
                                                    {isLoggedIn && (
                                                        <button
                                                            onClick={() => handleLogout(plat)}
                                                            className="px-2 py-1.5 bg-red-500/20 text-red-400 text-xs rounded-lg hover:bg-red-500/30 transition-colors flex items-center gap-1"
                                                        >
                                                            <LogOut size={12} /> Logout
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <form onSubmit={handleSearch} className="space-y-4">
                <div className="space-y-2">
                    <label className="text-sm font-medium text-zinc-400">Search Query</label>
                    <input
                        type="text"
                        placeholder="e.g. looking for marketing agency, cafe owner"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:border-purple-500 outline-none"
                    />
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium text-zinc-400">Platforms</label>
                    <div className="flex flex-wrap gap-2">
                        {allPlatforms.map(platform => (
                            <button
                                key={platform}
                                type="button"
                                onClick={() => togglePlatform(platform)}
                                className={clsx(
                                    "px-3 py-1.5 rounded-lg text-sm font-medium border transition-all",
                                    platforms.includes(platform)
                                        ? "bg-purple-500/20 text-purple-400 border-purple-500/50"
                                        : "bg-zinc-800 text-zinc-400 border-zinc-700 hover:border-zinc-600"
                                )}
                            >
                                {platform}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400 flex justify-between">
                            <span>Max Results (per platform)</span>
                            <span className="text-white">{maxResults}</span>
                        </label>
                        <input
                            type="range"
                            min="5"
                            max="50"
                            step="5"
                            value={maxResults}
                            onChange={e => setMaxResults(parseInt(e.target.value))}
                            className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
                        />
                    </div>
                    <div className="flex items-end">
                        <label className="flex items-center gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={headless}
                                onChange={e => setHeadless(e.target.checked)}
                                className="rounded border-zinc-600 bg-zinc-700"
                            />
                            <span className="text-sm text-zinc-400">Headless Mode</span>
                        </label>
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={isSearching || !query || platforms.length === 0}
                    className="w-full h-12 bg-purple-500 text-white rounded-xl font-semibold flex items-center justify-center gap-2 hover:bg-purple-600 transition-colors disabled:opacity-50"
                >
                    {isSearching ? (
                        <><Loader2 className="animate-spin" size={18} /> Searching...</>
                    ) : (
                        <><Globe size={18} /> Start Social Search</>
                    )}
                </button>
            </form>

            {/* Search Result */}
            {searchMutation.isSuccess && (
                <div className="flex items-center gap-3 text-green-400 p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
                    <CheckCircle size={20} />
                    <div>
                        <p className="font-medium">Found {searchMutation.data?.leads_found || 0} leads!</p>
                        <p className="text-sm text-zinc-500">Check Manage Data to view your leads.</p>
                    </div>
                </div>
            )}
            {searchMutation.isError && (
                <div className="text-red-400 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <p className="font-medium">Search failed: {searchMutation.error?.message || 'Unknown error'}</p>
                </div>
            )}
        </motion.div>
    )
}

function ManualAddTab({ queryClient }) {
    const [businessName, setBusinessName] = useState('')
    const [email, setEmail] = useState('')
    const [website, setWebsite] = useState('')
    const [ownerName, setOwnerName] = useState('')
    const [phone, setPhone] = useState('')

    const addMutation = useMutation({
        mutationFn: async (data) => {
            const response = await axios.post('/api/leads/add', data)
            return response.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['leads'])
            setBusinessName('')
            setEmail('')
            setWebsite('')
            setOwnerName('')
            setPhone('')
        }
    })

    const handleSubmit = (e) => {
        e.preventDefault()
        if (!businessName) return
        addMutation.mutate({
            business_name: businessName,
            email,
            website,
            owner_name: ownerName,
            phone,
            source: 'Manual'
        })
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-zinc-900 border border-zinc-800 p-6 rounded-2xl space-y-6"
        >
            <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">Business Name *</label>
                        <input
                            type="text"
                            value={businessName}
                            onChange={e => setBusinessName(e.target.value)}
                            placeholder="Acme Corp"
                            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:border-blue-500 outline-none"
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            placeholder="contact@acme.com"
                            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:border-blue-500 outline-none"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">Website</label>
                        <input
                            type="url"
                            value={website}
                            onChange={e => setWebsite(e.target.value)}
                            placeholder="https://acme.com"
                            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:border-blue-500 outline-none"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">Owner Name</label>
                        <input
                            type="text"
                            value={ownerName}
                            onChange={e => setOwnerName(e.target.value)}
                            placeholder="John Smith"
                            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:border-blue-500 outline-none"
                        />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                        <label className="text-sm font-medium text-zinc-400">Phone</label>
                        <input
                            type="tel"
                            value={phone}
                            onChange={e => setPhone(e.target.value)}
                            placeholder="+1 (555) 123-4567"
                            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:border-blue-500 outline-none"
                        />
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={addMutation.isPending || !businessName}
                    className="w-full h-12 bg-blue-500 text-white rounded-xl font-semibold flex items-center justify-center gap-2 hover:bg-blue-600 transition-colors disabled:opacity-50"
                >
                    {addMutation.isPending ? (
                        <><Loader2 className="animate-spin" size={18} /> Adding...</>
                    ) : (
                        <><Plus size={18} /> Add Lead</>
                    )}
                </button>

                {addMutation.isSuccess && (
                    <div className="flex items-center gap-2 text-green-400 text-sm">
                        <CheckCircle size={16} /> Lead added successfully!
                    </div>
                )}
            </form>
        </motion.div>
    )
}
