
import { useState, useEffect } from 'react'
import { Users, Mail, Send, Activity, ArrowUpRight, Settings } from 'lucide-react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import clsx from 'clsx'

export default function Dashboard() {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch('/stats')
            .then(res => res.json())
            .then(data => {
                setStats(data)
                setLoading(false)
            })
            .catch(err => {
                console.error("Failed to fetch stats:", err)
                setLoading(false)
            })
    }, [])

    return (
        <div className="space-y-8">
            <header>
                <h2 className="text-3xl font-bold tracking-tight">Overview</h2>
                <p className="text-secondary">Here's what's happening with your leads today.</p>
            </header>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <StatsCard
                    title="Total Leads"
                    value={loading ? "..." : stats?.total || 0}
                    icon={Users}
                    color="accent"
                    delay={0}
                />
                <StatsCard
                    title="Enriched"
                    value={loading ? "..." : stats?.enriched || 0}
                    icon={Mail}
                    color="green"
                    delay={0.1}
                />
                <StatsCard
                    title="Emails Sent"
                    value={loading ? "..." : stats?.sent || 0}
                    icon={Send}
                    color="purple"
                    delay={0.2}
                />
            </div>

            {/* Activity Feed Placeholder */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="grid grid-cols-1 lg:grid-cols-2 gap-6"
            >
                <div className="bg-surface border border-border rounded-xl p-6 min-h-[300px]">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Activity size={18} className="text-zinc-500" />
                        Recent Activity
                    </h3>
                    <div className="flex flex-col items-center justify-center h-full text-zinc-600 gap-2 opacity-50">
                        <Activity size={40} />
                        <p>No recent activity</p>
                    </div>
                </div>

                <div className="bg-surface border border-border rounded-xl p-6 min-h-[300px]">
                    <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
                    <div className="grid grid-cols-2 gap-4">
                        <QuickAction label="New Search" href="/find" />
                        <QuickAction label="Manage Leads" href="/manage" />
                        <QuickAction label="Draft Email" href="/email" />
                        <QuickAction label="Settings" href="/settings" />
                    </div>
                </div>
            </motion.div>
        </div>
    )
}

function StatsCard({ title, value, icon: Icon, color, delay }) {
    const colorMap = {
        accent: "text-accent bg-accent/10 border-accent/20",
        green: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
        purple: "text-purple-500 bg-purple-500/10 border-purple-500/20"
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay }}
            className="bg-surface border border-border p-6 rounded-xl flex items-center justify-between group hover:border-zinc-700 transition-colors"
        >
            <div>
                <p className="text-secondary text-sm font-medium mb-1 uppercase tracking-wider">{title}</p>
                <p className="text-4xl font-bold font-mono tracking-tight">{value}</p>
            </div>
            <div className={clsx("p-4 rounded-xl border transition-transform duration-300 group-hover:scale-110", colorMap[color])}>
                <Icon size={24} />
            </div>
        </motion.div>
    )
}

function QuickAction({ label, href }) {
    return (
        <Link to={href} className="flex items-center justify-between p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-600 hover:bg-zinc-800 transition-all group">
            <span className="font-medium text-zinc-300 group-hover:text-white transition-colors">{label}</span>
            <ArrowUpRight size={16} className="text-zinc-600 group-hover:text-white transition-colors" />
        </Link>
    )
}
