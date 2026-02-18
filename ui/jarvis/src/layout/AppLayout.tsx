import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { TopStatusBar } from './TopStatusBar';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex h-screen w-screen bg-background text-foreground overflow-hidden font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 relative">
        <TopStatusBar />
        <main className="flex-1 overflow-hidden relative p-0">
          {children}
        </main>
      </div>
    </div>
  );
}
