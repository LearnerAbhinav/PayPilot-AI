import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Eye, EyeOff, ArrowRight, Lock, Mail, User } from 'lucide-react';
import { login, register } from '../api/auth';

const SUGGESTIONS = [
  'Revenue trends & insights',
  'Real-time anomaly detection',
  'AI-powered cash flow forecast',
  'Autonomous payment recovery',
];

export default function LoginPage() {
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = isRegister
        ? await register(name, email, password)
        : await login(email, password);
      localStorage.setItem('paypilot_token', response.access_token);
      localStorage.setItem('paypilot_user_id', response.user_id);
      localStorage.setItem('paypilot_merchant_id', response.merchant_id || '');
      localStorage.setItem('paypilot_user_name', name || email.split('@')[0]);
      localStorage.setItem('paypilot_user_email', email);
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = () => {
    setEmail('demo@paypilot.ai');
    setPassword('demo123');
    setIsRegister(false);
  };

  return (
    <div
      className="min-h-screen flex"
      style={{ background: 'var(--bg-base)' }}
    >
      {/* Left panel — brand */}
      <div
        className="hidden lg:flex lg:w-[52%] flex-col justify-between p-12 relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #07070d 0%, #0e0818 60%, #110d25 100%)' }}
      >
        {/* Radial glows */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `
              radial-gradient(ellipse at 25% 40%, rgba(124,58,237,0.18) 0%, transparent 55%),
              radial-gradient(ellipse at 75% 70%, rgba(79,70,229,0.12) 0%, transparent 50%),
              radial-gradient(ellipse at 50% 10%, rgba(6,182,212,0.07) 0%, transparent 45%)
            `,
          }}
        />

        {/* Grid overlay */}
        <div
          className="absolute inset-0 pointer-events-none opacity-20"
          style={{
            backgroundImage: `linear-gradient(rgba(124,58,237,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(124,58,237,0.08) 1px, transparent 1px)`,
            backgroundSize: '48px 48px',
          }}
        />

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center animate-pulse-glow"
            style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
          >
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold gradient-text">PayPilot AI</span>
        </div>

        {/* Hero content */}
        <div className="relative z-10">
          <h1 className="text-4xl font-bold leading-tight mb-4" style={{ color: 'var(--text-primary)' }}>
            Autonomous Financial
            <br />
            <span className="gradient-text">Intelligence</span>
          </h1>
          <p className="text-sm leading-relaxed mb-8" style={{ color: 'var(--text-secondary)' }}>
            Real-time payment analytics, AI-powered anomaly detection, and autonomous recovery — built for Indian merchants.
          </p>

          <div className="space-y-3">
            {SUGGESTIONS.map((s, i) => (
              <div
                key={s}
                className="flex items-center gap-3 animate-fade-in-up"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <div
                  className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ background: 'rgba(124,58,237,0.2)', border: '1px solid rgba(124,58,237,0.3)' }}
                >
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#7c3aed' }} />
                </div>
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{s}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom badge */}
        <div className="relative z-10">
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
            style={{
              background: 'rgba(124,58,237,0.1)',
              border: '1px solid rgba(124,58,237,0.2)',
              color: 'var(--text-secondary)',
            }}
          >
            <span className="live-dot">
              <span className="status-dot captured" />
            </span>
            Processing ₹1.2Cr+ in demo transactions
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 relative">
        {/* Mobile logo */}
        <div className="lg:hidden mb-8 flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
          >
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold gradient-text">PayPilot AI</span>
        </div>

        <div className="w-full max-w-sm animate-fade-in-up">
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
              {isRegister ? 'Create account' : 'Welcome back'}
            </h2>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {isRegister ? 'Start your free dashboard' : 'Sign in to your dashboard'}
            </p>
          </div>

          {/* Demo shortcut */}
          {!isRegister && (
            <button
              type="button"
              onClick={handleDemoLogin}
              className="w-full mb-5 py-2.5 px-4 rounded-lg text-sm font-medium transition-all hover:brightness-110"
              style={{
                background: 'rgba(124,58,237,0.08)',
                border: '1px solid rgba(124,58,237,0.2)',
                color: '#a78bfa',
              }}
            >
              ⚡ Use demo credentials
            </button>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div className="gradient-border rounded-lg">
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none z-10" style={{ color: 'var(--text-muted)' }} />
                  <input
                    id="name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="dark-input has-icon-left"
                    style={{ paddingLeft: '44px' }}
                    placeholder="Full name"
                  />
                </div>
              </div>
            )}

            <div className="gradient-border rounded-lg">
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none z-10" style={{ color: 'var(--text-muted)' }} />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="dark-input has-icon-left"
                  style={{ paddingLeft: '44px' }}
                  placeholder="Email address"
                />
              </div>
            </div>

            <div className="gradient-border rounded-lg">
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none z-10" style={{ color: 'var(--text-muted)' }} />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={isRegister ? 8 : 1}
                  className="dark-input has-icon-left has-icon-right"
                  style={{ paddingLeft: '44px', paddingRight: '44px' }}
                  placeholder="Password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 transition-colors z-10 cursor-pointer p-1"
                  style={{ color: 'var(--text-muted)' }}
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div
                className="flex items-start gap-2.5 px-3.5 py-3 rounded-lg text-sm animate-fade-in"
                style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}
              >
                <span className="text-red-400 mt-0.5">⚠</span>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-4 h-4 rounded-full" style={{ border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', animation: 'spin 0.7s linear infinite' }} />
              ) : (
                <>
                  {isRegister ? 'Create Account' : 'Sign In'}
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
            {isRegister ? 'Already have an account? ' : "Don't have an account? "}
            <button
              onClick={() => { setIsRegister(!isRegister); setError(''); }}
              className="font-semibold transition-colors hover:text-violet-300"
              style={{ color: '#a78bfa' }}
            >
              {isRegister ? 'Sign in' : 'Register'}
            </button>
          </p>

          {!isRegister && (
            <p className="mt-4 text-center text-xs" style={{ color: 'var(--text-muted)' }}>
              Demo: <span style={{ color: 'var(--text-secondary)' }}>demo@paypilot.ai</span>{' '}
              / <span style={{ color: 'var(--text-secondary)' }}>demo123</span>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
