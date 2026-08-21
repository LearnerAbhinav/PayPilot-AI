import { useState, useRef, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { sendMessage, getConversations, createConversation, getAIInfo } from '../api/ai';
import type { AIInfoResponse } from '../api/ai';
import {
  startInvestigation,
  streamInvestigationWithAuth,
  getInvestigations,
  getInvestigation,
  runMonitoringCycle,
} from '../api/investigations';
import type { AgentStreamEvent, InvestigationResponse, InvestigationEvent } from '../api/investigations';
import type { ConversationResponse } from '../types';
import {
  Send, Bot, Loader2, Sparkles, Plus, MessageSquare,
  ChevronRight, Zap, AlertTriangle, CheckCircle2, Clock,
  Activity, Search, Terminal, TrendingDown, ArrowRight, ShieldCheck,
  RefreshCw, Layers, Check
} from 'lucide-react';
import { cn, formatDateTime, formatCurrency, relativeTime } from '../lib/utils';
import ReactMarkdown from 'react-markdown';

// ─── Types ──────────────────────────────────────────────────────────────────

interface AgentStep {
  id: string;
  type: 'tool_start' | 'tool_end' | 'finding' | 'error' | 'started';
  tool?: string;
  stage?: string;
  label?: string;
  summary?: string;
  duration_ms?: number;
  success?: boolean;
  timestamp: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tools_called?: Array<{ tool_name: string; round: number }>;
  agent_steps?: AgentStep[];
  investigation_id?: string;
  is_streaming?: boolean;
  created_at: string;
}

// ─── Investigation Stage Timeline ──────────────────────────────────────────

function InvestigationTimeline({ steps }: { steps: AgentStep[] }) {
  const [expanded, setExpanded] = useState(true);

  if (!steps.length) return null;

  const completedTools = steps.filter(s => s.type === 'tool_end' || (s.type === 'tool_start' && s.success !== undefined));
  const activeStep = steps.find(
    s => s.type === 'tool_start' && !steps.find(ss => ss.type === 'tool_end' && ss.tool === s.tool)
  );

  return (
    <div className="investigation-timeline-card">
      <div
        className="timeline-header"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Terminal size={13} className="text-violet-400" />
          <span className="font-semibold text-xs text-slate-200">
            Investigation Evidence Timeline
          </span>
          <span className="text-[11px] text-slate-400">
            ({completedTools.length || steps.length} stages executed)
          </span>
        </div>
        <div className="flex items-center gap-2">
          {activeStep && (
            <span className="flex items-center gap-1 text-[11px] text-violet-300 animate-pulse">
              <Loader2 size={11} className="animate-spin" />
              {activeStep.label || 'Analyzing...'}
            </span>
          )}
          <ChevronRight size={13} className={cn("text-slate-400 transition-transform duration-200", expanded && "rotate-90")} />
        </div>
      </div>

      {expanded && (
        <div className="timeline-body">
          {steps.map((step, idx) => {
            if (step.type === 'started') return null;

            if (step.type === 'tool_start') {
              const isDone = steps.some(s => s.type === 'tool_end' && s.tool === step.tool);
              if (isDone) return null; // Only show active starts
              return (
                <div key={step.id || idx} className="timeline-stage timeline-stage-running">
                  <div className="stage-indicator">
                    <Loader2 size={11} className="animate-spin text-violet-400" />
                  </div>
                  <div className="stage-content">
                    <div className="stage-name">{step.stage || step.tool}</div>
                    <div className="stage-detail text-violet-300">{step.label || 'Executing telemetry query...'}</div>
                  </div>
                </div>
              );
            }

            if (step.type === 'tool_end' || step.summary) {
              const isSuccess = step.success !== false;
              return (
                <div key={step.id || idx} className="timeline-stage timeline-stage-done">
                  <div className="stage-indicator">
                    {isSuccess ? (
                      <CheckCircle2 size={12} className="text-emerald-400" />
                    ) : (
                      <AlertTriangle size={12} className="text-amber-400" />
                    )}
                  </div>
                  <div className="stage-content">
                    <div className="flex items-center justify-between">
                      <span className="stage-name">{step.stage || step.tool || `Stage ${idx + 1}`}</span>
                      {step.duration_ms != null && (
                        <span className="stage-duration">{step.duration_ms}ms</span>
                      )}
                    </div>
                    <div className="stage-summary">{step.summary || step.label || 'Completed successfully'}</div>
                  </div>
                </div>
              );
            }

            if (step.type === 'error') {
              return (
                <div key={step.id || idx} className="timeline-stage timeline-stage-error">
                  <div className="stage-indicator">
                    <AlertTriangle size={12} className="text-red-400" />
                  </div>
                  <div className="stage-content">
                    <div className="stage-name text-red-400">Analysis Halted</div>
                    <div className="stage-summary text-red-300">{step.summary || 'Rate limit or connection issue'}</div>
                  </div>
                </div>
              );
            }

            return null;
          })}
        </div>
      )}
    </div>
  );
}

// ─── Evidence Provenance Breakdown Card ─────────────────────────────────────

function EvidenceProvenanceCard({ inv }: { inv: InvestigationResponse }) {
  if (!inv.supporting_evidence?.length && !inv.financial_impact?.recoverable_amount) return null;

  return (
    <div 
      className="mb-3 p-4 border rounded-xl space-y-3 shadow-sm transition-all"
      style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}
    >
      <div className="flex items-center justify-between border-b pb-2.5" style={{ borderColor: 'var(--border-subtle)' }}>
        <div className="flex items-center gap-2">
          <Layers size={14} className="text-violet-600 dark:text-violet-400" />
          <span className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--text-primary)' }}>
            Deterministic Evidence Provenance
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
            {inv.classification || 'CONFIRMED'} • {inv.confidence_score || 92}% Confidence
          </span>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {inv.financial_impact?.revenue_gap != null && (
          <div 
            className="p-2.5 rounded-lg border"
            style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] uppercase block font-semibold" style={{ color: 'var(--text-muted)' }}>Revenue Gap</span>
            <span className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>
              {formatCurrency(inv.financial_impact.revenue_gap)}
            </span>
          </div>
        )}
        {inv.financial_impact?.unrealized_revenue != null && (
          <div 
            className="p-2.5 rounded-lg border"
            style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] uppercase block font-semibold" style={{ color: 'var(--text-muted)' }}>Unrealized Volume</span>
            <span className="text-xs font-bold text-amber-600 dark:text-amber-400">
              {formatCurrency(inv.financial_impact.unrealized_revenue)}
            </span>
          </div>
        )}
        {inv.recovery_opportunity?.eligible_transactions != null && (
          <div 
            className="p-2.5 rounded-lg border"
            style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] uppercase block font-semibold" style={{ color: 'var(--text-muted)' }}>Policy Eligible</span>
            <span className="text-xs font-bold text-violet-700 dark:text-violet-300">
              {inv.recovery_opportunity.eligible_transactions} txns
            </span>
          </div>
        )}
        {inv.recovery_opportunity?.recoverable_amount != null && (
          <div 
            className="p-2.5 rounded-lg border"
            style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-subtle)' }}
          >
            <span className="text-[10px] uppercase block font-semibold" style={{ color: 'var(--text-muted)' }}>Recoverable (70%)</span>
            <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
              {formatCurrency(inv.recovery_opportunity.recoverable_amount)}
            </span>
          </div>
        )}
      </div>

      {/* Supporting & Contradictory Evidence */}
      <div className="space-y-2 pt-1">
        {inv.supporting_evidence?.map((item, i) => (
          <div key={i} className="flex items-start gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <Check size={12} className="text-emerald-500 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{item.claim}</span>
              {item.value && <span className="ml-1" style={{ color: 'var(--text-muted)' }}>({item.value})</span>}
              <span className="text-[10px] text-violet-600 dark:text-violet-400 ml-1.5 font-mono">[{item.source_tool}]</span>
            </div>
          </div>
        ))}
        {inv.contradictory_evidence?.map((item, i) => (
          <div key={i} className="flex items-start gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <AlertTriangle size={12} className="text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{item.claim}</span>
              {item.counter_indicator && <span className="ml-1" style={{ color: 'var(--text-muted)' }}>— {item.counter_indicator}</span>}
              <span className="text-[10px] ml-1.5 font-mono" style={{ color: 'var(--text-muted)' }}>[{item.source_tool}]</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function InvestigationBadge({ status }: { status: string; severity?: string }) {
  const config: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    STARTED: { label: 'Starting', color: 'badge-blue', icon: <Clock size={10} /> },
    ANALYZING: { label: 'Investigating', color: 'badge-purple', icon: <Loader2 size={10} className="animate-spin" /> },
    FINDINGS_READY: { label: 'Completed', color: 'badge-green', icon: <CheckCircle2 size={10} /> },
    ACTION_PROPOSED: { label: 'Action Proposed', color: 'badge-amber', icon: <Zap size={10} /> },
    CLOSED: { label: 'Closed', color: 'badge-gray', icon: <CheckCircle2 size={10} /> },
    AI_FAILED: { label: 'Investigation Failed', color: 'badge-red', icon: <AlertTriangle size={10} /> },
  };
  const cfg = config[status] || config.STARTED;
  return (
    <span className={cn("investigation-badge", cfg.color)}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function CopilotPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const investigationIdParam = searchParams.get('id');
  const initialMessage = searchParams.get('msg');
  const autoInvestigate = searchParams.get('investigate') === '1';
  const navigate = useNavigate();

  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [activeConversation, setActiveConversation] = useState<string | null>(null);
  const [activeInvestigation, setActiveInvestigation] = useState<InvestigationResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState(initialMessage || '');
  const [loading, setLoading] = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [investigations, setInvestigations] = useState<InvestigationResponse[]>([]);
  const [activeTab, setActiveTab] = useState<'investigations' | 'chat'>('investigations');
  const [aiInfo, setAiInfo] = useState<AIInfoResponse | null>(null);
  const [triggeringScan, setTriggeringScan] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadConversations();
    loadInvestigations();
    getAIInfo().then(setAiInfo).catch(() => {});
  }, []);

  // Load specific investigation from URL parameter or default to the most recent one
  useEffect(() => {
    if (investigationIdParam) {
      handleSelectInvestigation(investigationIdParam);
    } else if (investigations.length > 0 && !activeInvestigation && !activeConversation) {
      handleSelectInvestigation(investigations[0].id);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [investigationIdParam, investigations.length]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (initialMessage && autoInvestigate) {
      handleSend(undefined, initialMessage);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadConversations = async () => {
    try {
      const data = await getConversations();
      setConversations((data as unknown as ConversationResponse[]) || []);
    } catch { /* silent */ }
  };

  const loadInvestigations = async () => {
    try {
      const data = await getInvestigations();
      setInvestigations(data || []);
    } catch { /* silent */ }
  };

  const handleSelectInvestigation = async (invId: string) => {
    setLoading(true);
    setSearchParams({ id: invId });
    try {
      const inv = await getInvestigation(invId);
      setActiveInvestigation(inv);
      setActiveConversation(inv.conversation_id || null);

      // Reconstruct Timeline Steps from persisted events
      const steps: AgentStep[] = [];
      if (inv.events && Array.isArray(inv.events)) {
        inv.events.forEach((ev: InvestigationEvent, i: number) => {
          steps.push({
            id: `persisted-${i}`,
            type: 'tool_end',
            tool: ev.tool_name,
            stage: ev.stage,
            label: ev.label,
            summary: ev.summary,
            duration_ms: ev.duration_ms,
            success: ev.status === 'completed',
            timestamp: ev.end_time || ev.start_time || new Date().toISOString(),
          });
        });
      }

      // Reconstruct Messages
      if (inv.messages && inv.messages.length > 0) {
        setMessages(inv.messages.map(m => ({
          id: m.id,
          role: m.role,
          content: m.content,
          tools_called: m.tools_called,
          agent_steps: m.role === 'assistant' ? steps : undefined,
          investigation_id: inv.id,
          created_at: m.created_at,
        })));
      } else if (inv.agent_summary) {
        setMessages([
          {
            id: `user-req-${inv.id}`,
            role: 'user',
            content: inv.user_request || `Autonomous investigation for ${inv.title}`,
            created_at: inv.created_at,
          },
          {
            id: `assistant-res-${inv.id}`,
            role: 'assistant',
            content: inv.agent_summary,
            agent_steps: steps,
            investigation_id: inv.id,
            created_at: inv.updated_at || inv.created_at,
          }
        ]);
      } else {
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to load investigation:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = async () => {
    try {
      const conv = await createConversation('Investigation Session') as unknown as ConversationResponse;
      setConversations([conv, ...conversations]);
      setActiveConversation(conv.id);
      setActiveInvestigation(null);
      setMessages([]);
      setInput('');
      setSearchParams({});
      inputRef.current?.focus();
    } catch { /* silent */ }
  };

  const handleTriggerAutonomousScan = async () => {
    setTriggeringScan(true);
    try {
      await runMonitoringCycle();
      await loadInvestigations();
      if (investigations.length > 0) {
        handleSelectInvestigation(investigations[0].id);
      }
    } catch (err) {
      console.error('Failed to run monitoring scan:', err);
    } finally {
      setTriggeringScan(false);
    }
  };

  const handleSend = useCallback(async (e?: React.FormEvent, customMsg?: string) => {
    if (e) e.preventDefault();
    const userMsg = (customMsg || input).trim();
    if (!userMsg || loading) return;

    setInput('');
    setLoading(true);

    const userMsgId = Date.now().toString();
    const assistantMsgId = (Date.now() + 1).toString();

    setMessages(prev => [...prev, {
      id: userMsgId,
      role: 'user',
      content: userMsg,
      created_at: new Date().toISOString(),
    }]);

    setMessages(prev => [...prev, {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      is_streaming: true,
      agent_steps: [],
      created_at: new Date().toISOString(),
    }]);

    try {
      let invId: string | null = null;
      let convId: string | null = activeConversation;

      try {
        const inv = await startInvestigation({ message: userMsg });
        invId = inv.id;
        convId = inv.conversation_id;
        setActiveConversation(convId);
        setStreamingId(invId);
        setSearchParams({ id: invId });
      } catch { /* fallback */ }

      if (invId) {
        await streamInvestigationWithAuth(
          invId,
          (event: AgentStreamEvent) => {
            setMessages(prev => prev.map(m => {
              if (m.id !== assistantMsgId) return m;
              const steps = m.agent_steps ? [...m.agent_steps] : [];

              if (event.type === 'tool_start') {
                steps.push({
                  id: `${Date.now()}-start`,
                  type: 'tool_start',
                  tool: String(event.data.tool ?? ''),
                  stage: String(event.data.stage ?? ''),
                  label: String(event.data.label ?? ''),
                  timestamp: new Date().toISOString(),
                });
              } else if (event.type === 'tool_end') {
                steps.push({
                  id: `${Date.now()}-end`,
                  type: 'tool_end',
                  tool: String(event.data.tool ?? ''),
                  stage: String(event.data.stage ?? ''),
                  summary: String(event.data.summary ?? ''),
                  duration_ms: typeof event.data.duration_ms === 'number' ? event.data.duration_ms : undefined,
                  success: Boolean(event.data.success),
                  timestamp: new Date().toISOString(),
                });
              } else if (event.type === 'complete') {
                return {
                  ...m,
                  content: String(event.data.content ?? ''),
                  agent_steps: steps,
                  tools_called: (event.data.tool_calls as Array<{ tool_name: string; round: number }>) || [],
                  investigation_id: invId || undefined,
                  is_streaming: false,
                };
              } else if (event.type === 'error') {
                return {
                  ...m,
                  content: `⚠️ Investigation note: ${String(event.data.message ?? 'Rate limit reached')}`,
                  agent_steps: steps,
                  is_streaming: false,
                };
              }

              return { ...m, agent_steps: steps };
            }));
          },
          () => {
            setLoading(false);
            setStreamingId(null);
            loadInvestigations();
            if (invId) {
              getInvestigation(invId).then(setActiveInvestigation).catch(() => {});
            }
          },
          (err: string) => {
            fallbackToChat(assistantMsgId, userMsg, convId);
            console.warn('SSE stream failed, falling back:', err);
          }
        );
      } else {
        await fallbackToChat(assistantMsgId, userMsg, convId);
      }
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === assistantMsgId
          ? { ...m, content: '❌ Something went wrong. Please try again.', is_streaming: false }
          : m
      ));
      setLoading(false);
      setStreamingId(null);
    }
  }, [input, loading, activeConversation]);

  const fallbackToChat = async (
    assistantMsgId: string,
    userMsg: string,
    convId: string | null
  ) => {
    try {
      const result = await sendMessage(userMsg, convId) as any;
      const content = result?.message?.content || result?.content || 'Analysis complete.';
      setMessages(prev => prev.map(m =>
        m.id === assistantMsgId
          ? { ...m, content, tools_called: result?.tools_called, is_streaming: false }
          : m
      ));
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === assistantMsgId
          ? { ...m, content: '❌ Unable to complete analysis. Please verify your connection.', is_streaming: false }
          : m
      ));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickPrompts = [
    { icon: <TrendingDown size={14} />, text: "Investigate this revenue drop — decompose Volume, ATV & Success Rate", color: "quick-blue" },
    { icon: <Activity size={14} />, text: "Analyze payment method health and failure rate surges", color: "quick-purple" },
    { icon: <Zap size={14} />, text: "Calculate recoverable revenue and evaluate Smart Retry policy", color: "quick-green" },
    { icon: <AlertTriangle size={14} />, text: "Run root-cause analysis on recent anomaly signals", color: "quick-amber" },
  ];

  return (
    <div className="copilot-layout">
      {/* Sidebar */}
      <aside className="copilot-sidebar">
        <div className="copilot-sidebar-header">
          <div className="copilot-brand">
            <div className="copilot-brand-icon">
              <Bot size={18} />
            </div>
            <div>
              <div className="copilot-brand-name">PayPilot AI</div>
              <div className="copilot-brand-sub">Autonomous Operations</div>
            </div>
          </div>
          <button className="copilot-new-btn" onClick={handleNewConversation} title="New Session">
            <Plus size={16} />
          </button>
        </div>

        <div className="copilot-tab-row">
          <button
            className={cn("copilot-tab", activeTab === 'investigations' && "copilot-tab-active")}
            onClick={() => { setActiveTab('investigations'); loadInvestigations(); }}
          >
            <Search size={13} /> Investigations {investigations.length > 0 && <span className="tab-count">{investigations.length}</span>}
          </button>
          <button
            className={cn("copilot-tab", activeTab === 'chat' && "copilot-tab-active")}
            onClick={() => setActiveTab('chat')}
          >
            <MessageSquare size={13} /> Sessions
          </button>
        </div>

        {activeTab === 'investigations' && (
          <div className="copilot-conv-list">
            <div className="p-2 border-b border-white/5">
              <button
                onClick={handleTriggerAutonomousScan}
                disabled={triggeringScan}
                className="w-full py-1.5 px-2.5 bg-violet-600/20 hover:bg-violet-600/30 border border-violet-500/30 rounded-lg text-xs font-semibold text-violet-300 flex items-center justify-center gap-1.5 transition-all"
              >
                {triggeringScan ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                {triggeringScan ? 'Scanning Telemetry...' : 'Run Monitoring Scan'}
              </button>
            </div>

            {investigations.length === 0 && (
              <div className="copilot-empty-state">
                <Search size={24} className="opacity-30 mx-auto mb-2" />
                <p className="text-xs text-muted">No investigations yet</p>
                <p className="text-[11px] text-slate-500 mt-1">Run a scan to detect anomalies</p>
              </div>
            )}
            {investigations.map(inv => (
              <button
                key={inv.id}
                onClick={() => handleSelectInvestigation(inv.id)}
                className={cn(
                  "investigation-sidebar-item text-left w-full transition-all",
                  activeInvestigation?.id === inv.id && "investigation-sidebar-active border-l-2 border-l-violet-500 bg-violet-500/10"
                )}
              >
                <div className="inv-sidebar-top">
                  <span className="inv-sidebar-title font-semibold">{inv.title}</span>
                  <InvestigationBadge status={inv.status} severity={inv.severity} />
                </div>
                {inv.financial_impact?.recoverable_amount != null && inv.financial_impact.recoverable_amount > 0 && (
                  <div className="inv-sidebar-amount">
                    ₹{inv.financial_impact.recoverable_amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })} recoverable
                  </div>
                )}
                <div className="inv-sidebar-time">{relativeTime(inv.created_at)}</div>
              </button>
            ))}
          </div>
        )}

        {activeTab === 'chat' && (
          <div className="copilot-conv-list">
            {conversations.length === 0 && (
              <div className="copilot-empty-state">
                <MessageSquare size={24} className="opacity-30 mx-auto mb-2" />
                <p className="text-xs text-muted">Start a new session</p>
              </div>
            )}
            {conversations.map(conv => (
              <button
                key={conv.id}
                className={cn("copilot-conv-item", activeConversation === conv.id && "copilot-conv-active")}
                onClick={() => {
                  setActiveConversation(conv.id);
                  setActiveInvestigation(null);
                  setSearchParams({});
                }}
              >
                <MessageSquare size={13} />
                <span>{conv.title || 'Investigation Session'}</span>
              </button>
            ))}
          </div>
        )}
      </aside>

      {/* Main Chat Area */}
      <main className="copilot-main">
        {/* Header */}
        <div className="copilot-main-header">
          <div className="copilot-header-left">
            <Sparkles size={18} className="text-violet-400" />
            <div>
              <div className="copilot-header-title">
                {activeInvestigation?.title || (streamingId ? 'Decomposing Telemetry & Investigating...' : 'PayPilot Autonomous AI')}
              </div>
              {activeInvestigation && (
                <div className="text-[11px] text-slate-400 flex items-center gap-2">
                  <span>ID: {activeInvestigation.id.slice(0, 8)}…</span>
                  <span>•</span>
                  <span>{formatDateTime(activeInvestigation.created_at)}</span>
                  <span>•</span>
                  <InvestigationBadge status={activeInvestigation.status} />
                </div>
              )}
            </div>
            {streamingId && (
              <span className="copilot-streaming-indicator">
                <span className="streaming-dot" />
                <span className="streaming-dot animation-delay-200" />
                <span className="streaming-dot animation-delay-400" />
              </span>
            )}
          </div>
          <div className="copilot-header-right">
            <div className="copilot-status-badge">
              <span className="status-dot status-dot-green" />
              {aiInfo ? `${aiInfo.provider} / ${aiInfo.model} • ${aiInfo.tools_count} Tools` : 'Groq / Active Engine'}
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="copilot-messages">
          {activeInvestigation && (
            <EvidenceProvenanceCard inv={activeInvestigation} />
          )}

          {messages.length === 0 && !activeInvestigation && (
            <div className="copilot-welcome">
              <div className="copilot-welcome-icon">
                <Bot size={40} />
              </div>
              <h2 className="copilot-welcome-title">PayPilot AI</h2>
              <p className="copilot-welcome-subtitle">
                Autonomous financial operations agent. Evaluates telemetry, investigates payment anomalies,
                quantifies financial impact, and creates recovery proposals for the Action Center.
              </p>
              <div className="quick-prompt-grid">
                {quickPrompts.map((qp, i) => (
                  <button
                    key={i}
                    className={cn("quick-prompt-btn", qp.color)}
                    onClick={() => handleSend(undefined, qp.text)}
                  >
                    {qp.icon}
                    <span>{qp.text}</span>
                    <ChevronRight size={13} className="ml-auto opacity-50" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={cn("message-wrapper", msg.role === 'user' ? "message-user" : "message-assistant")}>
              <div className="message-avatar">
                {msg.role === 'user'
                  ? <div className="avatar-user">U</div>
                  : <div className="avatar-bot"><Bot size={14} /></div>}
              </div>
              <div className="message-body">
                {msg.role === 'assistant' && msg.agent_steps && msg.agent_steps.length > 0 && (
                  <InvestigationTimeline steps={msg.agent_steps} />
                )}

                {msg.is_streaming && !msg.content ? (
                  <div className="message-streaming">
                    <Loader2 size={14} className="animate-spin" />
                    <span>Decomposing financial metrics and evaluating telemetry...</span>
                  </div>
                ) : (
                  <div className="message-content">
                    {msg.role === 'assistant' ? (
                      <div className="prose-sm">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p>{msg.content}</p>
                    )}
                  </div>
                )}

                {msg.role === 'assistant' && (msg.content.includes('Action') || activeInvestigation?.action_id) && (
                  <div 
                    className="p-3.5 border rounded-xl flex items-center justify-between gap-4 mt-2 shadow-sm transition-all"
                    style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-default)' }}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center flex-shrink-0 text-violet-600 dark:text-violet-400">
                        <ShieldCheck size={18} />
                      </div>
                      <div>
                        <div className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Recovery Action Ready in Action Center</div>
                        <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>Human-in-the-loop authorization required before simulation execution</div>
                      </div>
                    </div>
                    <button
                      onClick={() => navigate('/actions')}
                      className="px-3.5 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md shadow-violet-600/20 hover:scale-[1.02] flex-shrink-0"
                    >
                      Review in Actions <ArrowRight size={12} />
                    </button>
                  </div>
                )}

                {msg.investigation_id && (
                  <div className="message-investigation-link">
                    <Search size={11} />
                    <span>Investigation ID:</span>
                    <span className="inv-id-chip">{msg.investigation_id.slice(0, 8)}…</span>
                  </div>
                )}

                <div className="message-meta">{formatDateTime(msg.created_at)}</div>
              </div>
            </div>
          ))}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="copilot-input-area">
          <form onSubmit={handleSend} className="copilot-input-form">
            <textarea
              ref={inputRef}
              className="copilot-textarea"
              placeholder="Ask PayPilot AI to decompose a revenue drop, investigate payment anomalies, or calculate recoverable revenue…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={loading}
            />
            <button
              type="submit"
              className={cn("copilot-send-btn", loading && "copilot-send-disabled")}
              disabled={loading || !input.trim()}
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            </button>
          </form>
          <p className="copilot-disclaimer">
            ⚠️ SIMULATION MODE — Evaluates real transaction datasets against deterministic policies. No real money moved.
          </p>
        </div>
      </main>
    </div>
  );
}
