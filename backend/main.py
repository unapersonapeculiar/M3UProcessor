"""
M3U Processor - Backend API
FastAPI application for processing IPTV M3U playlists
"""

import os
import re
import uuid
import json
import asyncio
import httpx
from datetime import datetime, timedelta, date
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from jose import JWTError, jwt
from passlib.context import CryptContext
import aiomysql

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
MAX_CONTENT_SIZE = 5 * 1024 * 1024  # 5MB

MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "m3u_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "m3u_password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "m3u_processor")

FRONTEND_DOMAIN = os.getenv("FRONTEND_DOMAIN", "http://localhost:3000")
API_DOMAIN = os.getenv("API_DOMAIN", "http://localhost:8000")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Database pool
db_pool = None


# ============ Pydantic Models ============

class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    is_approved: bool
    created_at: datetime


class Rule(BaseModel):
    search: str
    replace: str
    is_regex: bool = False
    case_sensitive: bool = True


class ProcessRequest(BaseModel):
    content: str
    rules: List[Rule] = []


class GenerateRequest(BaseModel):
    content: str
    rules: List[Rule] = []
    source_url: Optional[str] = None
    name: Optional[str] = None
    auto_update: bool = False
    auto_update_interval: int = 3600
    show_on_board: bool = False


class FetchRequest(BaseModel):
    url: str


class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    show_on_board: Optional[bool] = None
    auto_update: Optional[bool] = None
    auto_update_interval: Optional[int] = None


class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None


class SettingsUpdate(BaseModel):
    open_registration: bool


# ============ Database Functions ============

async def get_db():
    global db_pool
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            yield cursor, conn


async def init_db():
    global db_pool
    
    for attempt in range(30):
        try:
            db_pool = await aiomysql.create_pool(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DATABASE,
                autocommit=True,
                minsize=2,
                maxsize=10
            )
            break
        except Exception as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(2)
    
    if db_pool is None:
        raise Exception("Could not connect to database")
    
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Create tables
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    `key` VARCHAR(100) PRIMARY KEY,
                    `value` TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    role ENUM('user', 'admin') DEFAULT 'user',
                    is_active BOOLEAN DEFAULT TRUE,
                    is_approved BOOLEAN DEFAULT FALSE,
                    approved_at TIMESTAMP NULL,
                    approved_by INT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP NULL,
                    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    token VARCHAR(36) PRIMARY KEY,
                    user_id INT NULL,
                    content_m3u MEDIUMTEXT NOT NULL,
                    original_content MEDIUMTEXT,
                    rules_json TEXT,
                    source_url TEXT,
                    name VARCHAR(255),
                    auto_update BOOLEAN DEFAULT FALSE,
                    auto_update_interval INT DEFAULT 3600,
                    last_update_at TIMESTAMP NULL,
                    update_error TEXT,
                    total_hits INT DEFAULT 0,
                    show_on_board BOOLEAN DEFAULT FALSE,
                    last_status ENUM('OK', 'FAIL', 'UNKNOWN') DEFAULT 'UNKNOWN',
                    last_check_at TIMESTAMP NULL,
                    last_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_hits (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    token VARCHAR(36) NOT NULL,
                    date DATE NOT NULL,
                    hits INT DEFAULT 0,
                    UNIQUE KEY unique_token_date (token, date),
                    FOREIGN KEY (token) REFERENCES playlists(token) ON DELETE CASCADE
                )
            """)
            
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS check_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    token VARCHAR(36) NOT NULL,
                    check_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('OK', 'FAIL') NOT NULL,
                    http_code INT,
                    error TEXT,
                    FOREIGN KEY (token) REFERENCES playlists(token) ON DELETE CASCADE
                )
            """)
            
            # Insert default settings
            await cursor.execute("""
                INSERT IGNORE INTO system_settings (`key`, `value`) VALUES ('open_registration', 'false')
            """)
            
            # Create default admin if not exists
            await cursor.execute("SELECT id FROM users WHERE email = 'admin@m3uprocessor.xyz'")
            if not await cursor.fetchone():
                hashed = pwd_context.hash("admin123")
                await cursor.execute("""
                    INSERT INTO users (email, username, hashed_password, role, is_approved, approved_at)
                    VALUES ('admin@m3uprocessor.xyz', 'admin', %s, 'admin', TRUE, NOW())
                """, (hashed,))
            
            await conn.commit()
    
    print("Database initialized successfully")


async def close_db():
    global db_pool
    if db_pool:
        db_pool.close()
        await db_pool.wait_closed()


# ============ Background Tasks ============

async def auto_update_task():
    """Background task to auto-update playlists"""
    while True:
        try:
            if db_pool:
                async with db_pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cursor:
                        await cursor.execute("""
                            SELECT token, source_url, rules_json, auto_update_interval
                            FROM playlists
                            WHERE auto_update = TRUE
                            AND source_url IS NOT NULL
                            AND (last_update_at IS NULL OR 
                                 last_update_at < DATE_SUB(NOW(), INTERVAL auto_update_interval SECOND))
                        """)
                        playlists = await cursor.fetchall()
                        
                        for playlist in playlists:
                            try:
                                async with httpx.AsyncClient(timeout=30.0) as client:
                                    response = await client.get(playlist['source_url'])
                                    response.raise_for_status()
                                    content = response.text
                                    
                                    if playlist['rules_json']:
                                        rules = json.loads(playlist['rules_json'])
                                        content = apply_rules(content, rules)
                                    
                                    await cursor.execute("""
                                        UPDATE playlists 
                                        SET content_m3u = %s, last_update_at = NOW(), update_error = NULL
                                        WHERE token = %s
                                    """, (content, playlist['token']))
                                    await conn.commit()
                            except Exception as e:
                                await cursor.execute("""
                                    UPDATE playlists SET update_error = %s, last_update_at = NOW()
                                    WHERE token = %s
                                """, (str(e), playlist['token']))
                                await conn.commit()
        except Exception as e:
            print(f"Auto-update error: {e}")
        
        await asyncio.sleep(30)


async def source_check_task():
    """Background task to check source URLs every 24h"""
    while True:
        try:
            if db_pool:
                async with db_pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cursor:
                        await cursor.execute("""
                            SELECT token, source_url
                            FROM playlists
                            WHERE source_url IS NOT NULL
                            AND (last_check_at IS NULL OR 
                                 last_check_at < DATE_SUB(NOW(), INTERVAL 24 HOUR))
                        """)
                        playlists = await cursor.fetchall()
                        
                        for playlist in playlists:
                            await check_source(playlist['token'], playlist['source_url'])
        except Exception as e:
            print(f"Source check error: {e}")
        
        await asyncio.sleep(3600)


async def check_source(token: str, url: str):
    """Check if source URL is accessible"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.head(url, follow_redirects=True)
            status = "OK" if response.status_code == 200 else "FAIL"
            http_code = response.status_code
            error = None if status == "OK" else f"HTTP {response.status_code}"
    except Exception as e:
        status = "FAIL"
        http_code = None
        error = str(e)
    
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                UPDATE playlists SET last_status = %s, last_check_at = NOW(), last_error = %s
                WHERE token = %s
            """, (status, error, token))
            
            await cursor.execute("""
                INSERT INTO check_history (token, status, http_code, error)
                VALUES (%s, %s, %s, %s)
            """, (token, status, http_code, error))
            
            await conn.commit()
    
    return {"status": status, "http_code": http_code, "error": error}


# ============ Auth Functions ============

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db)
):
    cursor, conn = db
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    await cursor.execute("SELECT * FROM users WHERE id = %s AND is_active = TRUE", (user_id,))
    user = await cursor.fetchone()
    return user


async def require_user(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_approved_user(user=Depends(require_user)):
    if not user['is_approved']:
        raise HTTPException(status_code=403, detail="Account pending approval")
    return user


async def require_admin(user=Depends(require_user)):
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ============ Helper Functions ============

def apply_rules(content: str, rules: list) -> str:
    """Apply search/replace rules to content"""
    for rule in rules:
        search = rule.get('search', '')
        replace = rule.get('replace', '')
        is_regex = rule.get('is_regex', False)
        case_sensitive = rule.get('case_sensitive', True)
        
        if not search:
            continue
        
        if is_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                content = re.sub(search, replace, content, flags=flags)
            except re.error:
                pass
        else:
            if case_sensitive:
                content = content.replace(search, replace)
            else:
                pattern = re.compile(re.escape(search), re.IGNORECASE)
                content = pattern.sub(replace, content)
    
    return content


def count_channels(content: str) -> int:
    """Count EXTINF entries in M3U content"""
    return len(re.findall(r'#EXTINF:', content, re.IGNORECASE))


def get_m3u_stats(content: str) -> dict:
    """Get statistics from M3U content"""
    lines = content.split('\n')
    channels = count_channels(content)
    groups = set()
    
    for line in lines:
        match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
        if match:
            groups.add(match.group(1))
    
    return {
        "channels": channels,
        "groups": len(groups),
        "lines": len(lines),
        "size": len(content.encode('utf-8'))
    }


# ============ Lifespan ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(auto_update_task())
    asyncio.create_task(source_check_task())
    yield
    await close_db()


# ============ FastAPI App ============

app = FastAPI(
    title="M3U Processor API",
    description="API for processing IPTV M3U playlists",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Auth Endpoints ============

@app.post("/api/auth/register")
async def register(data: UserRegister, db=Depends(get_db)):
    cursor, conn = db
    
    # Check if email exists
    await cursor.execute("SELECT id FROM users WHERE email = %s", (data.email,))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username exists
    await cursor.execute("SELECT id FROM users WHERE username = %s", (data.username,))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Check open registration
    await cursor.execute("SELECT value FROM system_settings WHERE `key` = 'open_registration'")
    setting = await cursor.fetchone()
    is_open = setting and setting['value'] == 'true'
    
    hashed = get_password_hash(data.password)
    
    await cursor.execute("""
        INSERT INTO users (email, username, hashed_password, is_approved, approved_at)
        VALUES (%s, %s, %s, %s, %s)
    """, (data.email, data.username, hashed, is_open, datetime.utcnow() if is_open else None))
    await conn.commit()
    
    return {
        "message": "Registration successful" if is_open else "Registration pending approval",
        "requires_approval": not is_open
    }


@app.post("/api/auth/login")
async def login(data: UserLogin, db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
    user = await cursor.fetchone()
    
    if not user or not verify_password(data.password, user['hashed_password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user['is_active']:
        raise HTTPException(status_code=403, detail="Account disabled")
    
    if not user['is_approved']:
        raise HTTPException(status_code=403, detail="Account pending approval")
    
    # Update last login
    await cursor.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user['id'],))
    await conn.commit()
    
    token = create_access_token({"sub": user['id']})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user['id'],
            "email": user['email'],
            "username": user['username'],
            "role": user['role']
        }
    }


@app.get("/api/auth/me")
async def get_me(user=Depends(require_user)):
    return {
        "id": user['id'],
        "email": user['email'],
        "username": user['username'],
        "role": user['role'],
        "is_approved": user['is_approved'],
        "created_at": user['created_at']
    }


@app.put("/api/auth/me")
async def update_me(data: UserUpdate, user=Depends(require_approved_user), db=Depends(get_db)):
    cursor, conn = db
    
    updates = []
    values = []
    
    if data.username:
        await cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (data.username, user['id']))
        if await cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already taken")
        updates.append("username = %s")
        values.append(data.username)
    
    if data.password:
        updates.append("hashed_password = %s")
        values.append(get_password_hash(data.password))
    
    if updates:
        values.append(user['id'])
        await cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", tuple(values))
        await conn.commit()
    
    return {"message": "Profile updated"}


# ============ User Playlist Endpoints ============

@app.get("/api/my/playlists")
async def get_my_playlists(user=Depends(require_approved_user), db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("""
        SELECT token, name, source_url, auto_update, auto_update_interval,
               last_update_at, update_error, total_hits, show_on_board,
               last_status, last_check_at, created_at
        FROM playlists WHERE user_id = %s
        ORDER BY created_at DESC
    """, (user['id'],))
    
    playlists = await cursor.fetchall()
    
    return [{
        **p,
        "raw_url": f"{API_DOMAIN}/raw/{p['token']}.m3u"
    } for p in playlists]


@app.put("/api/my/playlists/{token}")
async def update_my_playlist(token: str, data: PlaylistUpdate, user=Depends(require_approved_user), db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("SELECT * FROM playlists WHERE token = %s AND user_id = %s", (token, user['id']))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    updates = []
    values = []
    
    if data.name is not None:
        updates.append("name = %s")
        values.append(data.name)
    
    if data.show_on_board is not None:
        updates.append("show_on_board = %s")
        values.append(data.show_on_board)
    
    if data.auto_update is not None:
        updates.append("auto_update = %s")
        values.append(data.auto_update)
    
    if data.auto_update_interval is not None:
        if data.auto_update_interval < 30 or data.auto_update_interval > 86400:
            raise HTTPException(status_code=400, detail="Interval must be between 30 and 86400 seconds")
        updates.append("auto_update_interval = %s")
        values.append(data.auto_update_interval)
    
    if updates:
        values.append(token)
        await cursor.execute(f"UPDATE playlists SET {', '.join(updates)} WHERE token = %s", tuple(values))
        await conn.commit()
    
    return {"message": "Playlist updated"}


@app.delete("/api/my/playlists/{token}")
async def delete_my_playlist(token: str, user=Depends(require_approved_user), db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("DELETE FROM playlists WHERE token = %s AND user_id = %s", (token, user['id']))
    await conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    return {"message": "Playlist deleted"}


# ============ Admin Endpoints ============

@app.get("/api/admin/stats")
async def get_admin_stats(user=Depends(require_admin), db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("SELECT COUNT(*) as total FROM users")
    total_users = (await cursor.fetchone())['total']
    
    await cursor.execute("SELECT COUNT(*) as total FROM users WHERE is_approved = TRUE")
    approved_users = (await cursor.fetchone())['total']
    
    await cursor.execute("SELECT COUNT(*) as total FROM users WHERE is_approved = FALSE")
    pending_users = (await cursor.fetchone())['total']
    
    await cursor.execute("SELECT COUNT(*) as total FROM playlists")
    total_playlists = (await cursor.fetchone())['total']
    
    await cursor.execute("SELECT COALESCE(SUM(total_hits), 0) as total FROM playlists")
    total_hits = (await cursor.fetchone())['total']
    
    await cursor.execute("""
        SELECT COALESCE(SUM(hits), 0) as total FROM daily_hits 
        WHERE date >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
    """)
    hits_24h = (await cursor.fetchone())['total']
    
    await cursor.execute("SELECT COUNT(*) as total FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)")
    users_24h = (await cursor.fetchone())['total']
    
    await cursor.execute("SELECT COUNT(*) as total FROM playlists WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)")
    playlists_24h = (await cursor.fetchone())['total']
    
    await cursor.execute("SELECT value FROM system_settings WHERE `key` = 'open_registration'")
    setting = await cursor.fetchone()
    open_registration = setting and setting['value'] == 'true'
    
    return {
        "total_users": total_users,
        "approved_users": approved_users,
        "pending_users": pending_users,
        "total_playlists": total_playlists,
        "total_hits": total_hits,
        "hits_24h": hits_24h,
        "users_24h": users_24h,
        "playlists_24h": playlists_24h,
        "open_registration": open_registration
    }


@app.get("/api/admin/settings")
async def get_settings(user=Depends(require_admin), db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("SELECT value FROM system_settings WHERE `key` = 'open_registration'")
    setting = await cursor.fetchone()
    
    return {
        "open_registration": setting and setting['value'] == 'true'
    }


@app.put("/api/admin/settings")
async def update_settings(data: SettingsUpdate, user=Depends(require_admin), db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("""
        INSERT INTO system_settings (`key`, `value`) VALUES ('open_registration', %s)
        ON DUPLICATE KEY UPDATE `value` = %s
    """, ('true' if data.open_registration else 'false', 'true' if data.open_registration else 'false'))
    await conn.commit()
    
    return {"message": "Settings updated"}


@app.get("/api/admin/users")
async def get_users(
    filter_pending: bool = False,
    search: str = "",
    user=Depends(require_admin),
    db=Depends(get_db)
):
    cursor, conn = db
    
    query = "SELECT id, email, username, role, is_active, is_approved, created_at, last_login_at FROM users"
    params = []
    
    conditions = []
    if filter_pending:
        conditions.append("is_approved = FALSE")
    if search:
        conditions.append("(email LIKE %s OR username LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY created_at DESC"
    
    await cursor.execute(query, tuple(params))
    users = await cursor.fetchall()
    
    return users


@app.put("/api/admin/users/{user_id}")
async def update_user(user_id: int, data: AdminUserUpdate, admin=Depends(require_admin), db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    target_user = await cursor.fetchone()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updates = []
    values = []
    
    if data.role is not None:
        if data.role not in ['user', 'admin']:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        # If demoting admin, ensure there's another admin
        if target_user['role'] == 'admin' and data.role == 'user':
            await cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin' AND id != %s", (user_id,))
            if (await cursor.fetchone())['count'] == 0:
                raise HTTPException(status_code=400, detail="Cannot demote the last admin")
        
        updates.append("role = %s")
        values.append(data.role)
    
    if data.is_active is not None:
        updates.append("is_active = %s")
        values.append(data.is_active)
    
    if data.is_approved is not None:
        updates.append("is_approved = %s")
        values.append(data.is_approved)
        if data.is_approved:
            updates.append("approved_at = NOW()")
            updates.append("approved_by = %s")
            values.append(admin['id'])
    
    if updates:
        values.append(user_id)
        await cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", tuple(values))
        await conn.commit()
    
    return {"message": "User updated"}


@app.post("/api/admin/users/{user_id}/approve")
async def approve_user(user_id: int, admin=Depends(require_admin), db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("""
        UPDATE users SET is_approved = TRUE, approved_at = NOW(), approved_by = %s
        WHERE id = %s AND is_approved = FALSE
    """, (admin['id'], user_id))
    await conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found or already approved")
    
    return {"message": "User approved"}


@app.post("/api/admin/users/{user_id}/reject")
async def reject_user(user_id: int, admin=Depends(require_admin), db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("DELETE FROM users WHERE id = %s AND is_approved = FALSE", (user_id,))
    await conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found or already approved")
    
    return {"message": "User rejected"}


@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, admin=Depends(require_admin), db=Depends(get_db)):
    cursor, conn = db
    
    if user_id == admin['id']:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    await cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
    target = await cursor.fetchone()
    
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target['role'] == 'admin':
        await cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
        if (await cursor.fetchone())['count'] <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin")
    
    await cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    await conn.commit()
    
    return {"message": "User deleted"}


@app.get("/api/admin/playlists")
async def get_all_playlists(
    search: str = "",
    user=Depends(require_admin),
    db=Depends(get_db)
):
    cursor, conn = db
    
    query = """
        SELECT p.token, p.name, p.source_url, p.total_hits, p.show_on_board,
               p.last_status, p.created_at, u.username as owner
        FROM playlists p
        LEFT JOIN users u ON p.user_id = u.id
    """
    params = []
    
    if search:
        query += " WHERE p.name LIKE %s OR p.token LIKE %s"
        params.extend([f"%{search}%", f"%{search}%"])
    
    query += " ORDER BY p.created_at DESC"
    
    await cursor.execute(query, tuple(params))
    playlists = await cursor.fetchall()
    
    return [{
        **p,
        "raw_url": f"{API_DOMAIN}/raw/{p['token']}.m3u"
    } for p in playlists]


# ============ Public Endpoints ============

@app.post("/api/process")
async def process_m3u(data: ProcessRequest):
    if len(data.content.encode('utf-8')) > MAX_CONTENT_SIZE:
        raise HTTPException(status_code=400, detail="Content exceeds 5MB limit")
    
    original_stats = get_m3u_stats(data.content)
    processed = apply_rules(data.content, [r.dict() for r in data.rules])
    processed_stats = get_m3u_stats(processed)
    
    return {
        "preview": processed[:5000] if len(processed) > 5000 else processed,
        "original": original_stats,
        "processed": processed_stats,
        "full_content": processed
    }


@app.post("/api/generate")
async def generate_playlist(
    data: GenerateRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    cursor, conn = db
    
    if len(data.content.encode('utf-8')) > MAX_CONTENT_SIZE:
        raise HTTPException(status_code=400, detail="Content exceeds 5MB limit")
    
    # Validate interval
    if data.auto_update and (data.auto_update_interval < 30 or data.auto_update_interval > 86400):
        raise HTTPException(status_code=400, detail="Interval must be between 30 and 86400 seconds")
    
    token = str(uuid.uuid4())
    processed = apply_rules(data.content, [r.dict() for r in data.rules])
    
    user_id = user['id'] if user and user['is_approved'] else None
    
    await cursor.execute("""
        INSERT INTO playlists (token, user_id, content_m3u, original_content, rules_json, 
                               source_url, name, auto_update, auto_update_interval, show_on_board)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        token, user_id, processed, data.content,
        json.dumps([r.dict() for r in data.rules]) if data.rules else None,
        data.source_url, data.name or f"Playlist {token[:8]}",
        data.auto_update, data.auto_update_interval, data.show_on_board
    ))
    await conn.commit()
    
    # Check source if URL provided
    if data.source_url:
        background_tasks.add_task(check_source, token, data.source_url)
    
    return {
        "token": token,
        "raw_url": f"{API_DOMAIN}/raw/{token}.m3u",
        "view_url": f"{FRONTEND_DOMAIN}/view.html?token={token}"
    }


@app.post("/api/fetch-m3u")
async def fetch_m3u(data: FetchRequest):
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(data.url)
            response.raise_for_status()
            content = response.text
            
            if len(content.encode('utf-8')) > MAX_CONTENT_SIZE:
                raise HTTPException(status_code=400, detail="Content exceeds 5MB limit")
            
            return {
                "content": content,
                "stats": get_m3u_stats(content)
            }
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Request timeout")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")


@app.get("/raw/{token}.m3u")
async def get_raw_m3u(token: str, db=Depends(get_db)):
    cursor, conn = db
    
    # Remove .m3u if present in token
    token = token.replace('.m3u', '')
    
    await cursor.execute("SELECT content_m3u FROM playlists WHERE token = %s", (token,))
    playlist = await cursor.fetchone()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    # Update hits
    today = date.today()
    await cursor.execute("""
        INSERT INTO daily_hits (token, date, hits) VALUES (%s, %s, 1)
        ON DUPLICATE KEY UPDATE hits = hits + 1
    """, (token, today))
    
    await cursor.execute("UPDATE playlists SET total_hits = total_hits + 1 WHERE token = %s", (token,))
    await conn.commit()
    
    return PlainTextResponse(
        content=playlist['content_m3u'],
        media_type="audio/x-mpegurl",
        headers={
            "Content-Disposition": f"attachment; filename={token}.m3u"
        }
    )


@app.get("/api/playlist/{token}")
async def get_playlist_info(token: str, db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("""
        SELECT token, name, source_url, total_hits, show_on_board,
               last_status, last_check_at, last_error, created_at,
               auto_update, auto_update_interval, last_update_at, update_error
        FROM playlists WHERE token = %s
    """, (token,))
    
    playlist = await cursor.fetchone()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    # Get check history
    await cursor.execute("""
        SELECT check_at, status, http_code, error
        FROM check_history WHERE token = %s
        ORDER BY check_at DESC LIMIT 10
    """, (token,))
    history = await cursor.fetchall()
    
    return {
        **playlist,
        "raw_url": f"{API_DOMAIN}/raw/{token}.m3u",
        "check_history": history
    }


@app.post("/api/playlist/{token}/check")
async def check_playlist(token: str, db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("SELECT source_url FROM playlists WHERE token = %s", (token,))
    playlist = await cursor.fetchone()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if not playlist['source_url']:
        raise HTTPException(status_code=400, detail="No source URL configured")
    
    result = await check_source(token, playlist['source_url'])
    return result


@app.post("/api/playlist/{token}/refresh")
async def refresh_playlist(token: str, db=Depends(get_db)):
    cursor, conn = db
    
    await cursor.execute("""
        SELECT source_url, rules_json FROM playlists WHERE token = %s
    """, (token,))
    playlist = await cursor.fetchone()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if not playlist['source_url']:
        raise HTTPException(status_code=400, detail="No source URL configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(playlist['source_url'])
            response.raise_for_status()
            content = response.text
            
            if playlist['rules_json']:
                rules = json.loads(playlist['rules_json'])
                content = apply_rules(content, rules)
            
            await cursor.execute("""
                UPDATE playlists 
                SET content_m3u = %s, last_update_at = NOW(), update_error = NULL
                WHERE token = %s
            """, (content, token))
            await conn.commit()
            
            return {"message": "Playlist refreshed", "stats": get_m3u_stats(content)}
    except Exception as e:
        await cursor.execute("""
            UPDATE playlists SET update_error = %s WHERE token = %s
        """, (str(e), token))
        await conn.commit()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/board")
async def get_board(period: str = "total", db=Depends(get_db)):
    cursor, conn = db
    
    if period == "24h":
        await cursor.execute("""
            SELECT p.token, p.name, p.last_status, 
                   COALESCE(SUM(d.hits), 0) as period_hits
            FROM playlists p
            LEFT JOIN daily_hits d ON p.token = d.token AND d.date >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
            WHERE p.show_on_board = TRUE
            GROUP BY p.token
            ORDER BY period_hits DESC
            LIMIT 50
        """)
    elif period == "7d":
        await cursor.execute("""
            SELECT p.token, p.name, p.last_status,
                   COALESCE(SUM(d.hits), 0) as period_hits
            FROM playlists p
            LEFT JOIN daily_hits d ON p.token = d.token AND d.date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            WHERE p.show_on_board = TRUE
            GROUP BY p.token
            ORDER BY period_hits DESC
            LIMIT 50
        """)
    elif period == "30d":
        await cursor.execute("""
            SELECT p.token, p.name, p.last_status,
                   COALESCE(SUM(d.hits), 0) as period_hits
            FROM playlists p
            LEFT JOIN daily_hits d ON p.token = d.token AND d.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            WHERE p.show_on_board = TRUE
            GROUP BY p.token
            ORDER BY period_hits DESC
            LIMIT 50
        """)
    else:
        await cursor.execute("""
            SELECT token, name, last_status, total_hits as period_hits
            FROM playlists
            WHERE show_on_board = TRUE
            ORDER BY total_hits DESC
            LIMIT 50
        """)
    
    playlists = await cursor.fetchall()
    
    return [{
        **p,
        "raw_url": f"{API_DOMAIN}/raw/{p['token']}.m3u"
    } for p in playlists]


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
