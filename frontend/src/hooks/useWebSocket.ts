import { useState, useEffect, useCallback } from 'react';

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000];
const PING_INTERVAL = 30000;

interface WSMessage {
  type: string;
  data?: unknown;
}

type Listener = (message: WSMessage | null) => void;

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let pingTimer: ReturnType<typeof setInterval> | null = null;
let reconnectAttempt = 0;
const listeners = new Set<Listener>();
let globalReadyState: number = WebSocket.CLOSED;
let globalLastMessage: WSMessage | null = null;

function notifyListeners() {
  listeners.forEach((fn) => {
    try {
      fn(globalLastMessage);
    } catch {
      // Prevent one listener error from breaking others
    }
  });
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  const delay = RECONNECT_DELAYS[Math.min(reconnectAttempt, RECONNECT_DELAYS.length - 1)];
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    reconnectAttempt += 1;
    connect();
  }, delay);
}

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${protocol}//${window.location.host}/ws`;

  try {
    ws = new WebSocket(url);
  } catch {
    scheduleReconnect();
    return;
  }

  globalReadyState = WebSocket.CONNECTING;
  notifyListeners();

  ws.onopen = () => {
    reconnectAttempt = 0;
    globalReadyState = WebSocket.OPEN;
    notifyListeners();

    pingTimer = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, PING_INTERVAL);
  };

  ws.onmessage = (event) => {
    try {
      globalLastMessage = JSON.parse(event.data);
      notifyListeners();
    } catch {
      // Ignore invalid JSON
    }
  };

  ws.onclose = () => {
    globalReadyState = WebSocket.CLOSED;
    if (pingTimer) {
      clearInterval(pingTimer);
      pingTimer = null;
    }
    notifyListeners();
    scheduleReconnect();
  };

  ws.onerror = () => {
    console.error('WebSocket connection error');
  };
}

function teardownConnection() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (pingTimer) {
    clearInterval(pingTimer);
    pingTimer = null;
  }
  if (ws) {
    ws.onopen = null;
    ws.onmessage = null;
    ws.onclose = null;
    ws.onerror = null;
    ws.close();
    ws = null;
  }
  globalReadyState = WebSocket.CLOSED;
  globalLastMessage = null;
}

export function useWebSocket() {
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(globalLastMessage);
  const [readyState, setReadyState] = useState<number>(globalReadyState);

  useEffect(() => {
    const listener: Listener = (message) => {
      setLastMessage(message);
      setReadyState(globalReadyState);
    };

    listeners.add(listener);
    setReadyState(globalReadyState);

    if (listeners.size === 1) {
      connect();
    }

    return () => {
      listeners.delete(listener);
      if (listeners.size === 0) {
        teardownConnection();
      }
    };
  }, []);

  const sendMessage = useCallback((data: Record<string, unknown>) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  }, []);

  return { lastMessage, readyState, sendMessage };
}
