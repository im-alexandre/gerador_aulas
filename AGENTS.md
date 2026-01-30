# Diretrizes do Repositório

## Estrutura do Projeto & Organização dos Módulos
- Raiz: `pipeline.py` (execução fim a fim).
- Lógica da aplicação: `app/pipeline_core.py` (pipeline), `app/browser.py` (browser), `app/` (módulos), `app/scripts/` (scripts CLI).
- Configs e prompts: `app/config/`, `app/prompts/`.
- Dados do curso: `curso_*/` (DOCX, `cards/`, `cards_exemplo/`).
- Saídas: `app/output/<curso>/saida.txt` (respostas em modo append).

## Comandos de Build, Testes e Desenvolvimento
- Pipeline completo (GPT → Gamma → polling), na raiz:
  - `python .\pipeline.py --curso-dir .\curso_exemplo_testes_software --folder-id <id> --poll-interval 15 --max-wait-minutes 0`
  - Gera cards, envia ao Gamma e consulta até `completed`.
- Apenas cards (na raiz):
  - `python .\app\scripts\gera_cards.py --root .\curso_exemplo_testes_software --export-dir .\curso_exemplo_testes_software\cards`
  - Lê DOCX nas subpastas, grava `cards.md` e exporta `*_card.md`.
- Apenas Gamma (na raiz):
  - `python .\app\scripts\gamma_create_from_template.py`
  - Usa `COURSE_DIR` para localizar `cards_exemplo/`.
- Consultar status de geração:
  - `python .\app\scripts\consulta_geracoes.py <generation_id>`
  - Imprime a resposta bruta e o status extraído.

## Estilo de Código & Convenções de Nome
- Python: 4 espaços de indentação, snake_case para variáveis e funções.
- Mantenha prompts e instruções em `app/prompts/`, chaves/configs em `app/config/`.
- Prefira caminhos explícitos nos configs (ex.: `app/config/config.json`).

## Diretrizes de Testes
- Não há suíte de testes. Se adicionar, documente o framework e o comando aqui.

## Diretrizes de Commit & Pull Request
- Não há histórico Git disponível; convenções são desconhecidas.
- Use mensagens claras e orientadas a ação (ex.: “Adicionar validação do payload Gamma”).
- PRs devem incluir:
  - Resumo das mudanças e scripts afetados.
  - Atualização de configs/prompts quando houver mudança de contrato.
  - Exemplo de saída ou logs ao alterar chamadas de API.

## Segurança & Configuração
- `OPENAI_API_KEY` deve estar no ambiente para chamadas GPT.
- A chave do Gamma é lida em `app/config/chave_api_gamma.txt`; não commitar segredos reais.
- Revise `app/config/api_config.json` e `app/config/config.json` antes de rodar.

## Como adicionar novos cursos
- Crie um diretório na raiz com o padrão `curso_nome_do_curso/`.
- Adicione `cards/` e `cards_exemplo/` dentro do curso.
- Copie os DOCX do curso para `curso_*/`.
- Rode `python .\pipeline.py --curso-dir .\curso_nome` (ou defina `COURSE_DIR`).
