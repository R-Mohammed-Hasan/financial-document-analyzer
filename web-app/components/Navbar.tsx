import Link from 'next/link';
import { useRouter } from 'next/router';
import { Button } from '@/components/ui/button';
import { useUserAuth, PUBLIC_ROUTES } from '@/providers/auth-provider';
import { LogOut, UserRound, FileText, Home } from 'lucide-react';

export default function Navbar() {
  const { user, logOut } = useUserAuth();
  const router = useRouter();

  // Optionally hide navbar on public routes (login/register)
  if (PUBLIC_ROUTES.includes(router.pathname)) return null;

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <nav className="flex items-center gap-3 text-sm">
          <Link href="/" className="inline-flex items-center gap-2 font-semibold">
            <Home size={18} />
            <span>FinDoc Analyzer</span>
          </Link>
          <Link href="/dashboard" className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">
            <FileText size={16} /> Dashboard
          </Link>
        </nav>

        <div className="flex items-center gap-3">
          {user ? (
            <>
              <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
                <UserRound size={16} />
                <span>{user.email}</span>
              </div>
              <Button variant="outline" size="sm" onClick={logOut} className="gap-2">
                <LogOut size={16} />
                Logout
              </Button>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <Link href="/users/login">
                <Button variant="outline" size="sm">Login</Button>
              </Link>
              <Link href="/users/register">
                <Button size="sm">Register</Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
