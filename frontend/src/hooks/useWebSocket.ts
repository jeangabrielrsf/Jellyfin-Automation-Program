import { useState, useEffect, useRef, useCallback } from 'react';

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000];
const PING_INTERVAL = 30000;

type Listener = (message: any) => void;

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let pingTimer: ReturnType<typeof setInterval> | null = null;
let reconnectAttempt = 0;
let listeners: Set<Listener> = new Set();
let globalReadyState: number = WebSocket.CLOSED;
let globalLastMessage: any = null;

function notifyListeners() {
  listeners.forEach((fn) => fn(globalLastMessage));
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
    // onclose will be called after this
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
  const [lastMessage, setLastMessage] = useState<any>(globalLastMessage);
  const [readyState, setReadyState] = useState<number>(globalReadyState);
  const listenerRef = useRef<Listener | null>(null);

  useEffect(() => {
    const listener = (message: any) => {
      setLastMessage(message);
    };
    listenerRef.current = listener;
    listeners.add(listener);

    setReadyState(globalReadyState);

    if (listeners.size === 1) {
      connect();
    }

    return () => {
      listeners.delete(listener);
      listenerRef.current = null;
      if (listeners.size === 0) {
        teardownConnection();
      }
    };
  }, []);

  useEffect(() => {
    const sync = () => {
      setReadyState(globalReadyState);
    };
    const originalListener = listenerRef.current;
    if (originalListener) {
      listeners.delete(originalListener as any);
    }
    const newListener = (message: any) => {
      setLastMessage(message);
      setReadyState(globalReadyState);
    };
    listenerRef.current = newListener;
    listeners.add(newListener);
    listeners.delete(sync as any);
  });

  const sendMessage = useCallback((data: any) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  }, []);

  return { lastMessage, readyState, sendMessage };
}
