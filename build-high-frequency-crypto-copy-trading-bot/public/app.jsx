const { useState, useEffect, useCallback } = React;

// Mock data generators
function generateMockPools() {
  const pools = [
    { name: 'TUNA / SOL', dex: 'pumpswap', price: 0.000426, volume: 2930000, liquidity: 70220, change: 142.5 },
    { name: 'PENGU / SOL', dex: 'orca', price: 0.009232, volume: 114560, liquidity: 3370000, change: 12.3 },
    { name: 'BONK / SOL', dex: 'raydium', price: 0.0000234, volume: 890000, liquidity: 2100000, change: -5.2 },
    { name: 'WIF / SOL', dex: 'orca', price: 1.23, volume: 4500000, liquidity: 8900000, change: 8.7 },
    { name: 'POPCAT / SOL', dex: 'raydium', price: 0.892, volume: 1200000, liquidity: 3400000, change: -2.1 },
  ];
  return pools.map((p, i) => ({
    ...p,
    address: `${Math.random().toString(36).substring(2, 8)}...${Math.random().toString(36).substring(2, 6)}`,
    id: i + 1,
  }));
}

function generateMockWallets() {
  return [
    { address: '6sAFaCPkdU...4RwqPJ', trades: 8, buys: 5, sells: 3, pnl: 1745.89, avgSize: 234.50 },
    { address: '2qpj8oFAQA...q6UYF6', trades: 5, buys: 2, sells: 3, pnl: 624.94, avgSize: 156.20 },
    { address: 'HnQKwmAP5z...8kPmN2', trades: 12, buys: 7, sells: 5, pnl: 423.12, avgSize: 89.30 },
    { address: '9xVrTpLmKj...2nWqR4', trades: 6, buys: 3, sells: 3, pnl: -127.50, avgSize: 312.00 },
    { address: 'Dw8mNpYcRt...7fLsK9', trades: 4, buys: 2, sells: 2, pnl: -289.33, avgSize: 445.00 },
  ];
}

function generateMockTrade(targetWallets) {
  const types = ['buy', 'sell'];
  const tokens = ['TUNA', 'PENGU', 'BONK', 'WIF', 'POPCAT'];
  const isTarget = Math.random() > 0.7 && targetWallets.length > 0;
  
  return {
    id: Date.now(),
    time: new Date().toLocaleTimeString(),
    type: types[Math.floor(Math.random() * types.length)],
    token: tokens[Math.floor(Math.random() * tokens.length)],
    amount: (Math.random() * 1000 + 50).toFixed(2),
    wallet: isTarget 
      ? targetWallets[Math.floor(Math.random() * targetWallets.length)]
      : `${Math.random().toString(36).substring(2, 8)}...${Math.random().toString(36).substring(2, 6)}`,
    isTarget,
  };
}

function shortNum(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(2) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(2) + 'K';
  return n.toFixed(2);
}

function App() {
  const [network, setNetwork] = useState('eth');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  const [pools, setPools] = useState([]);
  const [wallets, setWallets] = useState([]);
  const [targetWallets, setTargetWallets] = useState([]);
  const [trades, setTrades] = useState([]);
  const [logs, setLogs] = useState([]);
  
  const [equity, setEquity] = useState(10000);
  const [maxPositionPct, setMaxPositionPct] = useState(5);
  const [paperTrades, setPaperTrades] = useState([]);
  
  const [stats, setStats] = useState({
    totalTrades: 0,
    profitableTrades: 0,
    totalPnL: 0,
    copiedTrades: 0,
  });

  const addLog = useCallback((message, type = 'info') => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-50), { time, message, type }]);
  }, []);

  const fetchTrendingPools = useCallback(async () => {
    setIsLoading(true);
    addLog(`Fetching trending pools on ${network}...`, 'info');
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const mockPools = generateMockPools();
    setPools(mockPools);
    addLog(`Found ${mockPools.length} trending pools`, 'success');
    setIsLoading(false);
  }, [network, addLog]);

  const analyzePool = useCallback(async (poolAddress) => {
    setIsLoading(true);
    addLog(`Analyzing wallets in pool ${poolAddress}...`, 'info');
    
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const mockWallets = generateMockWallets();
    setWallets(mockWallets);
    addLog(`Found ${mockWallets.length} wallets with trade history`, 'success');
    
    const profitable = mockWallets.filter(w => w.pnl > 0).length;
    addLog(`${profitable} wallets are profitable`, 'success');
    setIsLoading(false);
  }, [addLog]);

  const addTargetWallet = useCallback((address) => {
    if (!targetWallets.includes(address)) {
      setTargetWallets(prev => [...prev, address]);
      addLog(`Added ${address} to target wallets`, 'success');
    }
  }, [targetWallets, addLog]);

  const removeTargetWallet = useCallback((address) => {
    setTargetWallets(prev => prev.filter(w => w !== address));
    addLog(`Removed ${address} from target wallets`, 'warn');
  }, [addLog]);

  const startMonitoring = useCallback(() => {
    if (targetWallets.length === 0) {
      addLog('No target wallets selected!', 'error');
      return;
    }
    
    setIsConnected(true);
    addLog('Connected to WebSocket trade stream', 'success');
    addLog(`Monitoring ${targetWallets.length} target wallets...`, 'info');
  }, [targetWallets, addLog]);

  const stopMonitoring = useCallback(() => {
    setIsConnected(false);
    addLog('Disconnected from trade stream', 'warn');
  }, [addLog]);

  // Simulate incoming trades when connected
  useEffect(() => {
    if (!isConnected) return;
    
    const interval = setInterval(() => {
      const trade = generateMockTrade(targetWallets);
      setTrades(prev => [trade, ...prev.slice(0, 49)]);
      
      if (trade.isTarget) {
        addLog(`TARGET WALLET TRADE: ${trade.type.toUpperCase()} ${trade.token}`, 'success');
        
        // Simulate copy trade
        const positionSize = Math.min(equity * (maxPositionPct / 100), parseFloat(trade.amount) * 0.1);
        setPaperTrades(prev => [...prev, {
          ...trade,
          copiedAmount: positionSize.toFixed(2),
          timestamp: new Date().toISOString(),
        }]);
        
        setStats(prev => ({
          ...prev,
          copiedTrades: prev.copiedTrades + 1,
          totalPnL: prev.totalPnL + (Math.random() * 100 - 30),
        }));
      }
      
      setStats(prev => ({
        ...prev,
        totalTrades: prev.totalTrades + 1,
      }));
    }, 2000 + Math.random() * 3000);
    
    return () => clearInterval(interval);
  }, [isConnected, targetWallets, equity, maxPositionPct, addLog]);

  return (
    <div className="container">
      {/* Header */}
      <div className="header">
        <h1>
          <span className="icon">🤖</span>
          Copy Trading Bot
        </h1>
        <div className={`status-badge ${isConnected ? '' : 'offline'}`}>
          <span className="status-dot"></span>
          {isConnected ? 'Live Monitoring' : 'Disconnected'}
        </div>
      </div>

      {/* Stats Overview */}
      <div className="card full-width" style={{ marginBottom: 20 }}>
        <div className="stats-grid">
          <div className="stat-item">
            <div className="stat-value">${equity.toLocaleString()}</div>
            <div className="stat-label">Paper Equity</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{targetWallets.length}</div>
            <div className="stat-label">Target Wallets</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{stats.totalTrades}</div>
            <div className="stat-label">Trades Seen</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{stats.copiedTrades}</div>
            <div className="stat-label">Copied Trades</div>
          </div>
          <div className="stat-item">
            <div className={`stat-value ${stats.totalPnL >= 0 ? 'good' : 'bad'}`}>
              {stats.totalPnL >= 0 ? '+' : ''}${stats.totalPnL.toFixed(2)}
            </div>
            <div className="stat-label">Paper PnL</div>
          </div>
        </div>
      </div>

      <div className="grid">
        {/* Pool Discovery */}
        <div className="card">
          <h2>🔍 Pool Discovery</h2>
          <div className="form-row">
            <div className="field">
              <label>Network</label>
              <select value={network} onChange={e => setNetwork(e.target.value)}>
                <option value="eth">Ethereum</option>
                <option value="solana">Solana</option>
                <option value="base">Base</option>
                <option value="arbitrum">Arbitrum</option>
              </select>
            </div>
            <div className="field" style={{ flex: 'none' }}>
              <label>&nbsp;</label>
              <button onClick={fetchTrendingPools} disabled={isLoading}>
                {isLoading ? 'Loading...' : 'Fetch Pools'}
              </button>
            </div>
          </div>
          
          {pools.length > 0 && (
            <div className="table-wrap" style={{ marginTop: 12 }}>
              <table>
                <thead>
                  <tr>
                    <th>Pool</th>
                    <th>DEX</th>
                    <th>Volume 24h</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {pools.map(pool => (
                    <tr key={pool.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{pool.name}</div>
                        <div className="addr">{pool.address}</div>
                      </td>
                      <td>{pool.dex}</td>
                      <td>${shortNum(pool.volume)}</td>
                      <td>
                        <button 
                          className="secondary" 
                          style={{ padding: '6px 12px', fontSize: 12 }}
                          onClick={() => analyzePool(pool.address)}
                        >
                          Analyze
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Wallet Analysis */}
        <div className="card">
          <h2>👛 Wallet Analysis</h2>
          
          {wallets.length === 0 ? (
            <div className="empty-state">
              <div className="icon">📊</div>
              <div>Select a pool to analyze wallet profitability</div>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Wallet</th>
                    <th>Trades</th>
                    <th>PnL</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {wallets.map((wallet, i) => (
                    <tr key={i}>
                      <td className="addr">{wallet.address}</td>
                      <td>{wallet.trades}</td>
                      <td className={wallet.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}>
                        {wallet.pnl >= 0 ? '+' : ''}${wallet.pnl.toFixed(2)}
                      </td>
                      <td>
                        <button 
                          className="secondary" 
                          style={{ padding: '6px 12px', fontSize: 12 }}
                          onClick={() => addTargetWallet(wallet.address)}
                          disabled={targetWallets.includes(wallet.address)}
                        >
                          {targetWallets.includes(wallet.address) ? 'Added' : 'Copy'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Target Wallets & Controls */}
        <div className="card">
          <h2>🎯 Target Wallets</h2>
          
          <div className="form-row">
            <div className="field">
              <label>Paper Equity ($)</label>
              <input 
                type="number" 
                value={equity} 
                onChange={e => setEquity(Number(e.target.value))}
              />
            </div>
            <div className="field">
              <label>Max Position (%)</label>
              <input 
                type="number" 
                value={maxPositionPct} 
                onChange={e => setMaxPositionPct(Number(e.target.value))}
                min="1"
                max="100"
              />
            </div>
          </div>
          
          {targetWallets.length === 0 ? (
            <div className="empty-state" style={{ padding: 20 }}>
              <div>No target wallets selected</div>
            </div>
          ) : (
            <div className="wallet-chips">
              {targetWallets.map(wallet => (
                <div key={wallet} className="wallet-chip">
                  <span className="addr">{wallet}</span>
                  <span className="remove" onClick={() => removeTargetWallet(wallet)}>✕</span>
                </div>
              ))}
            </div>
          )}
          
          <div style={{ marginTop: 16, display: 'flex', gap: 12 }}>
            {!isConnected ? (
              <button onClick={startMonitoring} disabled={targetWallets.length === 0}>
                ▶️ Start Monitoring
              </button>
            ) : (
              <button className="danger" onClick={stopMonitoring}>
                ⏹️ Stop Monitoring
              </button>
            )}
          </div>
        </div>

        {/* Live Trade Feed */}
        <div className="card">
          <h2>📡 Live Trade Feed</h2>
          
          {trades.length === 0 ? (
            <div className="empty-state">
              <div className="icon">📡</div>
              <div>{isConnected ? 'Waiting for trades...' : 'Start monitoring to see trades'}</div>
            </div>
          ) : (
            <div className="trade-feed">
              {trades.slice(0, 10).map(trade => (
                <div key={trade.id} className="trade-item" style={trade.isTarget ? { background: 'rgba(103,232,166,0.08)' } : {}}>
                  <span className="trade-time">{trade.time}</span>
                  <span className={`badge ${trade.type}`}>{trade.type.toUpperCase()}</span>
                  <div className="trade-details">
                    <div className="trade-token">{trade.token}</div>
                    <div className="trade-wallet">
                      {trade.isTarget && <span style={{ color: 'var(--good)', marginRight: 4 }}>⭐</span>}
                      {trade.wallet}
                    </div>
                  </div>
                  <div className="trade-amount">${trade.amount}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Activity Log */}
      <div className="card full-width">
        <h2>📋 Activity Log</h2>
        <div className="log-console">
          {logs.length === 0 ? (
            <div style={{ color: 'var(--muted)', padding: 8 }}>No activity yet...</div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="log-line">
                <span className="log-time">[{log.time}]</span>
                <span className={`log-${log.type}`}>{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
