'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
    Shield, Users, Key, RefreshCw, Check, X, AlertTriangle,
    Eye, EyeOff, Crown, Trash2, ToggleLeft, ToggleRight,
    UserCog, MoreVertical, ChevronDown
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface User {
    id: number;
    username: string;
    email: string;
    role: string;
    is_active: boolean;
    created_at: string | null;
    last_login: string | null;
}

export default function AdminPage() {
    const router = useRouter();
    const [users, setUsers] = useState<User[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isAdmin, setIsAdmin] = useState(false);
    const [error, setError] = useState('');
    const [currentUserId, setCurrentUserId] = useState<number | null>(null);

    // 操作狀態
    const [actionLoading, setActionLoading] = useState<number | null>(null);
    const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    // 重設密碼相關
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [newPassword, setNewPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [isResetting, setIsResetting] = useState(false);

    // 刪除確認
    const [deleteConfirmUser, setDeleteConfirmUser] = useState<User | null>(null);

    // 下拉選單
    const [openDropdown, setOpenDropdown] = useState<number | null>(null);

    const getToken = () => localStorage.getItem('access_token');

    // 驗證管理者權限並獲取用戶列表
    const fetchUsers = useCallback(async () => {
        const token = getToken();
        if (!token) {
            router.push('/login');
            return;
        }

        try {
            // 先獲取當前用戶資訊
            const meResponse = await fetch('http://localhost:8000/api/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const meData = await meResponse.json();
            if (meData.success) {
                setCurrentUserId(meData.user.id);
            }

            const response = await fetch('http://localhost:8000/api/admin/users', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 403) {
                setError('權限不足：您不是管理者');
                setIsAdmin(false);
                return;
            }

            if (!response.ok) {
                throw new Error('獲取用戶列表失敗');
            }

            const data = await response.json();
            if (data.success) {
                setUsers(data.users);
                setIsAdmin(true);
            }
        } catch (err) {
            setError('無法連接伺服器');
        } finally {
            setIsLoading(false);
        }
    }, [router]);

    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    // 顯示操作訊息
    const showMessage = (type: 'success' | 'error', text: string) => {
        setActionMessage({ type, text });
        setTimeout(() => setActionMessage(null), 3000);
    };

    // 切換用戶狀態
    const handleToggleStatus = async (user: User) => {
        const token = getToken();
        if (!token) return;

        setActionLoading(user.id);
        try {
            const response = await fetch(
                `http://localhost:8000/api/admin/user/${user.id}/toggle-status`,
                {
                    method: 'PUT',
                    headers: { 'Authorization': `Bearer ${token}` }
                }
            );
            const data = await response.json();

            if (data.success) {
                showMessage('success', data.message);
                fetchUsers();
            } else {
                showMessage('error', data.detail || '操作失敗');
            }
        } catch (err) {
            showMessage('error', '網路錯誤');
        } finally {
            setActionLoading(null);
            setOpenDropdown(null);
        }
    };

    // 修改用戶角色
    const handleChangeRole = async (user: User, newRole: string) => {
        const token = getToken();
        if (!token) return;

        setActionLoading(user.id);
        try {
            const response = await fetch(
                `http://localhost:8000/api/admin/user/${user.id}/role?new_role=${newRole}`,
                {
                    method: 'PUT',
                    headers: { 'Authorization': `Bearer ${token}` }
                }
            );
            const data = await response.json();

            if (data.success) {
                showMessage('success', data.message);
                fetchUsers();
            } else {
                showMessage('error', data.detail || '操作失敗');
            }
        } catch (err) {
            showMessage('error', '網路錯誤');
        } finally {
            setActionLoading(null);
            setOpenDropdown(null);
        }
    };

    // 刪除用戶
    const handleDeleteUser = async (user: User) => {
        const token = getToken();
        if (!token) return;

        setActionLoading(user.id);
        try {
            const response = await fetch(
                `http://localhost:8000/api/admin/user/${user.id}`,
                {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${token}` }
                }
            );
            const data = await response.json();

            if (data.success) {
                showMessage('success', data.message);
                fetchUsers();
            } else {
                showMessage('error', data.detail || '刪除失敗');
            }
        } catch (err) {
            showMessage('error', '網路錯誤');
        } finally {
            setActionLoading(null);
            setDeleteConfirmUser(null);
        }
    };

    // 重設密碼
    const handleResetPassword = async () => {
        if (!selectedUser || !newPassword) return;

        const token = getToken();
        if (!token) return;

        setIsResetting(true);
        try {
            const response = await fetch(
                `http://localhost:8000/api/admin/reset-password?target_user_id=${selectedUser.id}&new_password=${encodeURIComponent(newPassword)}`,
                {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                }
            );
            const data = await response.json();

            if (data.success) {
                showMessage('success', `已成功重設 ${selectedUser.username} 的密碼`);
                setNewPassword('');
                setSelectedUser(null);
            } else {
                showMessage('error', data.detail || '重設失敗');
            }
        } catch (err) {
            showMessage('error', '網路錯誤');
        } finally {
            setIsResetting(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-96">
                <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
            </div>
        );
    }

    if (!isAdmin) {
        return (
            <div className="flex flex-col items-center justify-center h-96 gap-4">
                <div className="p-4 bg-red-100 rounded-full">
                    <AlertTriangle className="w-12 h-12 text-red-500" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900">存取被拒絕</h2>
                <p className="text-gray-600">{error || '您沒有權限訪問此頁面'}</p>
                <button
                    onClick={() => router.push('/dashboard')}
                    className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                    返回儀表板
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 操作訊息 Toast */}
            {actionMessage && (
                <div className={cn(
                    "fixed top-4 right-4 z-50 px-6 py-3 rounded-xl shadow-lg flex items-center gap-2 animate-in slide-in-from-top duration-300",
                    actionMessage.type === 'success' ? "bg-green-500 text-white" : "bg-red-500 text-white"
                )}>
                    {actionMessage.type === 'success' ? <Check className="w-5 h-5" /> : <X className="w-5 h-5" />}
                    {actionMessage.text}
                </div>
            )}

            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl text-white shadow-lg">
                        <Shield className="w-6 h-6" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">帳號控管中心</h1>
                        <p className="text-sm text-gray-500">用戶管理、權限設定、密碼重設</p>
                    </div>
                </div>
                <button
                    onClick={fetchUsers}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    重新整理
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                            <Users className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-gray-900">{users.length}</p>
                            <p className="text-xs text-gray-500">總用戶數</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-100 rounded-lg">
                            <Crown className="w-5 h-5 text-purple-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-gray-900">{users.filter(u => u.role === 'admin').length}</p>
                            <p className="text-xs text-gray-500">管理員</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-green-100 rounded-lg">
                            <Check className="w-5 h-5 text-green-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-gray-900">{users.filter(u => u.is_active).length}</p>
                            <p className="text-xs text-gray-500">啟用中</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-red-100 rounded-lg">
                            <X className="w-5 h-5 text-red-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-gray-900">{users.filter(u => !u.is_active).length}</p>
                            <p className="text-xs text-gray-500">已停用</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* User Table */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="p-5 border-b border-gray-100 bg-gray-50/50">
                    <h2 className="font-bold text-gray-900 flex items-center gap-2">
                        <UserCog className="w-5 h-5 text-gray-600" />
                        帳號控管表
                    </h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50 text-xs uppercase text-gray-500 tracking-wider">
                            <tr>
                                <th className="px-6 py-3 text-left">ID</th>
                                <th className="px-6 py-3 text-left">用戶名稱</th>
                                <th className="px-6 py-3 text-left">Email</th>
                                <th className="px-6 py-3 text-left">角色</th>
                                <th className="px-6 py-3 text-left">帳號狀態</th>
                                <th className="px-6 py-3 text-left">註冊時間</th>
                                <th className="px-6 py-3 text-left">最後登入</th>
                                <th className="px-6 py-3 text-center">操作</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {users.map((user) => (
                                <tr key={user.id} className={cn(
                                    "hover:bg-gray-50 transition-colors",
                                    !user.is_active && "bg-red-50/30"
                                )}>
                                    <td className="px-6 py-4 text-sm text-gray-500">{user.id}</td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <div className={cn(
                                                "w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold uppercase",
                                                user.role === 'admin'
                                                    ? "bg-gradient-to-br from-purple-500 to-indigo-600"
                                                    : "bg-gradient-to-br from-blue-500 to-cyan-600"
                                            )}>
                                                {user.username.charAt(0)}
                                            </div>
                                            <div>
                                                <span className="font-medium text-gray-900">{user.username}</span>
                                                {user.id === currentUserId && (
                                                    <span className="ml-2 text-[10px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded-full font-bold">您</span>
                                                )}
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-600">{user.email || '-'}</td>
                                    <td className="px-6 py-4">
                                        <span className={cn(
                                            "px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider",
                                            user.role === 'admin'
                                                ? "bg-purple-100 text-purple-700"
                                                : "bg-gray-100 text-gray-600"
                                        )}>
                                            {user.role === 'admin' ? '👑 管理員' : '一般用戶'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        {user.is_active ? (
                                            <span className="flex items-center gap-1.5 text-green-600 text-xs font-bold">
                                                <ToggleRight className="w-4 h-4" /> 啟用中
                                            </span>
                                        ) : (
                                            <span className="flex items-center gap-1.5 text-red-500 text-xs font-bold">
                                                <ToggleLeft className="w-4 h-4" /> 已停用
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 text-xs text-gray-500">
                                        {user.created_at
                                            ? new Date(user.created_at).toLocaleDateString('zh-TW')
                                            : '-'}
                                    </td>
                                    <td className="px-6 py-4 text-xs text-gray-500">
                                        {user.last_login
                                            ? new Date(user.last_login).toLocaleString('zh-TW')
                                            : '從未登入'}
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <div className="relative inline-block">
                                            <button
                                                onClick={() => setOpenDropdown(openDropdown === user.id ? null : user.id)}
                                                disabled={actionLoading === user.id}
                                                className="inline-flex items-center gap-1 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200 transition-colors disabled:opacity-50"
                                            >
                                                {actionLoading === user.id ? (
                                                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                                ) : (
                                                    <>
                                                        操作 <ChevronDown className="w-3.5 h-3.5" />
                                                    </>
                                                )}
                                            </button>

                                            {openDropdown === user.id && (
                                                <div className="absolute right-0 mt-1 w-40 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden z-10 animate-in fade-in zoom-in duration-150">
                                                    <button
                                                        onClick={() => setSelectedUser(user)}
                                                        className="w-full px-4 py-2.5 text-left text-sm hover:bg-gray-50 flex items-center gap-2 text-gray-700"
                                                    >
                                                        <Key className="w-4 h-4" /> 重設密碼
                                                    </button>
                                                    <button
                                                        onClick={() => handleToggleStatus(user)}
                                                        className="w-full px-4 py-2.5 text-left text-sm hover:bg-gray-50 flex items-center gap-2 text-gray-700"
                                                    >
                                                        {user.is_active ? (
                                                            <><ToggleLeft className="w-4 h-4" /> 停用帳號</>
                                                        ) : (
                                                            <><ToggleRight className="w-4 h-4" /> 啟用帳號</>
                                                        )}
                                                    </button>
                                                    <button
                                                        onClick={() => handleChangeRole(user, user.role === 'admin' ? 'user' : 'admin')}
                                                        className="w-full px-4 py-2.5 text-left text-sm hover:bg-gray-50 flex items-center gap-2 text-gray-700"
                                                    >
                                                        <Crown className="w-4 h-4" />
                                                        {user.role === 'admin' ? '降為用戶' : '升為管理員'}
                                                    </button>
                                                    {user.id !== currentUserId && (
                                                        <button
                                                            onClick={() => {
                                                                setDeleteConfirmUser(user);
                                                                setOpenDropdown(null);
                                                            }}
                                                            className="w-full px-4 py-2.5 text-left text-sm hover:bg-red-50 flex items-center gap-2 text-red-600 border-t border-gray-100"
                                                        >
                                                            <Trash2 className="w-4 h-4" /> 刪除帳號
                                                        </button>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Reset Password Modal */}
            {selectedUser && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedUser(null)}>
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in zoom-in duration-200" onClick={e => e.stopPropagation()}>
                        <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
                            <div className="flex items-center gap-3">
                                <Key className="w-6 h-6" />
                                <div>
                                    <h3 className="font-bold text-lg">重設用戶密碼</h3>
                                    <p className="text-blue-100 text-sm">為 {selectedUser.username} 設定新密碼</p>
                                </div>
                            </div>
                        </div>

                        <div className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">新密碼</label>
                                <div className="relative">
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        placeholder="請輸入至少 6 個字元"
                                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none pr-12"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                    >
                                        {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="p-6 border-t border-gray-100 bg-gray-50 flex gap-3">
                            <button
                                onClick={() => {
                                    setSelectedUser(null);
                                    setNewPassword('');
                                }}
                                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-100 transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleResetPassword}
                                disabled={!newPassword || newPassword.length < 6 || isResetting}
                                className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            >
                                {isResetting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                                確認重設
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Confirm Modal */}
            {deleteConfirmUser && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setDeleteConfirmUser(null)}>
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden animate-in zoom-in duration-200" onClick={e => e.stopPropagation()}>
                        <div className="p-6 text-center">
                            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Trash2 className="w-8 h-8 text-red-500" />
                            </div>
                            <h3 className="text-xl font-bold text-gray-900 mb-2">確認刪除帳號？</h3>
                            <p className="text-gray-600 text-sm">
                                您確定要刪除用戶 <span className="font-bold text-red-600">{deleteConfirmUser.username}</span> 嗎？
                                此操作無法復原。
                            </p>
                        </div>
                        <div className="p-4 border-t border-gray-100 bg-gray-50 flex gap-3">
                            <button
                                onClick={() => setDeleteConfirmUser(null)}
                                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-100"
                            >
                                取消
                            </button>
                            <button
                                onClick={() => handleDeleteUser(deleteConfirmUser)}
                                disabled={actionLoading === deleteConfirmUser.id}
                                className="flex-1 px-4 py-2.5 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 flex items-center justify-center gap-2"
                            >
                                {actionLoading === deleteConfirmUser.id ? (
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Trash2 className="w-4 h-4" />
                                )}
                                確認刪除
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
