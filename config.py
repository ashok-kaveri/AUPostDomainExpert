import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

BASE_DIR = Path(__file__).parent


def _env_path(key: str, default: str = "") -> str:
    """Return an env var, expanding ~ and resolving relative paths."""
    raw = os.getenv(key, default)
    if not raw:
        return raw
    p = Path(raw).expanduser()
    return str(p)


def require_env_path(key: str) -> Path:
    val = _env_path(key)
    if not val:
        raise EnvironmentError(f"Required env var {key!r} is not set.")
    p = Path(val)
    if not p.exists():
        raise FileNotFoundError(f"{key}={val!r} does not exist on disk.")
    return p

# Anthropic / Claude
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Primary model — deep reasoning, code gen, visual exploration
CLAUDE_SONNET_MODEL = os.getenv("CLAUDE_SONNET_MODEL", "claude-sonnet-4-6")
# Fast/cheap model — card processing, feature detection, lightweight tasks
CLAUDE_HAIKU_MODEL = os.getenv("CLAUDE_HAIKU_MODEL", "claude-haiku-4-5-20251001")
# Default model used by the domain expert chat
DOMAIN_EXPERT_MODEL = os.getenv("DOMAIN_EXPERT_MODEL", CLAUDE_SONNET_MODEL)

# Ollama — kept ONLY for embeddings (Anthropic has no embedding model)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

# ChromaDB
CHROMA_PATH = str(BASE_DIR / "data" / "chroma_db")
CHROMA_COLLECTION = "aupost_knowledge"
# Separate collection for source code (backend + frontend)
CHROMA_CODE_COLLECTION = "aupost_code_knowledge"

# Source code paths (set via .env or indexed via the dashboard)
# Backend: shopify-australia-post-app  (Node/TS backend)
BACKEND_CODE_PATH  = os.getenv("BACKEND_CODE_PATH", "")
# Frontend: shopify-au-post-web-client  (React/TS frontend)
FRONTEND_CODE_PATH = os.getenv("FRONTEND_CODE_PATH", "")

# Shopify actions path (JSON file with UI interactions knowledge)
SHOPIFY_ACTIONS_PATH = _env_path("SHOPIFY_ACTIONS_PATH", "")
# PDF test cases path (additional test cases from PDF documents)
PDF_TEST_CASES_PATH = _env_path("PDF_TEST_CASES_PATH", "")

# File extensions to index from source code directories
CODE_FILE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".php", ".java", ".py", ".go", ".rb", ".cs"]

# Knowledge sources
PLUGINHIVE_BASE_URL = "https://www.pluginhive.com/product/australia-post-shopify-shipping-app-rates-label-tracking/"

# Guaranteed seed URLs — always crawled first before BFS expansion.
# These cover the AU Post Shopify app knowledge base and FAQ pages.
PLUGINHIVE_SEED_URLS: list[str] = [
    # Product page
    "https://www.pluginhive.com/product/australia-post-shopify-shipping-app-rates-label-tracking/",
    # Install & activate
    "https://www.pluginhive.com/knowledge-base/install-and-activate-shopify-australia-post-app/",
    # Full setup guide
    "https://www.pluginhive.com/knowledge-base/set-up-shopify-australia-post-rates-labels-tracking-app/",
    # Manual label generation
    "https://www.pluginhive.com/knowledge-base/how-to-generate-shopify-shipping-labels-using-australia-post-rates-and-labels-app/",
    # Auto label generation
    "https://www.pluginhive.com/knowledge-base/automatic-shipping-label-generation-with-shopify-australia-post-app/",
    # Real-time shipping rates
    "https://www.pluginhive.com/knowledge-base/shopify-real-time-australia-post-shipping-rates/",
    # Tracking & pickups
    "https://www.pluginhive.com/knowledge-base/shopify-australia-post-shipment-tracking-and-scheduling-pickups/",
    # International shipping
    "https://www.pluginhive.com/knowledge-base/shopify-australia-post-international-shipping/",
    # Packaging / box packing
    "https://www.pluginhive.com/knowledge-base/pack-products-optimally-using-shopify-australia-post-rates-and-labels-app/",
    # Label print preferences
    "https://www.pluginhive.com/knowledge-base/shopify-australia-post-shipping-label-print-preferences/",
    # Troubleshooting
    "https://www.pluginhive.com/knowledge-base/troubleshoot-shopify-australia-post-app/",
]

SHOPIFY_APP_STORE_URL = "https://apps.shopify.com/australia-post-rates-labels"

AUTOMATION_CODEBASE_PATH = _env_path(
    "AUTOMATION_CODEBASE_PATH",
    str(BASE_DIR.parent / "aupost-test-automation"),
)

# AU Post Shopify app slug (used for app URL construction)
AUPOST_APP_SLUG = os.getenv("AUPOST_APP_SLUG", "australia-post-rates-labels")

# Internal AU Post wiki (markdown knowledge base)
# Reads AUPOST_WIKI first, falls back to WIKI_PATH for backwards compatibility
WIKI_PATH = os.getenv("AUPOST_WIKI") or os.getenv("WIKI_PATH", "")

# Google Sheets — AU Post test cases
# eParcel test cases sheet
EPARCEL_SHEETS_ID = os.getenv(
    "EPARCEL_SHEETS_ID", "1Uf9NyCCwaKpHGlLVvI7S9xOVEGDekJNIHJFFlUsOcoA"
)
# MyPost Business test cases sheet
MYPOST_SHEETS_ID = os.getenv(
    "MYPOST_SHEETS_ID", "1zLRpb2HSeb7XM4bJMb0ZCNWSDHr3zbFzN2meyhDnvEE"
)
GOOGLE_SHEETS_ID = os.getenv(
    "GOOGLE_SHEETS_ID", "1i7YQWLSmiJ0wK-lAoAmaNe3gNvbm9T0ry3TwWSxB-Wc"
)
GOOGLE_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH", str(BASE_DIR / "credentials.json")
)

# RAG settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
PLUGINHIVE_MAX_PAGES = int(os.getenv("PLUGINHIVE_MAX_PAGES", "200"))
TOP_K_RESULTS = 8
MEMORY_WINDOW = 10
