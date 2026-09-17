import React, { useState } from 'react';

interface Props {
  title: string;
  count?: number;
}

const TestHeredoc: React.FC<Props> = ({ title, count = 0 }) => {
  const [counter, setCounter] = useState<number>(count);

  const handleClick = () => {
    setCounter((prev) => prev + 1);
  };

  return (
    <div className="test-container">
      <h1>{title}</h1>
      <p>Current count: <strong>{counter}</strong></p>
      <button onClick={handleClick} style={{ padding: '8px 16px' }}>
        +1
      </button>
      {counter > 10 && (
        <div className="warning">Count is greater than 10!</div>
      )}
    </div>
  );
};

export default TestHeredoc;
