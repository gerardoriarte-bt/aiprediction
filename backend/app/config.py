"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
import secrets
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)


class Config:
    """Flask配置类"""
    
    # Flask配置
    # If SECRET_KEY is not set, generate a random one (sessions won't persist across restarts).
    # Always set SECRET_KEY explicitly in production.
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False
    
    # LLM配置（统一使用OpenAI格式）
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # 文件上传与 multipart 表单
    # Flask 默认 MAX_FORM_MEMORY_SIZE 仅 500KB，较大的 simulation_requirement 会触发 413。
    # 非文件字段上限与整请求体上限对齐（可通过 MIROFISH_MAX_UPLOAD_MB 调整）。
    MIROFISH_MAX_UPLOAD_MB = int(os.environ.get('MIROFISH_MAX_UPLOAD_MB', '200'))
    MAX_CONTENT_LENGTH = MIROFISH_MAX_UPLOAD_MB * 1024 * 1024
    MAX_FORM_MEMORY_SIZE = MAX_CONTENT_LENGTH
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    # CORS — restrict to configured origins (comma-separated). Default: localhost dev server.
    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
        if o.strip()
    ]

    # Creative Testing (additive, opt-in). Default OFF: existing flow unchanged.
    # Phase 1 of ROADMAP_CREATIVE_TESTING_90D. When False, dedicated endpoints
    # respond 404 so the surface remains invisible to current users.
    CREATIVE_TESTING_ENABLED = os.environ.get('CREATIVE_TESTING_ENABLED', 'False').lower() == 'true'
    CREATIVE_TESTING_MODE = os.environ.get('CREATIVE_TESTING_MODE', 'mock')  # mock | live

    # Postgres connection.
    DATABASE_URL = os.environ.get('DATABASE_URL')

    # Embedding provider for the Postgres backend.
    EMBEDDING_PROVIDER = os.environ.get('EMBEDDING_PROVIDER', 'openai').lower()  # openai | ollama
    EMBEDDING_MODEL = os.environ.get(
        'EMBEDDING_MODEL',
        'text-embedding-3-small' if os.environ.get('EMBEDDING_PROVIDER', 'openai').lower() == 'openai'
        else 'nomic-embed-text'
    )
    # Dimension is provider-dependent. Defaults: OpenAI text-embedding-3-small=1536,
    # Ollama nomic-embed-text=768. Override with EMBEDDING_DIM when needed.
    EMBEDDING_DIM = int(os.environ.get(
        'EMBEDDING_DIM',
        '1536' if os.environ.get('EMBEDDING_PROVIDER', 'openai').lower() == 'openai' else '768'
    ))
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')

    @classmethod
    def validate(cls):
        """验证必要配置"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL 未配置 (required for the Postgres graph backend)")
        if cls.EMBEDDING_PROVIDER not in ('openai', 'ollama'):
            errors.append(
                f"EMBEDDING_PROVIDER='{cls.EMBEDDING_PROVIDER}' is invalid; expected 'openai' or 'ollama'"
            )
        if cls.EMBEDDING_DIM <= 0:
            errors.append("EMBEDDING_DIM must be a positive integer")

        return errors

