import React, { useState, useEffect } from 'react';
import { useSSE } from './hooks/useSSE';
import type { ChartPayload } from './hooks/useSSE';
import { useSessions } from './hooks/useSessions';
import type { Session } from './hooks/useSessions';
import { ChartRenderer } from './components/ChartRenderer';

/** Formats ISO timestamp to readable format */
const formatTimestamp = (iso: string): string => {
  try {
    const date = new Date(iso);
    return date.toLocaleDateString('en-IN', {
      month: 'short',
      day: 'numeric',
    }) + ', ' + date.toLocaleTimeString('en-IN', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return iso;
  }
};

/** Chart type badge colors */
const chartTypeBadge: Record<string, { bg: string; text: string }> = {
  bar: { bg: 'rgba(0, 255, 136, 0.1)', text: '#00ff88' },
  pie: { bg: 'rgba(192, 132, 252, 0.1)', text: '#c084fc' },
  line: { bg: 'rgba(0, 204, 255, 0.1)', text: '#00ccff' },
};

function App() {
  const { data: liveData, connected, error } = useSSE();
  const { sessions, loading, deleteSession, refreshSessions } = useSessions();
  const [activePayload, setActivePayload] = useState<ChartPayload | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);

  // When new SSE data arrives, set it as active and refresh sessions
  useEffect(() => {
    if (liveData) {
      setActivePayload(liveData);
      setActiveSessionId(null); // Clear session selection — live data takes priority
      // Refresh session list since ui-server just persisted a new session
      const timer = setTimeout(() => refreshSessions(), 500);
      return () => clearTimeout(timer);
    }
  }, [liveData, refreshSessions]);

  // Click a session to load its chart
  const handleSessionClick = (session: Session) => {
    try {
      const parsedData = JSON.parse(session.data_json);
      setActivePayload({
        chart_type: session.chart_type,
        title: session.title,
        data: parsedData,
        summary: session.summary,
        timestamp: session.timestamp,
      });
      setActiveSessionId(session.id);
    } catch (err) {
      console.error('Failed to parse session data:', err);
    }
  };

  // Delete a session
  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation(); // Prevent session click
    await deleteSession(id);
    // If we deleted the active session, clear the chart
    if (activeSessionId === id) {
      setActivePayload(null);
      setActiveSessionId(null);
    }
  };

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--bg-primary)', fontFamily: 'var(--font-main)' }}>

      {/* ── Left Sidebar: Session History ── */}
      <aside 
        className="w-72 flex-shrink-0 flex flex-col border-r"
        style={{ 
          background: 'var(--bg-secondary)', 
          borderColor: 'var(--border-default)',
          height: '100vh',
          position: 'sticky',
          top: 0,
        }}
      >
        {/* Sidebar Header */}
        <div className="px-5 py-5 border-b" style={{ borderColor: 'var(--border-default)' }}>
          <h1 className="text-xl font-bold tracking-tight">
            <span className="gradient-text">FinFlow</span>
            <span className="ml-1" style={{ color: 'var(--text-secondary)' }}>MCP</span>
          </h1>
          <div className="flex items-center gap-2 mt-3">
            <div 
              className={`w-2 h-2 rounded-full ${connected ? 'animate-pulse-glow' : ''}`}
              style={{ backgroundColor: connected ? 'var(--accent)' : 'var(--danger)' }}
            />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {connected ? 'Connected to UI Bridge' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Session List */}
        <div className="px-3 pt-4 pb-2">
          <p className="text-[10px] font-semibold tracking-[0.15em] uppercase px-2 mb-3"
             style={{ color: 'var(--text-muted)' }}>
            Session History
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-5 h-5 border-2 rounded-full animate-spin"
                   style={{ borderColor: 'var(--border-default)', borderTopColor: 'var(--accent)' }} />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-12 px-4">
              <div className="w-10 h-10 mx-auto mb-3 rounded-xl flex items-center justify-center"
                   style={{ background: 'var(--accent-dim)' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" 
                     strokeWidth="1.5" style={{ color: 'var(--accent)' }}>
                  <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                No sessions yet
              </p>
              <p className="text-[10px] mt-1" style={{ color: 'var(--text-muted)', opacity: 0.6 }}>
                Ask Claude to visualize your expenses
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {sessions.map((session, index) => {
                const isActive = activeSessionId === session.id;
                const badge = chartTypeBadge[session.chart_type] || chartTypeBadge.bar;
                return (
                  <div
                    key={session.id}
                    onClick={() => handleSessionClick(session)}
                    className="group rounded-lg px-3 py-3 cursor-pointer transition-all duration-200 animate-fade-in"
                    style={{
                      animationDelay: `${index * 50}ms`,
                      animationFillMode: 'both',
                      background: isActive ? 'var(--accent-dim)' : 'transparent',
                      borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) e.currentTarget.style.background = 'var(--bg-card)';
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                          {session.title.length > 30 ? session.title.slice(0, 30) + '…' : session.title}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className="text-[10px] px-1.5 py-0.5 rounded-md font-medium"
                                style={{ background: badge.bg, color: badge.text }}>
                            {session.chart_type}
                          </span>
                          <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                            {formatTimestamp(session.timestamp)}
                          </span>
                        </div>
                      </div>

                      {/* Delete button */}
                      <button
                        onClick={(e) => handleDelete(e, session.id)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity duration-150 p-1 rounded-md hover:bg-red-500/10"
                        title="Delete session"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" 
                             strokeWidth="1.5" style={{ color: 'var(--danger)' }}>
                          <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" 
                                strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </aside>

      {/* ── Main Content Panel ── */}
      <main className="flex-1 flex flex-col min-h-screen">
        {/* Top Bar */}
        <header className="px-8 py-4 flex items-center justify-between border-b"
                style={{ borderColor: 'var(--border-default)' }}>
          <div>
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
              {activePayload ? activePayload.title : 'Dashboard'}
            </h2>
            {activePayload?.timestamp && (
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                Last updated: {formatTimestamp(activePayload.timestamp)}
              </p>
            )}
          </div>
          {error && !activePayload && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" 
                 style={{ background: 'rgba(255,68,102,0.1)' }}>
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--danger)' }} />
              <span className="text-xs" style={{ color: 'var(--danger)' }}>{error}</span>
            </div>
          )}
        </header>

        {/* Chart Content Area */}
        <div className="flex-1 p-8 flex items-center justify-center">
          {!activePayload ? (
            /* Empty State */
            <div className="text-center animate-fade-in-up">
              <div className="animate-float mb-6">
                <div className="w-20 h-20 mx-auto rounded-2xl flex items-center justify-center"
                     style={{ background: 'var(--accent-dim)', border: '1px solid var(--border-accent)' }}>
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" 
                       strokeWidth="1.5" style={{ color: 'var(--accent)' }}>
                    <path d="M13 10V3L4 14h7v7l9-11h-7z" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
              <p className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                Waiting for Claude...
              </p>
              <p className="text-sm max-w-xs mx-auto" style={{ color: 'var(--text-muted)' }}>
                Ask Claude to show your expense charts. Try: "Show me my spending by category for this month"
              </p>
            </div>
          ) : (
            /* Chart + Summary */
            <div className="w-full max-w-4xl glass-accent rounded-2xl p-8 animate-fade-in-up"
                 style={{ boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}>
              <ChartRenderer payload={activePayload} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
