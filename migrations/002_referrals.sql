CREATE TABLE IF NOT EXISTS referrals (
    id            SERIAL PRIMARY KEY,
    inviter_id    BIGINT REFERENCES users(id),
    invited_id    BIGINT REFERENCES users(id),
    bonus_given   BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(invited_id)
);
