import React from 'react';

function Portfolio({ portfolio }) {
  return (
    <div>
      <h2>Portfolio</h2>
      {portfolio.map((coin) => (
        <div key={coin.id}>
          <h3>{coin.name}</h3>
          <p>Holdings: {coin.holdings}</p>
          <p>Current Value: {coin.currentValue}</p>
          <p>24h Change: {coin.change24h}%</p>
          <p>Total Value: {coin.totalValue}</p>
          <p>ROI: {coin.roi}%</p>
          <p>P&L: {coin.pl}</p>
          <p>Allocation: {coin.allocation}%</p>
        </div>
      ))}
    </div>
  );
}

export default Portfolio;