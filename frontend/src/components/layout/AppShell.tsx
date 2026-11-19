import { FileText, History, Menu } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router'

import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { ChatLauncher } from '@/features/chat/ChatLauncher'
import { cn } from '@/lib/utils'

import { useMe } from '@/features/auth/useAuth'

import { Logo } from './Logo'
import { UserMenu } from './UserMenu'

const navItems = [
  { to: '/documents', label: 'Documents', icon: FileText, adminOnly: false },
  { to: '/activity', label: 'Activity', icon: History, adminOnly: true },
]

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { data: me } = useMe()
  const isAdmin = me?.role === 'admin'
  return (
    <div className="flex h-full flex-col gap-7 px-3 py-5">
      <NavLink
        to="/documents"
        aria-label="Exin Lab Search home"
        className="px-2"
        onClick={onNavigate}
      >
        <Logo />
      </NavLink>

      <nav aria-label="Main" className="flex flex-col gap-0.5">
        {navItems
          .filter((item) => !item.adminOnly || isAdmin)
          .map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex h-10 items-center gap-2.5 rounded-lg px-2.5 text-sm transition-colors',
                isActive
                  ? 'bg-secondary font-medium text-foreground [&_svg]:text-primary'
                  : 'text-muted-foreground hover:bg-secondary/60 hover:text-foreground',
              )
            }
          >
            <Icon aria-hidden="true" className="size-[18px]" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto">
        <UserMenu />
      </div>
    </div>
  )
}

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="flex min-h-svh bg-background text-foreground">
      {/* Desktop / tablet sidebar */}
      <aside className="sticky top-0 hidden h-svh w-60 shrink-0 border-r border-border bg-card/40 md:block">
        <SidebarContent />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Phone top bar */}
        <header className="flex items-center justify-between border-b border-border px-4 py-2.5 md:hidden">
          <NavLink to="/documents" aria-label="Exin Lab Search home">
            <Logo />
          </NavLink>
          <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon" aria-label="Open menu" className="size-11">
                <Menu aria-hidden="true" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-60 p-0 data-[side=left]:w-60 data-[side=left]:sm:max-w-60">
              <SheetTitle className="sr-only">Menu</SheetTitle>
              <SidebarContent onNavigate={() => setMenuOpen(false)} />
            </SheetContent>
          </Sheet>
        </header>

        <main className="mx-auto w-full max-w-[1600px] px-5 py-8 md:px-8 md:py-10 xl:px-12">
          <Outlet />
        </main>
      </div>

      <ChatLauncher />
    </div>
  )
}
