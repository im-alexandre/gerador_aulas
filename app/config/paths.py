from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_DIR.parent

PROMPT_MD = "prompts/prompt_gpt.md"
TEMPLATE_CATALOG = {
    "graduacao": "template_ppt_graduacao.pptx",
    "tecnico": "template_ppt_tecnico.pptx",
}
TEMPLATE_PPTX = TEMPLATE_CATALOG["graduacao"]
USER_INPUT_SLIDES = "prompts/user_input_slides.j2"
USER_INPUT_IMAGE = "prompts/user_input_imagem.j2"
OPENAI_KEY_PATH = "prompts/openai_api_key"

ASSETS_DIRNAME = "assets"
ROTEIROS_DIRNAME = "roteiros"
PLAN_JSON_NAME = "slides_plan.json"

if __name__ == "__main__":
    print(
        APP_DIR,
        PROJECT_ROOT,
        PROMPT_MD,
        TEMPLATE_CATALOG,
        TEMPLATE_PPTX,
        USER_INPUT_SLIDES,
        USER_INPUT_IMAGE,
        ASSETS_DIRNAME,
        ROTEIROS_DIRNAME,
        PLAN_JSON_NAME,
    )
