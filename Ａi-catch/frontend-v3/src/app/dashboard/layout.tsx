'use client';

import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [isMobile, setIsMobile] = useState(false);
    const [isMounted, setIsMounted] = useState(false);
    const router = useRouter();

    useEffect(() => {
        setIsMounted(true);
        const token = localStorage.getItem('access_token');
        if (!token) {
            router.push('/login');
            return;
        }

        const checkMobile = () => {
            setIsMobile(window.innerWidth < 768);
            if (window.innerWidth < 768) {
                setSidebarCollapsed(true);
            }
        };

        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, [router]);

    if (!isMounted) return null;

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Sidebar */}
            <Sidebar />

            {/* Main Content */}
            <div
                className={cn(
                    "transition-all duration-300",
                    sidebarCollapsed ? "ml-16" : "ml-64"
                )}
            >
                {/* Header */}
                <Header />

                {/* Page Content */}
                <main className="p-6">
                    {children}
                </main>

                {/* Footer */}
                <footer className="border-t border-gray-200 bg-white py-4 px-6">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-gray-600">
                        <div>
                            © 2025 AI Stock Intelligence Platform. All rights reserved.
                        </div>
                        <div className="flex items-center gap-4">
                            <a href="#" className="hover:text-blue-600 transition-colors">
                                文档
                            </a>
                            <a href="#" className="hover:text-blue-600 transition-colors">
                                API
                            </a>
                            <a href="#" className="hover:text-blue-600 transition-colors">
                                支持
                            </a>
                            <a href="#" className="hover:text-blue-600 transition-colors">
                                关于
                            </a>
                        </div>
                    </div>
                </footer>
            </div>
        </div>
    );
}
