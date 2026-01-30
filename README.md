# Pipeline GPT → Gamma

Automatiza a geração de cards a partir de DOCX do curso (GPT) e cria apresentações no Gamma via template, consultando até todas as gerações concluírem.

## Início Rápido
Na raiz do repositório:
```powershell
python .\pipeline.py
```

Para apontar para um curso específico (argumento):
```powershell
python .\pipeline.py --curso-dir .\curso_exemplo_testes_software
```

Também é possível usar a variável de ambiente:
```powershell
$env:COURSE_DIR="D:\desenvolvimento_local\criador_aulas\curso_exemplo_testes_software"
python .\pipeline.py
```

## Estrutura do Repositório
- `pipeline.py`: entrada principal (GPT → Gamma → polling).
- `app/pipeline_core.py`: lógica do pipeline.
- `app/browser.py`: abertura do navegador.
- `app/`: código da aplicação, configs, prompts e scripts auxiliares.
- `curso_*/`: conteúdo do curso (DOCX + `cards/` + `cards_exemplo/`).

## Configuração
- `app/config/config.json`: endpoint do Gamma + caminhos.
- `app/config/api_config.json`: headers/corpo padrão do Gamma.
- `app/config/chave_api_gamma.txt`: chave da API do Gamma.
- `app/prompts/prompt_gpt.md`: prompt do GPT.
- `app/prompts/instrucoes_gerais_gamma.md`: instruções de formatação do Gamma.

## Comandos Úteis
- Pipeline completo (sequencial):
  - `python .\pipeline.py --curso-dir .\curso_exemplo_testes_software --folder-id <id> --poll-interval 15 --max-wait-minutes 0`
- Apenas cards:
  - `python .\app\scripts\gera_cards.py --root .\curso_exemplo_testes_software --export-dir .\curso_exemplo_testes_software\cards`
- Apenas Gamma:
  - `python .\app\scripts\gamma_create_from_template.py`
- Consultar status de geração:
  - `python .\app\scripts\consulta_geracoes.py <generation_id>`

## Saída
- Logs são anexados em `app/output/<curso>/saida.txt` com timestamp e `generation_id`.

## Como adicionar novos cursos
1) Crie um diretório na raiz com o padrão `curso_nome_do_curso/`.
2) Dentro dele, crie as pastas:
   - `cards/` (saída dos cards gerados)
   - `cards_exemplo/` (cards prontos para testes manuais)
3) Copie os DOCX do curso para dentro do diretório `curso_*` (ex.: `curso_novo/`).
4) Rode o pipeline a partir da raiz:
   - `python .\pipeline.py`
