CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    public_key VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    developer_id INT REFERENCES users(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    capabilities JSONB,
    price DECIMAL(10,2),
    version VARCHAR(50) DEFAULT '1.0.0',
    download_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    agent_id INT REFERENCES agents(id),
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT TRUE
);

CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    agent_id INT REFERENCES agents(id),
    score INT CHECK (score >= 1 AND score <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
