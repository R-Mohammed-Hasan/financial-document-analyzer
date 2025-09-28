import React, { PropsWithChildren, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { ChevronLeft, ChevronRight, LayoutDashboard, FileText } from 'lucide-react';

// Simple utility fallback if cn is not available
function classNames(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ');
}

export default function SidebarLayout({ children }: PropsWithChildren<{}>) {
  const [collapsed, setCollapsed] = useState(false);
  const router = useRouter();

  const navItems = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/files', label: 'Files', icon: FileText },
  ];

  const isActive = (href: string) => {
    const current = router.asPath || router.pathname;
    return current === href || current.startsWith(href + '/');
  };

  return (
    <div className="h-[calc(100vh-56px)] bg-background overflow-hidden">
      <div className="flex h-full">
        {/* Sidebar */}
        <aside
          className={classNames(
            'relative transition-[width] duration-300 ease-in-out bg-blue-900 text-white h-full flex-shrink-0',
            collapsed ? 'w-16 md:w-16' : 'w-16 md:w-64'
          )}
        >
          <div className="h-12 flex items-center px-3 border-b border-blue-800">
            <span className={classNames('font-semibold text-sm transition-opacity', collapsed && 'opacity-0')}></span>
          </div>

          {/* Floating toggle handle */}
          <button
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onClick={() => setCollapsed((v) => !v)}
            className="hidden md:flex absolute top-[5%] -right-3 -translate-y-1/2 rounded-full border border-blue-200 bg-white text-blue-900 shadow hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 p-1.5"
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
          <nav className="py-2">
            {navItems.map((item) => {
              const Icon = item.icon as any;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={classNames(
                    'flex items-center gap-2 px-3 py-2 text-sm hover:bg-blue-800 transition-colors',
                    isActive(item.href) && 'bg-blue-800 font-medium',
                  )}
                >
                  {Icon && <Icon size={16} />}
                  <span className={classNames('hidden md:inline truncate transition-[opacity] duration-200', collapsed && 'opacity-0')}>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Content */}
        <main className={classNames('flex-1 min-w-0 h-full overflow-y-auto transition-[width] duration-300 ease-in-out')}>
          <div className="p-4 md:p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
