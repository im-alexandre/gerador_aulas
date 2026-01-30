# Geração de Cards para Gamma — MODO PRAGMÁTICO

## CONTEXTO

- Existem **2 arquivos DOCX anexados**.
- Ao abrir os docx, dê atenção especial às IMAGENS
  - Abra-as
  - verifique seu conteúdo visual
  - busque por código para inserir no cartão
  - se não houver código tente gerar uma descrição dela para inserir na nota
- Você **DEVE** abrir e ler ambos usando o python tool.
- Um arquivo contém o conteúdo do vídeo.
- O outro contém o ROT (com sinopse).

Retorne **APENAS** o Markdown final.

---

## ESTRUTURA DOS CARDS (SIMPLES)

- Gere entre **6 e 10 cards**.
- Cada card DEVE conter:
  1. Título
  2. Texto corrido **bem curto!!!** (no máximo duas frases)
  3. Equilibrar texto corrido (curto) com tópicos.

---

## CÓDIGO (REGRA FLEXÍVEL, MAS OBRIGATÓRIA)

- Se houver **código em TEXTO**, copie integralmente.
- Se houver **imagem contendo código**:
  - **RECONSTRUA o código por inferência visual**, o mais fiel possível.
  - Abra cada imagem, identifique se ela possui código (mesmo que pequeno)
  - Transcreva o código na íntegra para o respectivo slide
  - Insira o código em Markdown utilizando ``.
  - Logo acima do código, insira:

> **[CÓDIGO EXTRAÍDO DE IMAGEM — REVISAR]**

⚠️ É melhor trazer código aproximado do que não trazer código nenhum!

---

## IMAGENS SEM CÓDIGO

- Se houver **imagem conceitual** (diagramas, telas, fluxos):
  - NÃO descreva a imagem.
  - NÃO crie conteúdo a partir dela.
  - Insira no texto do card correspondente, exatamente:

> **[NOTA PARA REVISÃO] Há imagem conceitual associada a este conteúdo.**

---

## RESTRIÇÕES

- Não invente conceitos que não estejam no material.
- Não cite mercado, níveis profissionais ou práticas externas.
- Se algo estiver confuso, **prefira ser superficial**.
- utilize apenas conceitos presentes no conteúdo

---

## CARD INICIAL

- O primeiro card deve conter **apenas o nome do vídeo** (conforme ROT).

---

## Vídeos de INTRODUÇÃO

- Videos cards baseados em arquivos contendo "vidint" devem ser reduzidos, apenas citando os conceitos principais do material.
- A idéia é apenas citar os conceitos, pois eles serão detalhados em outros conteúdos
