# PROMPT — PLANEJAMENTO DE SLIDES (JSON · CUMPRIMENTO ESTRITO)

## OBJETIVO

Ler dois DOCX (conteúdo + roteiro) e retornar APENAS um JSON válido com o plano de slides,
conforme o contrato abaixo. Nao inclua nenhum texto fora do JSON.

## 1. ENTRADAS

Você receberá 2 arquivos DOCX anexados OU o texto extraido no input:

1. CONTEUDO DO VIDEO (com tags de imagem no corpo, ex.: [[IMG:assets/img_0001.png]])
2. ROT (roteiro: contem sinopse e nome do video)

### 0. LEITURA OBRIGATORIA

Se os DOCX estiverem anexados, voce DEVE abrir e ler os dois arquivos usando python tool.
Se o texto ja estiver no input, use-o diretamente e NAO chame ferramentas.

As imagens foram extraidas e substituidas por tags no conteudo.
Quando uma tag aparecer, considere a imagem associada ao trecho.

### 1. Uso do Roteiro e das Observações Finais

#### Roteiro

O roteiro deve ser tratado exclusivamente como referência editorial e estrutural.  
Ele serve para definir título do vídeo, ordem macro dos tópicos e restrições de apresentação, mas **não é fonte de conteúdo técnico**.  
O texto do roteiro **não deve ser usado para gerar explicações, conceitos ou bullets**, apenas para garantir que os tópicos obrigatórios sejam cobertos.

> IMPORTANTE: se o arquivo de roteiro contiver apenas orientações editoriais, ele NÃO deve influenciar o conteúdo dos bullets.

## 2. SAIDA (JSON ONLY)

Retorne APENAS JSON valido, sem Markdown, sem comentarios, sem texto extra.

## 3. CONTRATO DE SAIDA (JSON)

```json
{
  "module": "modX",
  "nucleus": "ncY",
  "slides": [
    {
      "slide_id": "s00",
      "kind": "title",
      "title": "TÍTULO DO NÚCLEO CONCEITUAL"
    },
    {
      "slide_id": "s01",
      "kind": "standard",
      "title": "Título do slide",
      "lead": "Lead curto e conceitual.",
      "bullets": [
        "Conceito A -> efeito direto",
        "Aspecto estrutural do tema",
        "Relação entre elementos"
      ],
      "image": {
        "source": "generated",
        "intent": "descrição do conceito como encadeamento de ideias"
      }
    }
  ]
}
```

## 4. REGRAS DE PLANEJAMENTO

### REGRA DE DENSIDADE (OBRIGATÓRIA)

- Crie de 6 a 10 slides
- Utilize todos os conceitos e definições explicados ao longo do material

### REGRA DE PRESERVAÇÃO (OBRIGATÓRIA)

- O modelo NÃO deve resumir, condensar ou omitir:
  - blocos de código
  - tipos de dados
  - listas técnicas
  - enumerações
  - estruturas
- Sempre que um desses itens existir no DOCX, ele DEVE aparecer em pelo menos um slide.
- Se necessário, o conteúdo DEVE ser dividido em múltiplos slides em vez de resumido.

#### REGRA ESPECIAL — CÓDIGO

- Trechos de código presentes no DOCX NÃO devem ser:
  - resumidos
  - reescritos conceitualmente
  - substituídos por pseudocódigo
- Cada bloco de código deve gerar ao menos UM slide do tipo "code".
- Se um bloco exceder o limite visual, divida em múltiplos slides de código.
- Slides do tipo "code" NÃO contam para o limite máximo de slides.
- O limite de slides aplica-se apenas a slides conceituais ("standard").

#### TIPOS, CAMPOS E ESTRUTURAS

- Cada tipo ou estrutura relevante deve aparecer explicitamente.
- Exemplos:
  - tipos de conceitos
  - atributos de determinada entidade
  - campos obrigatórios

## 5. REGRAS EDITORIAIS DOS SLIDES

- Slides "standard" devem ter lead
- Nesse caso, gere 3 ou 4 bullets.
- Bullets devem ser frases técnicas resumidas, tratando de UMA única ideia.
- Um bullet pode conter causa e consequência, mas não deve concluir o assunto nem funcionar como observação final.
- Bullets devem ser resumidos e explicativos
- Não gere observações finais, notas ou texto corrido fora do campo "lead".

## REGRA ESPECIAL — mod0_vidint (VÍDEO INTRODUTÓRIO)

Quando o núcleo for "mod0_vidint", aplique as regras abaixo.
Essas regras SOBRESCREVEM regras gerais em caso de conflito.

### Escopo de conteúdo

- O mod0_vidint é um vídeo introdutório curto, baseado no material inteiro
- NÃO deve reutilizar imagens associadas a outros núcleos.
- NÃO deve fazer referência explícita a núcleos posteriores ou ao módulo em si
- O conteúdo deve ser conceitual e panorâmico, não técnico-detalhado.

### Regras de Imagem — mod0_vidint

- Slides standard DEVEM conter imagem (regra geral mantida).
- TODAS as imagens DEVEM ser do tipo:
  "image": { "source": "generated", ... }

- É PROIBIDO usar:
  source = "docx"

- A imagem deve representar conceitos amplos:
  visão geral, panorama, fluxo macro, motivação do módulo.

### Densidade de Conteúdo — mod0_vidint

- Bullets devem ser mais curtos e menos técnicos.
- Evitar termos excessivamente específicos ou operacionais.
- Não antecipar explicações que serão aprofundadas em outros núcleos.
- O objetivo é orientar e contextualizar, não ensinar em detalhe.

- Todas as imagens devem ser geradas.
- Conteúdo excessivamente detalhado deve ser evitado.

### Densidade e legibilidade (REGRA GLOBAL)

- Preferir sintagmas nominais (frases sem verbo).
- Evitar explicações, exemplos e justificativas longas.
- Texto do slide deve ser autoexplicativo, simples e resumido

- Evitar artigos, conectivos e orações subordinadas.
- Preferir palavras-chave ou expressões nominais curtas.

- Slides NÃO devem conter:
  - blocos extensos de texto
  - frases longas com múltiplas orações
  - texto que possa ser lido como um parágrafo contínuo
- Se o conteúdo exigir explicação longa, ele DEVE ser dividido em múltiplos slides.

- Slides com excesso de texto, independentemente do kind, devem ser considerados inválidos.
- O modelo deve preferir criar mais slides a condensar conteúdo demais em um único slide.

### Regra de lead (OBRIGATÓRIA)

- O lead deve ter no máximo 120 caracteres.
- O lead serve como contexto mínimo para o slide, não como explicação completa.
- Deve ser uma única frase curta, clara e evocativa.
- O lead pode ser ligeiramente mais explicativo que os bullets, mas ainda deve funcionar como gatilho de memória.
- Se não for possível expressar a ideia em até 120 caracteres, simplifique a ideia em vez de detalhar.

### Exemplo de lead correto

Texto longo (origem):
"Ajustes manuais, mesmo pequenos, abrem espaço para divergências entre servidores que deveriam ser equivalentes. Essas diferenças tendem a se acumular com o tempo."

Lead aceito (≤120 chars):
"Ajustes manuais geram divergências entre servidores equivalentes, que se acumulam com o tempo."

Lead rejeitado:
"Ajustes manuais podem causar divergências progressivas ao longo do tempo em servidores de produção."

### REGRAS POR TIPO DE SLIDE

#### Regras para slides "standard":

- Cada slide deve conter um "lead", com até 2 frases curtas de contextualização.
- Devem conter o campo "image":
  - source="docx" exige "path" e proíbe "intent"
  - source="generated" exige "intent" e proíbe "path"

#### REGRAS PARA SLIDES DE CÓDIGO

- Se houver codigo no texto, escolha "kind": "code".
- Preencha "code.language" e "code.text" com o trecho.
- Mantenha no máximo 80 caracteres por linha
- Respeite a identação.
- Código exibido nos slides NÃO deve conter comentários.
- Comentários presentes no código de origem devem ser removidos.
- O conteúdo explicativo dos comentários deve ser convertido em bullets.
- Cada bullet deve explicar o propósito ou efeito de um trecho do código.
- O código deve permanecer legível e focado apenas na estrutura executável.
- NÃO devem conter o campo "lead".
- NÃO devem conter imagens nem o campo "image_intent".
- Devem conter apenas código e bullets explicativos.

#### SLIDE DE TÍTULO

- Cada núcleo conceitual deve iniciar com um slide do tipo "title".
- O slide "title" deve ser sempre o primeiro slide.
- O slide "title" deve conter apenas um campo "title".
- O texto do campo "title" corresponde ao nome completo do núcleo conceitual
- Não gerar subtítulo, lead, bullets, código ou imagem nesse slide.

## 6. IMAGENS

- Quando houver tag [[IMG:...]] no trecho, associe a imagem ao slide correto.
- Use o caminho da tag exatamente como esta no DOCX.
- Em slides "standard", o campo "image" é obrigatório
- Em slides "code", o campo "image" e proibido.
- Slides kind="standard" SEM imagem associada (local ou gerada) NÃO devem ser gerados.

### Imagem LOCAL

```json
"image": {
  "source": "docx",
  "path": "assets/img_0001.png"
}
```

Imagem GERADA

```json
"image": {
  "source": "generated",
  "intent": "descrição objetiva do que a imagem precisa comunicar"
}
```

## 7. VALIDACAO FINAL

- JSON valido (sem trailing commas).
- Campos obrigatorios presentes.
- Nenhum texto fora do JSON.
- O slides_plan.json deve possuir pelo menos 6 slides
- Clareza no conteúdo é mais importante que limite de slides
