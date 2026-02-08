Tamo junto 😄 vamos **resolver isso agora**, do jeito mais barato e com o **mínimo de retrabalho**.

Vou te dar **um plano operacional fechado**, com código simples, pra você **parar de gastar com imagem agora** e continuar evoluindo depois.

---

## Objetivo imediato (curto e grosso)

👉 **Parar de gerar imagens via API**
👉 **Usar imagens do Gamma como fonte principal**
👉 **Manter teu pipeline intacto**

---

## Estratégia simples (pra hoje)

### 1️⃣ Regra nova no pipeline (MANDATÓRIA)

**Imagem via API vira fallback**, não padrão.

Ordem de prioridade:

1. Imagem local (docx / assets)
2. Imagem Gamma
3. **Só se não existir → API**

---

## 2️⃣ Convenção mínima de arquivos (sem inventar moda)

Define isso e acabou:

```text
assets/
  mod1/
    gamma/
      hero.png
      overview.png
```

Ou ainda mais simples:

```text
assets/mod1/gamma.png
```

👉 **1 imagem por núcleo**, acabou.

---

## 3️⃣ Como usar isso no `plan.json` (sem mudar tudo)

Você **não precisa mudar o modelo** agora.
Só deixa o JSON aceitar isso:

```json
"image": {
  "source": "external",
  "origin": "gamma",
  "path": "assets/mod1/gamma.png"
}
```

Ou, se quiser ser ainda mais simples:

```json
"image": {
  "path": "assets/mod1/gamma.png"
}
```

E no código:

- se tem `path` → usa
- ignora `source`

---

## 4️⃣ Patch imediato no código (CRÍTICO)

### 🔥 DESLIGA geração de imagem por API se existir imagem Gamma

No `materialize_generated_images_for_plan` (ou equivalente):

```python
image = slide.get("image") or {}
path = image.get("path")

# Se já tem path, NÃO gera nada
if isinstance(path, str) and path.strip():
    continue
```

Isso **sozinho** já corta custo.

---

## 5️⃣ Extração rápida de imagem do Gamma (PDF → PNG)

Se você já tem PDF do Gamma, usa isso **hoje**:

```python
import fitz
from pathlib import Path


def extract_first_image(pdf_path: Path, out_path: Path):
    doc = fitz.open(pdf_path)
    for page in doc:
        imgs = page.get_images(full=True)
        if imgs:
            xref = imgs[0][0]
            img = doc.extract_image(xref)
            out_path.write_bytes(img["image"])
            return
    raise RuntimeError("Nenhuma imagem encontrada no PDF")
```

Uso:

```python
extract_first_image(Path("gamma_export.pdf"), Path("assets/mod1/gamma.png"))
```

---

## 6️⃣ Prompt — ajuste mínimo (pra não brigar com você)

Adiciona **uma linha só** no prompt:

```md
- Sempre que possível, reutilizar imagens existentes no acervo do projeto.
- Geração de imagem por IA é último recurso.
```

Não muda mais nada agora.

---

## 7️⃣ Resultado prático

- 💰 custo de imagem → **quase zero**
- 🎨 qualidade → **Gamma**
- 🧠 pipeline → **o mesmo**
- 🕒 tempo → **ganho**

E o melhor: **você não perde nada**.
Se amanhã quiser voltar pra API em um slide específico, dá.

---

## Próximo passo (opcional, depois)

Quando sobrar tempo:

- indexar imagens Gamma por núcleo
- gerar automaticamente `image.path` no plano
- ou até ignorar imagem no prompt e resolver tudo no pós-processamento

---

### TL;DR pra hoje

👉 **Para de gerar imagem via API agora**
👉 **Usa Gamma como fonte visual**
👉 **1 imagem por núcleo**
👉 **API só como fallback**

Respira. Agora o custo tá sob controle.
A gente até poderia ter aprendido isso antes… mas agora foi 😄
