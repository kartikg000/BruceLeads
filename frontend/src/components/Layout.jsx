
import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Users, Mail, Send, Settings, Database, LogOut } from 'lucide-react'
import clsx from 'clsx'

const NAV_ITEMS = [
    { label: 'Dashboard', icon: LayoutDashboard, path: '/' },
    { label: 'Find Leads', icon: Users, path: '/find' },
    { label: 'Manage Data', icon: Database, path: '/manage' },
    { label: 'Email Studio', icon: Mail, path: '/email' },
    { label: 'Outbox', icon: Send, path: '/outbox' },
]

export default function Layout({ children, user, onLogout }) {
    const location = useLocation()

    return (
        <div className="flex bg-background text-primary min-h-screen w-full font-sans">
            {/* Sidebar */}
            <aside className="w-64 border-r border-border bg-surface flex flex-col fixed h-full z-10 transition-all duration-300">
                <div className="p-8 pb-4 text-center">
                    <h1 className="text-xl font-bold tracking-widest text-primary">
                        BRUCE LEADS <span className="text-[10px] align-top text-accent font-bold">BW</span>
                    </h1>
                    <p className="text-xs text-secondary mt-1 tracking-widest uppercase opacity-50">AgenticOS v2.0</p>
                </div>

                <nav className="flex flex-col gap-1 px-4 mt-6">
                    {NAV_ITEMS.map((item) => (
                        <NavItem
                            key={item.path}
                            item={item}
                            active={location.pathname === item.path}
                        />
                    ))}
                </nav>

                {/* Bottom: User profile + Settings */}
                <div className="mt-auto">
                    {user && (
                        <div className="px-4 pb-2">
                            <div className="flex items-center gap-3 p-3 bg-zinc-800/50 rounded-xl">
                                {user.picture ? (
                                    <img src={user.picture} alt="" className="w-8 h-8 rounded-full flex-shrink-0" referrerPolicy="no-referrer" />
                                ) : (
                                    <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
                                        {(user.name || user.email || '?')[0].toUpperCase()}
                                    </div>
                                )}
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-white truncate">{user.name || 'User'}</p>
                                    <p className="text-[11px] text-zinc-500 truncate">{user.email}</p>
                                </div>
                                <button onClick={onLogout} title="Sign out"
                                    className="text-zinc-600 hover:text-red-400 transition-colors flex-shrink-0">
                                    <LogOut size={15} />
                                </button>
                            </div>
                        </div>
                    )}
                    <div className="p-4 pt-0">
                        <Link to="/settings" className="flex items-center gap-3 px-4 py-3 rounded-lg text-zinc-500 hover:text-white hover:bg-zinc-800/50 transition-all">
                            <Settings size={20} />
                            <span className="text-sm font-medium">Settings</span>
                        </Link>
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 ml-64 p-8 overflow-y-auto h-screen scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent">
                <div className="max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {children}
                </div>
            </main>
        </div>
    )
}

function NavItem({ item, active }) {
    const Icon = item.icon
    return (
        <Link
            to={item.path}
            className={clsx(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group relative overflow-hidden",
                active
                    ? "bg-primary text-background font-semibold shadow-[0_0_15px_rgba(255,255,255,0.1)]"
                    : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
            )}
        >
            <Icon size={20} className={clsx("transition-transform duration-300", active && "scale-110")} />
            <span className="text-sm">{item.label}</span>

            {/* Active Indicator Line */}
            {active && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-accent rounded-r-full" />
            )}
        </Link>
    )
}
