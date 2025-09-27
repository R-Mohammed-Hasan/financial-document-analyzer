import { Spinner } from '@/components/ui/spinner';
import { useUserAuth } from '@/providers/auth-provider';

export default function GlobalLoader() {
  const { loading } = useUserAuth();

  if (!loading) return null;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-background/60 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-3 rounded-md border bg-card p-6 shadow-sm">
        <Spinner size={28} />
        <div className="text-sm text-muted-foreground">Loading your session…</div>
      </div>
    </div>
  );
}
