import { useEffect, useRef, useState } from 'react';

export function useNegotiationSocket(onMessageCallback: (data: any) => void) {
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let socketUrl = '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    
    if (import.meta.env.VITE_WS_URL) {
      socketUrl = import.meta.env.VITE_WS_URL;
    } else if (host.includes('-3000')) {
      // Auto-resolve Codespaces & VS Code WebSockets on port 8080
      socketUrl = `${protocol}//${host.replace('-3000', '-8080')}/ws`;
    } else if (host.includes(':3000')) {
      // Resolve to same IP or hostname running on port 8080
      socketUrl = `${protocol}//${window.location.hostname}:8080/ws`;
    } else {
      const apiUrl = import.meta.env.VITE_API_URL;
      if (apiUrl) {
        socketUrl = apiUrl.replace(/^http/, 'ws').replace(/\/+$/, '') + '/ws';
      } else {
        socketUrl = `${protocol}//${window.location.host}/ws`;
      }
    }

    let active = true;
    const connect = () => {
      if (!active) return;
      console.log(`Connecting to WebSocket: ${socketUrl}`);
      try {
        const ws = new WebSocket(socketUrl);
        socketRef.current = ws;

        ws.onopen = () => {
          if (active) setConnected(true);
          console.log('WebSocket connection established.');
        };

        ws.onmessage = (event) => {
          if (!active) return;
          try {
            const data = JSON.parse(event.data);
            onMessageCallback(data);
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };

        ws.onclose = () => {
          if (active) {
            setConnected(false);
            console.log('WebSocket connection closed. Reconnecting in 3s...');
            setTimeout(connect, 3000);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error occurred:', error);
          try {
            ws.close();
          } catch (e) {}
        };
      } catch (err) {
        console.error('Failed to create WebSocket client:', err);
        if (active) {
          setConnected(false);
          // Try to reconnect in 5s
          setTimeout(connect, 5000);
        }
      }
    };

    connect();

    return () => {
      active = false;
      if (socketRef.current) {
        try {
          socketRef.current.close();
        } catch (e) {}
      }
    };
  }, [onMessageCallback]);

  const send = (message: any) => {
    if (socketRef.current && connected) {
      socketRef.current.send(JSON.stringify(message));
    }
  };

  return { connected, send };
}
