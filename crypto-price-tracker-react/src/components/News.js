import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Marquee from 'react-marquee-slider';

function NewsTicker() {
  const [news, setNews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const apiKey = process.env.REACT_APP_NEWS_API_KEY;

    const NEWS_API_URL = `https://api.allorigins.win/get?url=${encodeURIComponent(
      `https://newsapi.org/v2/top-headlines?country=us&apiKey=${apiKey}`
    )}`;

    axios.get(NEWS_API_URL)
      .then(response => {
        const parsedData = JSON.parse(response.data.contents); // Parse the wrapped response
        console.log('Parsed API Response:', parsedData);
        setNews(parsedData.articles);
        setIsLoading(false);
      })
      .catch(error => {
        console.error('API Error:', error);
        setError('Failed to fetch news');
        setIsLoading(false);
      });
  }, []);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  return (
    <Marquee velocity={1}>
      {news.map((article, index) => (
        <a key={`marquee-example-news-${index}`} href={article.url} target="_blank" rel="noopener noreferrer" className="news-ticker">
          <h1>{article.description}</h1>
          <p>{new Date(article.publishedAt).toLocaleString()}</p>
        </a>
      ))}
    </Marquee>
  );
}

export default NewsTicker;