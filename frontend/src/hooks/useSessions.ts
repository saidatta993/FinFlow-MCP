import { useState, useEffect, useCallback } from 'react';

export type Session = {
  id: number;
  timestamp: string;
  query: string;
  chart_type: "bar" | "pie" | "line";
  title: string;
  data_json: string;
  summary: string;
};

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useSessions = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteSession = useCallback(async (id: number) => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.id !== id));
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  }, []);

  // Fetch sessions on mount
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return { sessions, loading, deleteSession, refreshSessions: fetchSessions };
};
