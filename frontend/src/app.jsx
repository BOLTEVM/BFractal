import { useState, useEffect, useRef } from 'preact/hooks';
import './index.css';

export function App() {
  const [address, setAddress] = useState('bc1p0...your_fractal_address');
  const [threads, setThreads] = useState(1);
  const [rpcUser, setRpcUser] = useState('user');
  const [rpcPass, setRpcPass] = useState('pass');
  
  const [stats, setStats] = useState({ 
    node_running: false, 
    miner_running: false, 
    block_height: 0, 
    headers_synced: 0,
    sync_progress: 0, 
    hashrate: 0,
    logs: [] 
  });
  
  const [errorHeader, setErrorHeader] = useState(null);
  const ws = useRef(null);
  const cliRef = useRef(null);

  useEffect(() => {
    connectWS();
    return () => ws.current?.close();
  }, []);

  const connectWS = () => {
    ws.current = new WebSocket(`ws://${window.location.hostname}:8000/ws`);
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStats(data);
    };
    ws.current.onerror = () => setErrorHeader("Communication link severed. Reconnecting...");
    ws.current.onopen = () => setErrorHeader(null);
    ws.current.onclose = () => setTimeout(connectWS, 3000);
  };

  useEffect(() => {
    if (cliRef.current) cliRef.current.scrollTop = cliRef.current.scrollHeight;
  }, [stats.logs]);

  const toggleNode = async () => {
    const endpoint = stats.node_running ? '/node/stop' : '/node/start';
    try {
      await fetch(`http://${window.location.hostname}:8000${endpoint}`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({}) });
    } catch (e) { setErrorHeader("Node Control Failure"); }
  };

  const toggleMiner = async () => {
    const endpoint = stats.miner_running ? '/miner/stop' : '/miner/start';
    const payload = { address, threads: Number(threads), rpc_user: rpcUser, rpc_pass: rpcPass };
    try {
      await fetch(`http://${window.location.hostname}:8000${endpoint}`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: endpoint === '/miner/start' ? JSON.stringify(payload) : undefined
      });
    } catch (e) { setErrorHeader("Miner Control Failure"); }
  };

  const blocksRemaining = stats.headers_synced - stats.block_height;

  return (
    <>
      <div className="mesh-bg"></div>
      {errorHeader && <div className="error-banner">⚠️ SYSTEM ALERT: {errorHeader}</div>}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', maxWidth: '1100px', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <img src="/logo.png" className="logo-main" alt="Fractal Logo" style={{ marginBottom: 0 }} />
            <div>
                <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Fractal Bitcoin</h1>
                <div className="subtitle" style={{ margin: 0, fontSize: '0.6rem', letterSpacing: '2px' }}>Infinite Scaling Substrate</div>
            </div>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
            <div className="tuning-badge balanced" style={{ opacity: 0.8 }}>WATCHDOG: ACTIVE</div>
            <div className={`tuning-badge ${stats.node_running ? 'turbo' : ''}`} style={{ opacity: 0.8 }}>NETWORK: {stats.node_running ? 'CONNECTED' : 'STANDBY'}</div>
        </div>
      </div>

      <div className="dashboard-layout">
        <div className="glass-panel node-zone">
            <label>Substrate Node Control</label>
            <div className="stats-grid-v2" style={{ marginBottom: '1.5rem' }}>
                <div className="stat-widget">
                    <span className="stat-header">Validated Blocks</span>
                    <span className="stat-data highlight">{stats.block_height.toLocaleString()}</span>
                </div>
                <div className="stat-widget">
                    <span className="stat-header">Network Headers</span>
                    <span className="stat-data">{stats.headers_synced.toLocaleString()}</span>
                </div>
            </div>
            
            <div className="input-section">
                <label>Verification Depth</label>
                <div className="progress-container">
                    <div className="progress-bar" style={{ width: `${stats.sync_progress * 100}%` }}></div>
                    <span className="progress-text">{blocksRemaining > 0 ? `${blocksRemaining.toLocaleString()} blocks remaining` : 'Synced'}</span>
                </div>
            </div>

            <button className={`btn-premium ${stats.node_running ? 'btn-stop' : 'btn-start'}`} onClick={toggleNode}>
                {stats.node_running ? 'Shutdown Node' : 'Initialize Node'}
            </button>
        </div>

        <div className="glass-panel miner-zone">
            <label>Mining Cluster Performance</label>
            <div className="stats-grid-v2" style={{ marginBottom: '1.5rem' }}>
                <div className="stat-widget">
                    <span className="stat-header">Cluster Hashrate</span>
                    <span className="stat-data highlight">{stats.hashrate} <small style={{fontSize: '0.8rem'}}>MH/s</small></span>
                </div>
                <div className="stat-widget">
                    <span className="stat-header">Safety Coupling</span>
                    <span className="stat-data" style={{ color: stats.miner_running ? 'var(--neon-cyan)' : 'var(--text-dim)' }}>
                        {stats.miner_running ? 'PROTECTED' : 'IDLE'}
                    </span>
                </div>
            </div>

            <div className="grid-2">
                <div className="input-section">
                    <label>Wallet Address</label>
                    <input className="input-glow" value={address} onInput={e => setAddress(e.target.value)} disabled={stats.miner_running} />
                </div>
                <div className="input-section">
                    <label>Threads</label>
                    <input type="number" className="input-glow" value={threads} onInput={e => setThreads(e.target.value)} disabled={stats.miner_running} />
                </div>
            </div>

            <button className={`btn-premium ${stats.miner_running ? 'btn-stop' : 'btn-start'}`} onClick={toggleMiner} disabled={!stats.node_running && !stats.miner_running}>
                {stats.miner_running ? 'Halt Cluster' : 'Start Mining'}
            </button>
            {!stats.node_running && !stats.miner_running && <div style={{fontSize: '0.6rem', color: 'var(--neon-amber)', marginTop: '0.5rem'}}>Node must be initialized before mining.</div>}
        </div>

        <div className="glass-panel chart-group">
            <label>Integrated Substrate Logs // Multi-Channel Terminal</label>
            <div className="cli-container" ref={cliRef}>
                {stats.logs.map((log, i) => (
                    <div key={i} className="cli-line">
                        <span className="cli-time">[{log.time}]</span>
                        <span className={`cli-cat cat-${log.cat}`} style={{ borderColor: log.source === 'NODE' ? 'var(--primary)' : 'var(--secondary)' }}>
                            {log.source}
                        </span>
                        <span className="cli-msg">{log.msg}</span>
                    </div>
                ))}
            </div>
        </div>
      </div>

      <footer className="footer-credits">SYSTEM VERSION 4.1.0-HARDENED | SECURED BY BOLTEVM WATCHDOG</footer>
    </>
  );
}
