import { Logo } from '@/components/layout/Logo'

export function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="space-y-4 text-center">
        <div className="flex justify-center"><Logo /></div>
        <p className="text-muted-foreground">Sign-in is built in the Auth feature.</p>
      </div>
    </main>
  )
}
