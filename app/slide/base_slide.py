from __future__ import annotations

"""
Slides + registry de validação.

Este módulo centraliza:
- Quais tipos de slide existem (kind="standard", "code", "title", etc.)
- Como cada tipo é validado
- Um ponto único para validar o JSON completo do plano

===========================================================================
COMO CRIAR UM NOVO TIPO DE SLIDE (MUITO IMPORTANTE)
===========================================================================

Exemplo: um slide "diagram" que aceita:
- image (vinda do docx), OU
- image.intent (para geração em outro passo)

1) Crie a classe em seu próprio arquivo dentro de app/slide/
   (veja outros slides ou use app/slide/diagram_slide.py como template):

    from app.slide.base_slide import BaseSlide, register_slide

    @register_slide
    class DiagramSlide(BaseSlide):
        KIND = "diagram"

        @classmethod
        def validate(cls, slide: dict, assets_base: Path, idx: int) -> list[str]:
            errors = cls.validate_common(slide, idx)
            # "diagram" usa regras parecidas com "standard", mas pode dispensar bullets
            image = slide.get("image")
            intent = image.get("intent")
            if intent is not None:
                errors += cls.validate_image_intent(intent, idx)
            if image:
                errors += cls.validate_image(image, assets_base, idx)
            if not image or (not image.get("path") and not image.get("intent")):
                errors.append(
                    f"Slide {idx}: diagram exige image.path ou image.intent."
                )
            return errors

2) Garanta que o módulo do novo slide seja importado:

   - Opção A (recomendada): importe no app/slide/__init__.py
   - Opção B: importe em app/slide/base_slide.py junto aos demais

   Isso é necessário porque o decorator @register_slide registra o tipo
   quando o módulo é carregado.

3) Atualize o renderer (IMPORTANTE):
   O renderer decide qual layout do PPTX será usado para cada kind.
   Se você adicionar um novo kind, precisa atualizar:
     - app/pptx_renderer.py
   para renderizar o novo tipo corretamente.

4) Atualize a documentação:
   - CRIA_APRESENTACOES.md (contrato)
   - README.md (execução + troubleshooting)

Notas:
- A validação deve ser rígida o suficiente para bloquear saída inválida,
  mas não tão rígida a ponto de bloquear variações válidas.
- Prefira usar helpers do BaseSlide para manter mensagens consistentes.
"""

from pathlib import Path
from typing import Any

class BaseSlide:
    """Validador base com checagens comuns a todos os tipos de slide."""

    KIND = "base"
    LAYOUT_NAME: str | None = None

    @classmethod
    def validate_common(cls, slide: dict, idx: int) -> list[str]:
        """Valida campos comuns a todos os tipos de slide."""
        errors: list[str] = []

        slide_id = slide.get("slide_id")
        if not isinstance(slide_id, str) or not slide_id.strip():
            errors.append(f"Slide {idx}: slide_id ausente ou inválido.")

        title = slide.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"Slide {idx}: title ausente ou inválido.")

        bullets = slide.get("bullets", [])
        if bullets is None:
            bullets = []
        if not isinstance(bullets, list):
            errors.append(f"Slide {idx}: bullets deve ser uma lista.")
        else:
            for b_idx, bullet in enumerate(bullets, 1):
                if not isinstance(bullet, str) or not bullet.strip():
                    errors.append(
                        f"Slide {idx}: bullet {b_idx} inválido ou vazio."
                    )

        return errors

    @staticmethod
    def validate_image_intent(value: Any, idx: int) -> list[str]:
        """Valida image.intent quando presente."""
        if not isinstance(value, str) or not value.strip():
            return [f"Slide {idx}: image.intent inválido."]
        return []

    @staticmethod
    def validate_image(image: Any, assets_base: Path, idx: int) -> list[str]:
        """Valida objeto image com source/path e existência do arquivo."""
        errors: list[str] = []
        if not isinstance(image, dict):
            return [f"Slide {idx}: image deve ser objeto."]

        source = image.get("source")
        if not isinstance(source, str) or not source.strip():
            errors.append(f"Slide {idx}: image.source ausente.")

        path = image.get("path")
        if not isinstance(path, str) or not path.strip():
            errors.append(f"Slide {idx}: image.path ausente.")
        elif not (assets_base / path).exists():
            errors.append(f"Slide {idx}: image.path não encontrado ({path}).")

        return errors

    @classmethod
    def validate(cls, slide: dict, assets_base: Path, idx: int) -> list[str]:
        """Sobrescreva nas subclasses para validação específica por kind."""
        return cls.validate_common(slide, idx)

    @classmethod
    def render(cls, slide: dict, dst_slide, assets_base: Path, ph_map: dict) -> None:
        """Sobrescreva nas subclasses para renderização específica."""
        return None


SLIDE_REGISTRY: dict[str, type["BaseSlide"]] = {}


def register_slide(slide_cls: type["BaseSlide"]) -> type["BaseSlide"]:
    """Registra uma classe de slide no registry global."""
    SLIDE_REGISTRY[slide_cls.KIND] = slide_cls
    return slide_cls


def load_default_slides() -> None:
    """Carrega os tipos de slide padrão (registro via import)."""
    from app.slide import code_slide, standard_slide, title_slide  # noqa: F401


def get_slide_class(kind: str) -> type["BaseSlide"] | None:
    """Retorna a classe registrada para o kind informado."""
    if not SLIDE_REGISTRY:
        load_default_slides()
    return SLIDE_REGISTRY.get(kind)


def validate_plan(plan: dict, assets_base: Path) -> list[str]:
    """Valida o JSON completo (contrato + regras por slide)."""
    errors: list[str] = []

    if not isinstance(plan, dict):
        return ["Plano não é um objeto JSON."]

    for key in ("module", "nucleus", "slides"):
        if key not in plan:
            errors.append(f"Campo obrigatório ausente: {key}")

    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        errors.append("Campo slides deve ser uma lista não vazia.")
        return errors

    # Garante que os tipos padrão estão registrados (import side effects).
    if not SLIDE_REGISTRY:
        load_default_slides()

    for idx, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            errors.append(f"Slide {idx}: item não é objeto.")
            continue

        kind = slide.get("kind", "standard")
        slide_cls = SLIDE_REGISTRY.get(kind)
        if not slide_cls:
            errors.append(f"Slide {idx}: kind inválido ({kind}).")
            continue

        errors.extend(slide_cls.validate(slide, assets_base, idx))

    return errors
