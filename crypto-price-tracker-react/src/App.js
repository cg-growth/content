import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import './App.css'; // Import the CSS
import NewsTicker from './components/News'; // Import the News components
import CryptoNewsAnalyzer from './components/CryptoNewsAnalyzer'; // Import the CryptoNewsAnalyzer components

function CoinDetails({ coin, history }) {
  // Prepare the data for the line chart
  const chartData = history.map(dataPoint => ({ date: new Date(dataPoint[0]).toDateString(), price: dataPoint[1] }));
  const priceChangeColor = coin.price_change_24h < 0 ? 'red' : 'green';

  return (
    <div className="coin-details">
      <h2>{coin.name} ({coin.symbol.toUpperCase()})</h2>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%' }}>
        <span style={{ color: priceChangeColor, fontSize: '0.8em', top: 2, right: 1200, }}>
          {coin.price_change_24h > 0 && '+'}{coin.price_change_24h?.toFixed(2)}%
        </span>
        <p style={{ fontSize: '2em', margin: 0 }}>
          Current Price: ${coin.current_price?.toFixed(2)}
        </p>
      </div>
      <h2>Historical Data</h2>
      <LineChart width={500} height={300} data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="price" stroke="#8884d8" activeDot={{ r: 8 }} />
      </LineChart>
    </div>
  );
}

const holdingsData = [
  { id: 'bitcoin', symbol: 'BTC', amount: 0.5, cost_basis: 30000 }, // replace with actual data
  { id: 'ethereum', symbol: 'ETH', amount: 2, cost_basis: 1500 }, // replace with actual data
  // add more coins here...
];

function App() {
  const [coins, setCoins] = useState([]);
  const [allCoins, setAllCoins] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(new Date());
  const [endDate, setEndDate] = useState(new Date());
  const api_key = process.env.REACT_APP_COINGECKO_API_KEY;

  const holdings = useMemo(() => holdingsData, []);

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042']; // add more colors if you have more coins

  useEffect(() => {
    axios.get(`https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd`, {
      headers: {
        'X-CoinAPI-Key': api_key
      }
    })
      .then(response => {
        setAllCoins(response.data);
      })
      .catch(error => {
        console.error('Error fetching all coins', error);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    axios.get(`https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${holdings.map(holding => holding.id).join(',')}`, {
      headers: {
        'X-CoinAPI-Key': api_key
      }
    })
      .then(response => {
        const updatedHoldings = holdings.map(holding => {
          const coin = response.data.find(coin => coin.id === holding.id);
          return {
            ...holding,
            name: coin.name,
            current_price: coin.current_price,
            price_change_24h: coin.price_change_24h,
            price_change_percentage_24h: coin.price_change_percentage_24h
          };
        });
        setCoins(updatedHoldings);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching data', error);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [holdings]);

  const handleCoinSelect = (id) => {
    setLoading(true);
    const selected = allCoins.find(coin => coin.id === id);
    setSelectedCoin(selected);
  
    // Fetch historical data for the selected date range
    const promises = [];
    const date = new Date(startDate);
    while (date <= endDate) {
      const formattedDate = `${date.getDate()}-${date.getMonth() + 1}-${date.getFullYear()}`;
  
      const promise = axios.get(`https://api.coingecko.com/api/v3/coins/${id}/history?date=${formattedDate}`, {
        headers: {
          'X-CoinAPI-Key': api_key
        }
      })
        .then(response => {
          const price = response.data.market_data.current_price.usd;
          return [Date.parse(formattedDate), price];
        })
        .catch(error => {
          console.error('Error fetching historical data', error);
          return [Date.parse(formattedDate), 0]; // Return a default value
        });
  
      promises.push(promise);
      date.setDate(date.getDate() + 1); // Increment the date
    }
  
    Promise.all(promises)
      .then(history => {
        setHistory(history);
        setLoading(false);
      });
  };

  // Calculate total portfolio value
  const totalValue = coins.reduce((total, coin) => total + (coin.current_price * coin.amount), 0);

  // Calculate ROI and P&L
  const totalInvested = coins.reduce((total, coin) => total + coin.cost_basis, 0);
  const roi = ((totalValue - totalInvested) / totalInvested) * 100;
  const pnl = totalValue - totalInvested;

  return (
    <div className="App">
      <header className="App-header">
        <NewsTicker />
        <h1>Crypto Dashboard</h1>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100vh' }}>
            <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between', width: '100%', height: '100%' }}>
              <div style={{ flex: 1, border: '1px solid #333', margin: '10px', padding: '20px', borderRadius: '10px', boxSizing: 'border-box', backgroundColor: '#1F1F1F', color: '#A9A9A9' }}>
                <h2>Portfolio Tracker</h2>
                <ResponsiveContainer width="100%" height={400}>
                  <PieChart>
                    <Pie
                      data={coins}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="amount"
                    >
                      {
                        coins.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)
                      }
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <h3>Holdings</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Coin</th>
                      <th>Amount</th>
                      <th>Current Value</th>
                      <th>24h Change $</th>
                      <th>24h Change %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {coins.map((coin, index) => (
                      <tr key={index}>
                        <td>{coin.name}</td>
                        <td>{coin.amount}</td>
                        <td>${(coin.current_price * coin.amount).toFixed(2)}</td>
                        <td>{coin.price_change_24h?.toFixed(2)}</td>
                        <td>{coin.price_change_percentage_24h?.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <h3>Total Portfolio Value: ${totalValue.toFixed(2)}</h3>
                <h3>ROI: {roi.toFixed(2)}%</h3>
                <h3>P&L: ${pnl.toFixed(2)}</h3>
              </div>
              <div style={{ flex: 1, border: '1px solid #333', margin: '10px', padding: '20px', borderRadius: '10px', boxSizing: 'border-box', backgroundColor: '#1F1F1F', color: '#A9A9A9' }}>
                <h2>Trends</h2>
                <select value={selectedCoin ? selectedCoin.id : ''} onChange={e => handleCoinSelect(e.target.value)}>
                  {allCoins.map(coin => (
                    <option key={coin.id} value={coin.id}>{coin.name} ({coin.symbol.toUpperCase()})</option>
                  ))}
                </select>
                <DatePicker selected={startDate} onChange={date => setStartDate(date)} />
                <DatePicker selected={endDate} onChange={date => setEndDate(date)} />
                {selectedCoin && <CoinDetails coin={selectedCoin} history={history} />}
                </div>
              <div style={{ flex: 1, border: '1px solid #333', margin: '10px', padding: '20px', borderRadius: '10px', boxSizing: 'border-box', backgroundColor: '#1F1F1F', color: '#A9A9A9' }}>
                <CryptoNewsAnalyzer coins={allCoins} />
              </div>
            </div>
          </div>
        )}
      </header>
    </div>
  );
}

export default App;