'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Lock, User, Mail, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function LoginPage() {
    const router = useRouter();
    const [isLogin, setIsLogin] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const [formData, setFormData] = useState({
        username: '',
        password: '',
        email: '',
        confirmPassword: ''
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setIsLoading(true);

        try {
            if (!isLogin) {
                // 註冊驗證
                if (formData.password !== formData.confirmPassword) {
                    setError('密碼不一致');
                    setIsLoading(false);
                    return;
                }
                if (formData.password.length < 6) {
                    setError('密碼至少需要 6 個字元');
                    setIsLoading(false);
                    return;
                }
            }

            const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
            const body = isLogin
                ? { username: formData.username, password: formData.password }
                : { username: formData.username, password: formData.password, email: formData.email || null };

            const response = await fetch(`http://localhost:8000${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            const data = await response.json();

            if (data.success) {
                // 保存 Token 到 localStorage
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('user', JSON.stringify(data.user));

                setSuccess(isLogin ? '登入成功！正在跳轉...' : '註冊成功！正在跳轉...');

                // 跳轉到 Dashboard
                setTimeout(() => {
                    router.push('/dashboard');
                }, 1000);
            } else {
                setError(data.error || data.detail || '操作失敗');
            }
        } catch (err) {
            setError('連接伺服器失敗，請稍後再試');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center p-4">
            {/* 背景動畫 */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-to-br from-blue-500/10 to-transparent rounded-full blur-3xl animate-pulse" />
                <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-to-tl from-purple-500/10 to-transparent rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
            </div>

            <div className="relative z-10 w-full max-w-md">
                {/* Logo 和標題 */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl shadow-lg mb-4">
                        <span className="text-3xl font-bold text-white">AI</span>
                    </div>
                    <h1 className="text-3xl font-bold text-white mb-2">
                        AI 股票智能分析
                    </h1>
                    <p className="text-blue-200">
                        {isLogin ? '歡迎回來' : '創建您的帳號'}
                    </p>
                </div>

                {/* 登入/註冊表單 */}
                <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-8 border border-white/20 shadow-2xl">
                    {/* Tab 切換 */}
                    <div className="flex bg-white/10 rounded-lg p-1 mb-6">
                        <button
                            onClick={() => { setIsLogin(true); setError(''); }}
                            className={cn(
                                "flex-1 py-2 px-4 rounded-md font-medium transition-all",
                                isLogin
                                    ? "bg-white text-gray-900 shadow"
                                    : "text-white/70 hover:text-white"
                            )}
                        >
                            登入
                        </button>
                        <button
                            onClick={() => { setIsLogin(false); setError(''); }}
                            className={cn(
                                "flex-1 py-2 px-4 rounded-md font-medium transition-all",
                                !isLogin
                                    ? "bg-white text-gray-900 shadow"
                                    : "text-white/70 hover:text-white"
                            )}
                        >
                            註冊
                        </button>
                    </div>

                    {/* 錯誤/成功訊息 */}
                    {error && (
                        <div className="flex items-center gap-2 bg-red-500/20 border border-red-500/50 text-red-200 rounded-lg p-3 mb-4">
                            <AlertCircle className="w-5 h-5 flex-shrink-0" />
                            <span className="text-sm">{error}</span>
                        </div>
                    )}
                    {success && (
                        <div className="flex items-center gap-2 bg-green-500/20 border border-green-500/50 text-green-200 rounded-lg p-3 mb-4">
                            <CheckCircle className="w-5 h-5 flex-shrink-0" />
                            <span className="text-sm">{success}</span>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {/* 使用者名稱 */}
                        <div>
                            <label className="block text-sm font-medium text-white/80 mb-2">
                                使用者名稱
                            </label>
                            <div className="relative">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                                <input
                                    type="text"
                                    value={formData.username}
                                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                    className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="請輸入使用者名稱"
                                    required
                                />
                            </div>
                        </div>

                        {/* Email (僅註冊時顯示) */}
                        {!isLogin && (
                            <div>
                                <label className="block text-sm font-medium text-white/80 mb-2">
                                    Email（選填）
                                </label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                                    <input
                                        type="email"
                                        value={formData.email}
                                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                        className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="your@email.com"
                                    />
                                </div>
                            </div>
                        )}

                        {/* 密碼 */}
                        <div>
                            <label className="block text-sm font-medium text-white/80 mb-2">
                                密碼
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    className="w-full pl-10 pr-12 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="請輸入密碼"
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white"
                                >
                                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        {/* 確認密碼 (僅註冊時顯示) */}
                        {!isLogin && (
                            <div>
                                <label className="block text-sm font-medium text-white/80 mb-2">
                                    確認密碼
                                </label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        value={formData.confirmPassword}
                                        onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                                        className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="請再次輸入密碼"
                                        required
                                    />
                                </div>
                            </div>
                        )}

                        {/* 提交按鈕 */}
                        <button
                            type="submit"
                            disabled={isLoading}
                            className={cn(
                                "w-full py-3 px-4 rounded-lg font-semibold text-white transition-all",
                                "bg-gradient-to-r from-blue-500 to-purple-600",
                                "hover:from-blue-600 hover:to-purple-700",
                                "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-transparent",
                                "disabled:opacity-50 disabled:cursor-not-allowed",
                                "flex items-center justify-center gap-2"
                            )}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    處理中...
                                </>
                            ) : (
                                isLogin ? '登入' : '註冊'
                            )}
                        </button>
                    </form>

                    {/* 忘記密碼 */}
                    {isLogin && (
                        <div className="mt-4 text-center">
                            <button className="text-sm text-blue-300 hover:text-blue-200">
                                忘記密碼？
                            </button>
                        </div>
                    )}
                </div>

                {/* 底部版權 */}
                <div className="mt-8 text-center text-white/40 text-sm">
                    © 2025 AI Stock Intelligence. All rights reserved.
                </div>
            </div>
        </div>
    );
}
