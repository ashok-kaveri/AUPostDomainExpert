import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

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

# File extensions to index from source code directories
CODE_FILE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".php", ".java", ".py", ".go", ".rb", ".cs"]

# Knowledge sources
PLUGINHIVE_BASE_URL = "https://www.pluginhive.com/product/australia-post-shopify-shipping-app-rates-label-tracking/"

# Guaranteed seed URLs — always crawled first before BFS expansion.
# These cover the AU Post Shopify app knowledge base and FAQ pages.
PLUGINHIVE_SEED_URLS: list[str] = [
    # Product page
    "https://www.pluginhive.com/product/australia-post-shopify-shipping-app-rates-label-tracking/",
    # Knowledge base articles
    "https://www.pluginhive.com/knowledge-base/install-and-activate-shopify-australia-post-app/",
    "https://www.pluginhive.com/knowledge-base/shopify-australia-post-shipping-app-setup/",
    "https://www.pluginhive.com/knowledge-base/australia-post-eparcel-label-printing-in-shopify/",
    "https://www.pluginhive.com/knowledge-base/australia-post-mypost-business-shopify/",
    "https://www.pluginhive.com/knowledge-base/australia-post-shipping-rates-in-shopify/",
    "https://www.pluginhive.com/knowledge-base/australia-post-tracking-shopify/",
    "https://www.pluginhive.com/knowledge-base/australia-post-return-labels-shopify/",
    "https://www.pluginhive.com/knowledge-base/australia-post-international-shipping-shopify/",
    "https://www.pluginhive.com/knowledge-base/australia-post-pickup-shopify/",
]

SHOPIFY_APP_STORE_URL = "https://apps.shopify.com/australia-post-rates-labels"

AUTOMATION_CODEBASE_PATH = os.getenv(
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
