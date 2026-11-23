from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import DATABASE_PATH, ROLE_DURATION_DAYS

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    username = Column(String(100))
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    balance = Column(Integer, default=0)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    message_count = Column(Integer, default=0)
    vc_minutes = Column(Integer, default=0)
    last_message_at = Column(DateTime)
    last_reward_at = Column(DateTime)
    daily_reward_claimed_at = Column(DateTime)
    daily_streak = Column(Integer, default=0)


class ShopItem(Base):
    """Dynamic shop items that can be added/removed by admins."""
    __tablename__ = 'shop_items'
    
    role_id = Column(BigInteger, primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    duration_days = Column(Integer, default=30)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPurchase(Base):
    """User role purchases with expiry tracking."""
    __tablename__ = 'user_purchases'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    role_id = Column(BigInteger, nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    
    # Composite index for efficient queries
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class GuildConfig(Base):
    """Server-specific configuration."""
    __tablename__ = 'guild_config'
    
    guild_id = Column(BigInteger, primary_key=True)
    prefix = Column(String(10), default="!")
    default_channel_id = Column(BigInteger, nullable=True)


class Database:
    def __init__(self, db_path=DATABASE_PATH):
        # Convert SQLite path to async SQLite URL
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self.async_session = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
    
    async def init(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def _calculate_level_from_xp(self, xp: int) -> int:
        """
        Calculates the user's level based on Arcane's quadratic XP formula.
        Level L to L+1 takes 5*(L^2) + 50*L + 100 XP.
        """
        level = 0
        while True:
            xp_for_next = 5 * (level ** 2) + 50 * level + 100
            if xp >= xp_for_next:
                xp -= xp_for_next
                level += 1
            else:
                break
        return level
    
    async def get_or_create_user(self, user_id, guild_id, username=None):
        async with self.async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if user is None:
                user = User(id=user_id, guild_id=guild_id, username=username)
                session.add(user)
                await session.commit()
            elif username and user.username != username:
                user.username = username
                await session.commit()
            
            return user
    
    async def get_user(self, user_id):
        async with self.async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
    
    async def update_username(self, user_id, username):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.username = username
                await session.commit()
    
    # Balance methods
    async def get_balance(self, user_id):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            return user.balance if user else 0
    
    async def set_balance(self, user_id, amount):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.balance = amount
                await session.commit()
    
    async def add_balance(self, user_id, amount):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.balance += amount
                await session.commit()
                return user.balance
            return None

    async def add_xp(self, user_id, amount):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.xp += amount
                new_level = self._calculate_level_from_xp(user.xp)
                if new_level > user.level:
                    user.level = new_level
                await session.commit()
                return user.level
            return None
    
    async def remove_balance(self, user_id, amount):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.balance = max(0, user.balance - amount)
                await session.commit()
    
    # Message methods
    async def get_message_count(self, user_id):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            return user.message_count if user else 0
    
    async def increment_message_count(self, user_id):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.message_count += 1
                user.last_message_at = datetime.utcnow()
                await session.commit()
                return user.message_count
            return 0
    
    async def get_last_message_time(self, user_id):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            return user.last_message_at if user else None
    
    async def get_top_messagers(self, limit=10):
        async with self.async_session() as session:
            result = await session.execute(
                select(User).order_by(User.message_count.desc()).limit(limit)
            )
            return result.scalars().all()
    
    async def get_richest_users(self, limit=10):
        async with self.async_session() as session:
            result = await session.execute(
                select(User).order_by(User.balance.desc()).limit(limit)
            )
            return result.scalars().all()
    
    # Daily reward methods
    async def get_daily_reward_status(self, user_id):
        """Get user's daily reward status. Returns (can_claim, hours_until_reset, current_streak)."""
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if not user:
                return (True, 0, 0)
            
            if not user.daily_reward_claimed_at:
                return (True, 0, user.daily_streak or 0)
            
            now = datetime.utcnow()
            last_claim = user.daily_reward_claimed_at
            time_since_claim = now - last_claim
            
            # Can claim if 24 hours have passed
            if time_since_claim >= timedelta(hours=24):
                # Check if streak should reset (more than 48 hours = missed a day)
                if time_since_claim >= timedelta(hours=48):
                    streak = 0  # Reset streak
                else:
                    streak = user.daily_streak or 0
                return (True, 0, streak)
            else:
                hours_remaining = 24 - (time_since_claim.total_seconds() / 3600)
                return (False, hours_remaining, user.daily_streak or 0)
    
    async def claim_daily_reward(self, user_id, guild_id, username):
        """Claim daily reward. Returns (coins_earned, new_streak, total_streak_days)."""
        async with self.async_session() as session:
            user = await self.get_or_create_user(user_id, guild_id, username)
            
            now = datetime.utcnow()
            
            # Calculate streak
            if user.daily_reward_claimed_at:
                time_since_claim = now - user.daily_reward_claimed_at
                if time_since_claim >= timedelta(hours=48):
                    user.daily_streak = 1  # Reset streak (missed a day)
                else:
                    user.daily_streak = (user.daily_streak or 0) + 1
            else:
                user.daily_streak = 1  # First claim
            
            # Calculate reward (base 100 + 10 per streak day, max 500)
            base_reward = 100
            streak_bonus = min((user.daily_streak - 1) * 10, 400)  # Cap at 400 bonus
            total_reward = base_reward + streak_bonus
            
            # Update user
            user.daily_reward_claimed_at = now
            user.balance += total_reward
            user.xp += total_reward  # XP for daily reward too
            
            # Dynamic exponential level up check
            new_level = self._calculate_level_from_xp(user.xp)
            if new_level > user.level:
                user.level = new_level
            
            await session.commit()
            
            return (total_reward, user.daily_streak, user.daily_streak)
    
    async def get_user_active_purchases(self, user_id):
        """Get user's active role purchases with days remaining."""
        async with self.async_session() as session:
            now = datetime.utcnow()
            result = await session.execute(
                select(UserPurchase).where(
                    UserPurchase.user_id == user_id,
                    UserPurchase.expiry_date > now
                ).order_by(UserPurchase.expiry_date.asc())
            )
            purchases = result.scalars().all()
            
            # Calculate days remaining for each
            active_purchases = []
            for purchase in purchases:
                days_remaining = (purchase.expiry_date - now).days
                if days_remaining >= 0:
                    active_purchases.append({
                        'role_id': purchase.role_id,
                        'expiry_date': purchase.expiry_date,
                        'days_remaining': days_remaining
                    })
            
            return active_purchases
    
    # XP/Leveling methods
    async def get_xp(self, user_id):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            return user.xp if user else 0
    
    async def get_level(self, user_id):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            return user.level if user else 1
    
    async def add_xp(self, user_id, amount):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                old_level = user.level
                user.xp += amount

                # Dynamic exponential level up logic
                new_level = self._calculate_level_from_xp(user.xp)
                if new_level > user.level:
                    user.level = new_level
                await session.commit()
                return new_level > old_level, user.level
            return False, 1
    
    # VC methods
    async def add_vc_minutes(self, user_id, minutes):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.vc_minutes += minutes
                await session.commit()
    
    async def get_vc_minutes(self, user_id):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            return user.vc_minutes if user else 0
    
    async def get_last_reward_time(self, user_id):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            return user.last_reward_at if user else None
    
    async def update_last_reward_time(self, user_id):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.last_reward_at = datetime.utcnow()
                await session.commit()
    
    # Dynamic Shop Methods
    async def add_shop_item(self, role_id: int, name: str, price: int, duration: int, description: str = None):
        """
        Add or update a shop item.
        
        Args:
            role_id: Discord role ID
            name: Role display name
            price: Cost in coins
            duration: Duration in days
            description: Optional description
            
        Returns:
            The created/updated ShopItem
        """
        async with self.async_session() as session:
            item = await session.get(ShopItem, role_id)
            if item:
                item.name = name
                item.price = price
                item.duration_days = duration
                item.description = description
            else:
                item = ShopItem(
                    role_id=role_id,
                    name=name,
                    price=price,
                    duration_days=duration,
                    description=description
                )
                session.add(item)
            await session.commit()
            return item
    
    async def remove_shop_item(self, role_id: int):
        """
        Remove a shop item from the database.
        
        Args:
            role_id: Discord role ID to remove
        """
        async with self.async_session() as session:
            item = await session.get(ShopItem, role_id)
            if item:
                await session.delete(item)
                await session.commit()
    
    async def get_shop_item(self, role_id: int):
        """
        Get a specific shop item by role ID.
        
        Args:
            role_id: Discord role ID
            
        Returns:
            ShopItem or None if not found
        """
        async with self.async_session() as session:
            return await session.get(ShopItem, role_id)
    
    async def get_all_shop_items(self):
        """
        Get all shop items.
        
        Returns:
            List of all ShopItem objects
        """
        async with self.async_session() as session:
            result = await session.execute(select(ShopItem))
            return result.scalars().all()
    
    # User Purchase Methods
    async def record_purchase(self, user_id: int, role_id: int, duration_days: int):
        """
        Record a role purchase with specified duration.
        
        Args:
            user_id: Discord user ID
            role_id: Discord role ID
            duration_days: How many days the role lasts
            
        Returns:
            The created UserPurchase object
        """
        async with self.async_session() as session:
            expiry = datetime.utcnow() + timedelta(days=duration_days)
            purchase = UserPurchase(
                user_id=user_id,
                role_id=role_id,
                expiry_date=expiry
            )
            session.add(purchase)
            await session.commit()
            return purchase
    
    async def get_expired_purchases(self):
        """
        Get all expired purchases.
        
        Returns:
            List of UserPurchase objects where expiry_date < now
        """
        async with self.async_session() as session:
            now = datetime.utcnow()
            result = await session.execute(
                select(UserPurchase).where(UserPurchase.expiry_date < now)
            )
            return result.scalars().all()
    
    async def get_user_active_purchases(self, user_id: int):
        """
        Get all active (non-expired) purchases for a user with days remaining.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of dicts with role_id, expiry_date, and days_remaining
        """
        async with self.async_session() as session:
            now = datetime.utcnow()
            result = await session.execute(
                select(UserPurchase)
                .where(UserPurchase.user_id == user_id)
                .where(UserPurchase.expiry_date > now)
                .order_by(UserPurchase.expiry_date.asc())
            )
            purchases = result.scalars().all()
            
            # Calculate days remaining for each
            active_purchases = []
            for purchase in purchases:
                days_remaining = (purchase.expiry_date - now).days
                if days_remaining >= 0:
                    active_purchases.append({
                        'role_id': purchase.role_id,
                        'expiry_date': purchase.expiry_date,
                        'days_remaining': days_remaining
                    })
            
            return active_purchases
    
    async def delete_user_purchase(self, purchase_id: int):
        """
        Delete a user purchase record by ID.
        
        Args:
            purchase_id: The purchase record ID to delete
        """
        async with self.async_session() as session:
            purchase = await session.get(UserPurchase, purchase_id)
            if purchase:
                await session.delete(purchase)
                await session.commit()
    
    # Legacy Purchase methods (kept for backward compatibility)
    async def add_purchase(self, user_id, role_id):
        """Legacy method - uses default ROLE_DURATION_DAYS."""
        return await self.record_purchase(user_id, role_id, ROLE_DURATION_DAYS)
    
    async def get_expired_roles(self):
        """Legacy method - delegates to get_expired_purchases."""
        return await self.get_expired_purchases()
    
    async def get_user_purchases(self, user_id):
        """Legacy method - delegates to get_user_active_purchases."""
        return await self.get_user_active_purchases(user_id)
    
    async def delete_purchase(self, purchase_id):
        """Legacy method - delegates to delete_user_purchase."""
        await self.delete_user_purchase(purchase_id)

    # Guild Config methods
    async def get_guild_config(self, guild_id: int):
        async with self.async_session() as session:
            result = await session.execute(select(GuildConfig).where(GuildConfig.guild_id == guild_id))
            config = result.scalar_one_or_none()
            if not config:
                config = GuildConfig(guild_id=guild_id)
                session.add(config)
                await session.commit()
            return config

    async def set_guild_prefix(self, guild_id: int, prefix: str):
        async with self.async_session() as session:
            config = await session.get(GuildConfig, guild_id)
            if not config:
                config = GuildConfig(guild_id=guild_id, prefix=prefix)
                session.add(config)
            else:
                config.prefix = prefix
            await session.commit()

    async def set_guild_channel(self, guild_id: int, channel_id: int):
        async with self.async_session() as session:
            config = await session.get(GuildConfig, guild_id)
            if not config:
                config = GuildConfig(guild_id=guild_id, default_channel_id=channel_id)
                session.add(config)
            else:
                config.default_channel_id = channel_id
            await session.commit()

    async def reset_guild_config(self, guild_id: int):
        async with self.async_session() as session:
            config = await session.get(GuildConfig, guild_id)
            if config:
                await session.delete(config)
                await session.commit()

