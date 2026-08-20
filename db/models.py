from __future__ import annotations

import logging
from datetime import datetime, timedelta

import db.connection as conn

logger = logging.getLogger(__name__)


async def get_or_create_user(
    user_id: int,
    username: str | None,
    first_name: str | None,
) -> dict:
    row = await conn.pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    if row:
        return dict(row)
    await conn.pool.execute(
        "INSERT INTO users (id, username, first_name) VALUES ($1, $2, $3)",
        user_id, username, first_name,
    )
    logger.info("New user registered: %s (%s)", user_id, first_name)
    return dict(await conn.pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id))


async def get_balance(user_id: int) -> int:
    bal = await conn.pool.fetchval("SELECT balance FROM users WHERE id = $1", user_id)
    return bal or 0


async def get_free_gen_left(user_id: int) -> int:
    val = await conn.pool.fetchval("SELECT free_gen_left FROM users WHERE id = $1", user_id)
    return val or 0


async def use_free_gen(user_id: int) -> bool:
    result = await conn.pool.execute(
        "UPDATE users SET free_gen_left = free_gen_left - 1 WHERE id = $1 AND free_gen_left > 0",
        user_id,
    )
    return result == "UPDATE 1"


async def deduct_balance(user_id: int, amount: int, description: str) -> bool:
    async with conn.pool.acquire() as connection:
        async with connection.transaction():
            bal = await connection.fetchval(
                "SELECT balance FROM users WHERE id = $1 FOR UPDATE",
                user_id,
            )
            if bal is None or bal < amount:
                return False
            new_bal = bal - amount
            await connection.execute(
                "UPDATE users SET balance = $1 WHERE id = $2",
                new_bal, user_id,
            )
            await connection.execute(
                "INSERT INTO transactions (user_id, type, amount, balance_after, description) "
                "VALUES ($1, 'generation', $2, $3, $4)",
                user_id, -amount, new_bal, description,
            )
    return True


async def add_balance(user_id: int, amount: int, payment_id: str) -> None:
    async with conn.pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute(
                "UPDATE users SET balance = balance + $1 WHERE id = $2",
                amount, user_id,
            )
            new_bal = await connection.fetchval(
                "SELECT balance FROM users WHERE id = $1", user_id,
            )
            await connection.execute(
                "INSERT INTO transactions (user_id, type, amount, balance_after, description) "
                "VALUES ($1, 'topup', $2, $3, $4)",
                user_id, amount, new_bal, f"Пополнение (платёж {payment_id})",
            )
            await connection.execute(
                "INSERT INTO payments (user_id, amount, payment_id, status) "
                "VALUES ($1, $2, $3, 'completed')",
                user_id, amount, payment_id,
            )


async def record_generation(
    user_id: int,
    action_type: str,
    model_used: str,
    cost: int,
    result_ok: bool,
) -> None:
    await conn.pool.execute(
        "INSERT INTO generations (user_id, action_type, model_used, cost, result_ok) "
        "VALUES ($1, $2, $3, $4, $5)",
        user_id, action_type, model_used, cost, result_ok,
    )


async def get_user_stats(user_id: int) -> dict:
    row = await conn.pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    if not row:
        return {}
    total_gens = await conn.pool.fetchval(
        "SELECT COUNT(*) FROM generations WHERE user_id = $1", user_id,
    )
    successful_gens = await conn.pool.fetchval(
        "SELECT COUNT(*) FROM generations WHERE user_id = $1 AND result_ok = true", user_id,
    )
    total_spent = await conn.pool.fetchval(
        "SELECT COALESCE(SUM(ABS(amount)), 0) FROM transactions "
        "WHERE user_id = $1 AND type = 'generation'", user_id,
    )
    total_topup = await conn.pool.fetchval(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions "
        "WHERE user_id = $1 AND type = 'topup'", user_id,
    )
    return {
        "balance": row["balance"],
        "free_gen_left": row["free_gen_left"],
        "total_gens": total_gens,
        "successful_gens": successful_gens,
        "total_spent": total_spent,
        "total_topup": total_topup,
        "joined": row["created_at"],
    }


async def get_paid_gen_count(user_id: int) -> int:
    val = await conn.pool.fetchval(
        "SELECT COUNT(*) FROM generations WHERE user_id = $1 AND cost > 0",
        user_id,
    )
    return val or 0


async def get_global_stats() -> dict:
    total_users = await conn.pool.fetchval("SELECT COUNT(*) FROM users")
    new_today = await conn.pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE",
    )
    total_gens = await conn.pool.fetchval("SELECT COUNT(*) FROM generations")
    gens_today = await conn.pool.fetchval(
        "SELECT COUNT(*) FROM generations WHERE created_at >= CURRENT_DATE",
    )
    total_revenue = await conn.pool.fetchval(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'topup'",
    )
    total_cost = await conn.pool.fetchval(
        "SELECT COALESCE(SUM(ABS(amount)), 0) FROM transactions WHERE type = 'generation'",
    )
    return {
        "total_users": total_users,
        "new_today": new_today,
        "total_gens": total_gens,
        "gens_today": gens_today,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
    }


BONUS_PER_REFERRAL = 1


async def process_referral(inviter_id: int, invited_id: int) -> bool:
    if inviter_id == invited_id:
        return False

    exists = await conn.pool.fetchval(
        "SELECT id FROM referrals WHERE invited_id = $1", invited_id,
    )
    if exists:
        return False

    inviter_exists = await conn.pool.fetchval(
        "SELECT id FROM users WHERE id = $1", inviter_id,
    )
    if not inviter_exists:
        return False

    async with conn.pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute(
                "INSERT INTO referrals (inviter_id, invited_id, bonus_given) "
                "VALUES ($1, $2, TRUE)",
                inviter_id, invited_id,
            )
            await connection.execute(
                "UPDATE users SET free_gen_left = free_gen_left + $1 WHERE id = $2",
                BONUS_PER_REFERRAL, inviter_id,
            )
            await connection.execute(
                "UPDATE users SET free_gen_left = free_gen_left + $1 WHERE id = $2",
                BONUS_PER_REFERRAL, invited_id,
            )
            inviter_bal = await connection.fetchval(
                "SELECT free_gen_left FROM users WHERE id = $1", inviter_id,
            )

    logger.info("Referral: %s invited %s, both got +%d free gen(s)", inviter_id, invited_id, BONUS_PER_REFERRAL)
    return True


async def get_referral_count(user_id: int) -> int:
    val = await conn.pool.fetchval(
        "SELECT COUNT(*) FROM referrals WHERE inviter_id = $1", user_id,
    )
    return val or 0
