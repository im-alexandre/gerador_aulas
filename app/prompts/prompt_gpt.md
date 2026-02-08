# PROMPT — PLANEJAMENTO DE SLIDES (JSON · CUMPRIMENTO ESTRITO)

## OBJETIVO

Ler dois DOCX (conteúdo + roteiro) e retornar APENAS um JSON válido com o plano de slides,
conforme o contrato abaixo. Nao inclua nenhum texto fora do JSON.

## 1. ENTRADAS

Você receberá exatamente 2 arquivos DOCX anexados:

1. CONTEUDO DO VIDEO (com tags de imagem no corpo, ex.: [[IMG:assets/img_0001.png]])
2. ROT (roteiro: contem sinopse e nome do video)

### 0. LEITURA OBRIGATORIA

Voce DEVE abrir e ler os dois DOCX usando python tool.

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
  "module": "mod1",
  "nucleus": "nc3",
  "slides": [
    {
      "slide_id": "s00",
      "kind": "title",
      "title": "Resources, Variables e Outputs no Terraform"
    },
    {
      "slide_id": "s01",
      "kind": "standard",
      "title": "Infraestrutura como Código no fluxo DevOps",
      "lead": "A Infraestrutura como Código integra a gestão de ambientes ao fluxo DevOps, permitindo automação, padronização e maior previsibilidade nas entregas.",
      "bullets": [
        "Infraestrutura versionada reduz divergências entre ambientes",
        "Automação do provisionamento elimina etapas manuais, tornando o fluxo mais previsível",
        "Padronização de ambientes sustenta testes confiáveis ao longo do pipeline",
        "Integração com controle de versão melhora rastreabilidade das mudanças"
      ],
      "image": {
        "source": "docx",
        "path": "assets/img_0001.png"
      }
    },
    {
      "slide_id": "s02",
      "kind": "code",
      "title": "Terraform — definição declarativa de recursos",
      "code": {
        "language": "hcl",
        "text": "resource \"aws_instance\" \"exemplo\" {\n  ami           = \"ami-123456\"\n  instance_type = \"t3.micro\"\n}"
      },
      "bullets": [
        "Recurso declara o estado desejado de uma instância EC2",
        "Definição declarativa descreve o que deve existir, não como criar",
        "Alterações no código permitem controle e rastreabilidade das mudanças",
        "Aplicação automatizada reduz dependência de intervenção manual"
      ]
    },
    {
      "slide_id": "s03",
      "kind": "standard",
      "title": "Idempotência e previsibilidade no provisionamento",
      "lead": "A idempotência garante que múltiplas execuções produzam o mesmo estado final, reduzindo riscos operacionais e surpresas em produção.",
      "bullets": [
        "Execuções repetidas convergem para o mesmo estado desejado, sem efeitos colaterais",
        "Falhas parciais podem ser reexecutadas com segurança",
        "Ambientes ficam reprodutíveis entre times e pipelines",
        "Auditoria e rollback se tornam mais simples e confiáveis"
      ],
      "image": {
        "source": "generated",
        "intent": "Diagrama simples mostrando múltiplas execuções convergindo para o mesmo estado final"
      }
    }
  ]
}
```

## 4. REGRAS DE PLANEJAMENTO

- Gere entre 6 slides (code + standard) + 1 (title).
- Só ultrapasse esse limite se existirem mais subseções no conteúdo
- Mantenha a ordem do conteudo.
- Cada slide trata de um unico foco conceitual.
- Nao invente conteudo fora do material.
- Use o titulo do nucleo conceitual para criar o título do slide

## 5. REGRAS EDITORIAIS DOS SLIDES

- Slides "standard" devem ter lead
- Nesse caso, gere 3 bullets.
- Bullets devem ser frases técnicas resumidas, sem verbo, tratando de UMA única ideia.
- Sempre que possível, utilize caracteres, símbolos na construção:
  “causa -> consequência".
  Ex.: "Maior automação -> menos erros humanos".
- Um bullet pode conter causa e consequência, mas não deve concluir o assunto nem funcionar como observação final.
- Não gere observações finais, notas ou texto corrido fora do campo "lead".

## REGRA ESPECIAL — mod0_vidint (VÍDEO INTRODUTÓRIO)

Quando o núcleo for "mod0_vidint", aplique as regras abaixo.
Essas regras SOBRESCREVEM regras gerais em caso de conflito.

### Escopo de conteúdo

- O mod0_vidint é um vídeo introdutório curto, baseado no CONJUNTO do material.
- NÃO deve reutilizar imagens associadas a outros núcleos.
- NÃO deve fazer referência explícita a conceitos específicos de núcleos posteriores.
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

- Se nucleus == "mod0_vidint":
  - Nenhum slide pode conter image.source="docx".
  - Todas as imagens devem ser geradas.
  - Conteúdo excessivamente detalhado deve ser evitado.

### Densidade e legibilidade (REGRA GLOBAL)

- Bullets devem ter no máximo 60 caracteres.
- Preferir sintagmas nominais (frases sem verbo).
- Evitar explicações, exemplos e justificativas.
- Texto do slide NÃO deve ser autoexplicativo.

- O texto do slide deve exigir explicação oral para ser plenamente compreendido.
- Slides devem funcionar como apoio visual, não como material de leitura.
- Evitar artigos, conectivos e orações subordinadas.
- Preferir palavras-chave ou expressões nominais curtas.

- Slides NÃO devem conter:
  - blocos extensos de texto
  - frases longas com múltiplas orações
  - explicações completas ou autoexplicativas
  - texto que possa ser lido como um parágrafo contínuo
- O slide deve funcionar como apoio visual à narração, não como material de leitura.
- Se o conteúdo exigir explicação longa, ele DEVE ser dividido em múltiplos slides.

- Slides com excesso de texto, independentemente do kind, devem ser considerados inválidos.
- O modelo deve preferir criar mais slides a condensar conteúdo demais em um único slide.

### Regra de lead (OBRIGATÓRIA)

- O lead deve ter no máximo 120 caracteres.
- O lead serve como contexto mínimo para o slide, não como explicação completa.
- Deve ser uma única frase curta, clara e evocativa.
- Se ultrapassar 120 caracteres, o texto DEVE ser reescrito até caber.
- O lead pode ser ligeiramente mais explicativo que os bullets, mas ainda deve funcionar como gatilho de memória.
- Se o conteúdo puder ser lido como texto corrido sem a fala do professor, o lead está longo demais.
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

- Cada slide deve conter um "lead", com até 2–3 frases curtas de contextualização.
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
- O texto do campo "title" corresponde ao nome do núcleo conceitual.
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
- Se o slides_plan.json possuir menos de 4 slides, refaça
