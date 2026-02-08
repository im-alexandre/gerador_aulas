# Slides

Este diretório contém **todos os tipos de slides** e suas regras de validação
e renderização. A ideia é simples:

1. O LLM gera um JSON com `slides[]`
2. Cada item tem `kind`
3. O `kind` aponta para uma classe que:
   - valida a estrutura desse slide
   - renderiza o slide no PPTX usando shapes nomeados

---

## Visão geral do fluxo

1. `validate_plan(...)` percorre os slides e chama a classe correta.
2. `render_from_plan(...)` usa a mesma classe para renderizar.

Isso garante que **a validação e a renderização sejam consistentes**.

---

## Placeholders por nome (template)

O renderer usa **nomes de placeholders** dos slides-sentinela para gerar um
mapping de `idx`. Para cada layout (title/standard/code), mantenha um slide
exemplo no template com placeholders nomeados:

- `title`
- `subtitle` (opcional)
- `pip` (opcional)
- `bullets`
- `code`
- `image`

Esses nomes são lidos no slide exemplo para descobrir o `placeholder_format.idx`,
e o renderer usa o `idx` para preencher slides gerados.

O mapping é salvo como `*_map.json` ao lado do template.
Se você trocar o template, apague o `_map.json` para forçar a regeneração.

Se o placeholder não existir no layout escolhido, aquele elemento **não é renderizado**.

---

## Layouts por kind

Cada classe de slide define `LAYOUT_NAME`. Esse nome precisa existir no template:

- `TitleSlide` → `LAYOUT_NAME = "title"`
- `StandardSlide` → `LAYOUT_NAME = "standard"`
- `CodeSlide` → `LAYOUT_NAME = "code"`

Se você criar um novo kind, **é obrigatório criar um layout com esse nome**
no template PPTX.

---

## Contrato de imagem (resumo)

Para slides `standard`, o campo `image` é obrigatório:

- `source="docx"` exige `path` e proíbe `intent`
- `source="generated"` exige `intent` e `path` é preenchido **após**
  a geração das imagens (não deve vir do LLM)

---

## Arquivos principais

- `base_slide.py`: base de validação + registro + `validate_plan`
- `render_utils.py`: helpers de renderização (textos, bullets, imagens)
- `title_slide.py`: slide de capa (kind="title")
- `standard_slide.py`: slide padrão com lead, bullets e imagem/intent
- `code_slide.py`: slide de código sem imagem
- `diagram_slide.py`: exemplo pronto para copiar

---

## Como criar um novo slide (passo a passo completo)

### 1) Crie o arquivo do slide

Exemplo: `app/slide/diagram_slide.py`

```python
from app.slide import BaseSlide, register_slide
from app.slide.render_utils import (
    get_shape_by_name,
    resolve_image_path,
    set_lead_with_bullets,
    set_text,
)

@register_slide
class DiagramSlide(BaseSlide):
    KIND = "diagram"
    LAYOUT_NAME = "layout_diagram"

    @classmethod
    def validate(cls, slide: dict, assets_base, idx: int) -> list[str]:
        errors = cls.validate_common(slide, idx)
        image = slide.get("image")
        intent = image.get("intent")
        if intent is not None:
            errors += cls.validate_image_intent(intent, idx)
        if image:
            errors += cls.validate_image(image, assets_base, idx)
        if not image and not intent:
            errors.append(f"Slide {idx}: diagram exige image.intent.")
        return errors

    @classmethod
    def render(cls, slide: dict, dst_slide, assets_base) -> None:
        set_text(get_shape_by_name(dst_slide, "title"), slide.get("title", ""))
        bullets = slide.get("bullets") or []
        lead = slide.get("lead") or ""
        set_lead_with_bullets(get_shape_by_name(dst_slide, "bullets"), lead, bullets)

        image = slide.get("image") or {}
        image_path = image.get("path")
        if image_path:
            image_box = get_shape_by_name(dst_slide, "image")
            if image_box:
                img_path = resolve_image_path(assets_base, image_path)
                if img_path.exists():
                    dst_slide.shapes.add_picture(
                        str(img_path),
                        image_box.left,
                        image_box.top,
                        image_box.width,
                        image_box.height,
                    )
```

### 2) Registre o módulo (import obrigatório)

O decorator `@register_slide` só funciona **quando o módulo é carregado**.
Por isso, você precisa importar o módulo em algum lugar carregado na execução.

Recomendado: importar no `app/slide/__init__.py`

```python
# app/slide/__init__.py
from app.slide.diagram_slide import DiagramSlide
```

### 3) Crie o layout no template PPTX

No PowerPoint:

1. Abra o template
2. Vá em `Exibir > Slide Mestre`
3. Crie um layout chamado exatamente `layout_diagram`
4. Adicione shapes com os nomes:
   - `title`
   - `bullets`
   - `image` (se o tipo usar imagem)

### 4) Atualize o contrato

Inclua o novo `kind` em:

- `CRIA_APRESENTACOES.md`
- `contrato_pipeline_aulas.md` (se necessário)

---

## Checklist rápido para novos kinds

- [ ] Classe criada com `KIND` e `LAYOUT_NAME`
- [ ] `validate` implementado
- [ ] `render` implementado
- [ ] Módulo importado (registro ativo)
- [ ] Layout criado no PPTX com shapes nomeados
- [ ] Documentação atualizada

---

## Atualização do contrato no prompt (obrigatória)

Todo novo `kind` precisa estar descrito no contrato usado pelo LLM
(`app/prompts/prompt_gpt.md`). Isso inclui:

- Nome do `kind`
- Campos obrigatórios do slide
- Campos proibidos (se houver)
- Exemplo mínimo de JSON para o novo tipo
- Regras de renderização (ex.: uso de imagem, lead, código)

**Não altere o `app/prompts/prompt_gpt.md` sem alinhamento**, pois ele é usado
diretamente nas requisições ao modelo.
