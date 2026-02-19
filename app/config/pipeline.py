DEFAULT_MODEL = "gpt-5.2"
ROTEIRO_PATTERN = r"ROT[_-]?MOD(\d+)[_-](?:N([CP])(\d+)|VIDINT)"
NUCLEUS_WORKERS = 5
IMAGE_WORKERS = 5
OPENAI_IMAGE_MODEL = "gpt-image-1.5"
OPENAI_IMAGE_SIZE = "1024x1536"
OPENAI_IMAGE_QUALITY = "low"
GAMMA_POLL_INTERVAL_SECONDS = 15
GAMMA_POLL_TIMEOUT_SECONDS = 600
GAMMA_COST_BRL_PER_CREDIT = 2.0

EXCLUDE_DIRS = {
    "app",
    "assets",
    "cards",
    "cards_exemplo",
    "config",
    "output",
    "prompts",
    "scripts",
    "terraform",
    "roteiros",
}
