CREATE TABLE IF NOT EXISTS users (
    id            BIGINT PRIMARY KEY,
    username      VARCHAR(255),
    first_name    VARCHAR(255),
    balance       INTEGER DEFAULT 0,
    free_gen_left INTEGER DEFAULT 2,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id            SERIAL PRIMARY KEY,
    user_id       BIGINT REFERENCES users(id),
    type          VARCHAR(20) NOT NULL,
    amount        INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description   TEXT,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS generations (
    id            SERIAL PRIMARY KEY,
    user_id       BIGINT REFERENCES users(id),
    action_type   VARCHAR(50),
    model_used    VARCHAR(100),
    cost          INTEGER,
    result_ok     BOOLEAN,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
    id            SERIAL PRIMARY KEY,
    user_id       BIGINT REFERENCES users(id),
    amount        INTEGER,
    payment_id    VARCHAR(255),
    status        VARCHAR(20) DEFAULT 'pending',
    created_at    TIMESTAMP DEFAULT NOW()
);
