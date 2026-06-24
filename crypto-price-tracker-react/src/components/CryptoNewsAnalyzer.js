import React, { useEffect, useState } from 'react';
import axios from 'axios';

function CryptoNewsAnalyzer({ coins }) {
  const [suggestedCoins, setSuggestedCoins] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const apiKey = process.env.REACT_APP_NEWS_API_KEY;

    const NEWS_API_URL = `https://api.allorigins.win/get?url=${encodeURIComponent(
      `https://newsapi.org/v2/top-headlines?country=us&apiKey=${apiKey}`
    )}`;
    const MARKET_API_URL = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1';

    Promise.all([
      axios.get(NEWS_API_URL),
      axios.get(MARKET_API_URL),
    ])
      .then(([newsResponse, marketResponse]) => {
        const parsedData = JSON.parse(newsResponse.data.contents);
        const articles = parsedData.articles;
        const positiveKeywords = [
          'bull', 'rally', 'rise', 'gain', 'positive', 'buy', 'up', 
          'growth', 'increase', 'profit', 'investment', 'crypto', 'currency'
        ];
        const marketData = marketResponse.data;

        // Filter coins based on news sentiment
        const suggestedCoins = marketData.filter(coin => {
          return articles.some(article => {
            const title = article.title ? article.title.toLowerCase() : '';
            const description = article.description ? article.description.toLowerCase() : '';
            return positiveKeywords.some(keyword => title.includes(keyword) || description.includes(keyword)) &&
                   (title.includes(coin.name.toLowerCase()) || description.includes(coin.name.toLowerCase()));
          });
        });

        // If no coins match news sentiment, fallback to top 10 by market cap
        if (suggestedCoins.length === 0) {
          setSuggestedCoins(marketData.slice(0, 10));
        } else {
          setSuggestedCoins(suggestedCoins.slice(0, 10));
        }

        setIsLoading(false);
      })
      .catch(error => {
        console.error('API Error:', error);
        setError('Failed to fetch data');
        setIsLoading(false);
      });
  }, []);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  if (suggestedCoins.length === 0) {
    return <div>No cryptocurrencies matched the news sentiment.</div>;
  }

  return (
    <div className="crypto-news-analyzer">
      <h2>Top 10 Cryptocurrencies to Buy Based on News Sentiment</h2>
      {suggestedCoins.map((coin, index) => (
        <div key={index} className="suggested-coin" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '300px' }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <img src={coin.image} alt={coin.name} style={{ width: '20px', height: '20px', marginRight: '10px' }} />
            <h3 style={{ margin: 0 }}>{coin.name} ({coin.symbol.toUpperCase()})</h3>
          </div>
          <div style={{ position: 'relative', width: '100%' }}>
            <p style={{ fontSize: '1.9em' }}>{coin.current_price.toFixed(2)}</p>
            <span style={{ position: 'absolute', top: 2, right: 120, color: coin.price_change_24h < 0 ? 'red' : 'green' }}>
              {coin.price_change_24h.toFixed(2)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

export default CryptoNewsAnalyzer;