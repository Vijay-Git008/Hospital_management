import { useEffect, useRef, useState } from 'react';

export function useNegotiationSocket(onMessageCallback: (data: any) => void) {
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let socketUrl = '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    // Check if we are running in dev mode or prod
    if (import.meta.env.DEV) {
      socketUrl = `ws://127.0.0.1:8000/ws`;
    } else {
      socketUrl = `${protocol}//${window.location.host}/ws`;
    }

    const connect = () => {
      console.log(`Connecting to WebSocket: ${socketUrl}`);
      const ws = new WebSocket(socketUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log('WebSocket connection established.');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageCallback(data);
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        console.log('WebSocket connection closed. Reconnecting in 3s...');
        setTimeout(connect, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error occurred:', error);
        ws.close();
      };
    };

    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
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
