import { useState, useEffect, useCallback } from 'react';

export type ChartPayload = {
  chart_type: "bar" | "pie" | "line";
  title: string;
  data: { name: string; value: number }[];
  summary: string;
  timestamp: string;
};

const SSE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/sse/dashboard`
  : 'http://localhost:8000/sse/dashboard';

export const useSSE = () => {
  const [data, setData] = useState<ChartPayload | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // Callback to notify parent components when new data arrives
  const [onDataCallbacks, setOnDataCallbacks] = useState<Array<(payload: ChartPayload) => void>>([]);

  const onNewData = useCallback((cb: (payload: ChartPayload) => void) => {
    setOnDataCallbacks(prev => [...prev, cb]);
  }, []);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let retryCount = 0;
    const maxRetries = 5;

    const connect = () => {
      eventSource = new EventSource(SSE_URL);

      eventSource.onopen = () => {
        setConnected(true);
        setError(null);
        retryCount = 0; // Reset retries on successful connection
      };

      eventSource.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data) as ChartPayload;
          setData(parsedData);
          setLastUpdated(parsedData.timestamp || new Date().toISOString());
          // Notify all registered callbacks
          onDataCallbacks.forEach(cb => cb(parsedData));
        } catch (err) {
          console.error("Failed to parse SSE data", err);
        }
      };

      eventSource.onerror = () => {
        setConnected(false);
        setError("Connection lost. Reconnecting...");
        eventSource?.close();

        if (retryCount < maxRetries) {
          retryCount++;
          const timeout = Math.pow(2, retryCount) * 1000;
          setTimeout(connect, timeout);
        } else {
          setError("Max connection retries reached. Please check the server.");
        }
      };
    };

    connect();

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [onDataCallbacks]);

  return { data, connected, error, lastUpdated, onNewData };
};
