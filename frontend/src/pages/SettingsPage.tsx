import { useState } from 'react';
import { User, Bell, Shield, Palette, HardDrive, Key, Save, Server } from 'lucide-react';
import Card from '../components/common/Card';

export default function SettingsPage() {
  const [name, setName] = useState(localStorage.getItem('paypilot_user_name') || 'Demo User');
  const [email, setEmail] = useState(localStorage.getItem('paypilot_user_email') || 'demo@paypilot.ai');
  const [activeTab, setActiveTab] = useState('profile');
  const [saving, setSaving] = useState(false);

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'preferences', label: 'Preferences', icon: Palette },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'api', label: 'API & Integrations', icon: Key },
    { id: 'system', label: 'System Status', icon: Server },
  ];

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setTimeout(() => {
      localStorage.setItem('paypilot_user_name', name);
      localStorage.setItem('paypilot_user_email', email);
      setSaving(false);
      // Trigger a custom event to update the layout
      window.dispatchEvent(new Event('user-updated'));
    }, 800);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="animate-fade-in-up">
        <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Settings</h1>
        <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Manage your account and platform preferences</p>
      </div>

      <div className="flex flex-col md:flex-row gap-6 animate-fade-in-up delay-50">
        {/* Sidebar */}
        <div className="w-full md:w-64 flex-shrink-0 space-y-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === tab.id
                  ? 'bg-violet-500/10 text-violet-400'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'profile' && (
            <div className="space-y-5 animate-fade-in">
              <Card title="Personal Information" subtitle="Update your personal details">
                <form onSubmit={handleSave} className="space-y-4">
                  <div className="flex items-center gap-6 pb-6" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <div className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold text-white bg-gradient-to-br from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/20">
                      {name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <button type="button" className="btn-ghost text-xs">Change Avatar</button>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Full Name</label>
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="dark-input"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Email Address</label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="dark-input"
                        required
                      />
                    </div>
                  </div>
                  
                  <div className="pt-4 flex justify-end">
                    <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2 text-sm">
                      {saving ? (
                        <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                      ) : (
                        <Save className="w-4 h-4" />
                      )}
                      {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </form>
              </Card>

              <Card title="Business Details" subtitle="Information about your merchant account">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Business Name</label>
                    <input type="text" defaultValue="TechBazaar India" className="dark-input" disabled />
                  </div>
                  <div>
                    <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Merchant ID</label>
                    <div className="flex gap-2">
                      <input type="text" defaultValue={localStorage.getItem('paypilot_merchant_id') || 'mer_DEMO1234'} className="dark-input font-mono text-xs" disabled />
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {activeTab === 'preferences' && (
            <div className="space-y-5 animate-fade-in">
              <Card title="Display Preferences">
                <div className="settings-section">
                  <div className="settings-row">
                    <div>
                      <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Theme</p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Choose your preferred appearance</p>
                    </div>
                    <div className="flex bg-white/5 rounded-lg p-1 border border-white/10">
                      <button className="px-3 py-1.5 rounded-md text-xs bg-white/10 text-white shadow-sm">Dark</button>
                      <button className="px-3 py-1.5 rounded-md text-xs text-slate-400 hover:text-white">Light</button>
                      <button className="px-3 py-1.5 rounded-md text-xs text-slate-400 hover:text-white">System</button>
                    </div>
                  </div>
                  <div className="settings-row">
                    <div>
                      <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Default Currency</p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Format used across dashboards</p>
                    </div>
                    <select className="dark-input w-32 cursor-pointer">
                      <option value="INR">INR (₹)</option>
                      <option value="USD">USD ($)</option>
                    </select>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {activeTab === 'system' && (
            <div className="space-y-5 animate-fade-in">
              <Card title="System Status" subtitle="Platform health and connectivity">
                <div className="space-y-4">
                  {[
                    { name: 'API Server', status: 'Operational', ping: '12ms' },
                    { name: 'Database Engine', status: 'Operational', ping: '8ms' },
                    { name: 'AI Copilot Engine', status: 'Operational', ping: '340ms' },
                    { name: 'Anomaly Detection Job', status: 'Operational', ping: '-' },
                  ].map((service, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
                        <span className="text-sm font-medium text-slate-200">{service.name}</span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-slate-400">
                        <span>{service.status}</span>
                        {service.ping !== '-' && <span className="font-mono">{service.ping}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}
          
          {/* Placeholders for other tabs */}
          {['notifications', 'security', 'api'].includes(activeTab) && (
            <Card className="animate-fade-in">
              <div className="py-12 text-center">
                <HardDrive className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                <h3 className="text-base font-medium text-slate-300">Section Under Construction</h3>
                <p className="text-sm text-slate-500 mt-1">This settings area is not available in the demo.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
