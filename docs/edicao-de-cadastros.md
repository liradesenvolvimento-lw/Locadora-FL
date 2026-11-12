# Edição dos cadastros

Branch: `codex/inicio-trabalho`.

## Uso

- **Dashboard / Frota / Manutenções:** botão **Editar** na linha do veículo. Inclui KM atual, KM da última revisão, identificação, carga e status.
- **Contratos & Clientes:** edição de contratos e lista de transportadoras com edição dos dados de contato.
- **Checklist:** lista de vistorias registradas abaixo do formulário, com edição de KM, tipo, combustível, itens de inspeção, observações e vínculos.
- **Financeiro:** edição de custos, valores, vencimentos, competência, parcelas e status.

O editor carrega o registro atual, permite cancelar e envia somente os campos alterados. Campos opcionais podem ser limpos. IDs e datas de criação permanecem internos; a foto de evidência existente é preservada ao editar os demais campos. Nenhuma migração de banco é necessária.

KM pode ser corrigido para cima ou para baixo, desde que não seja negativo e o KM da última revisão não supere o atual. A correção da última vistoria reflete no odômetro apenas quando ele ainda corresponde à leitura original. Vistorias históricas, troca do veículo da vistoria e odômetros corrigidos separadamente não são propagados automaticamente: nesses casos, ajuste a Frota explicitamente. A edição de tipo de vistoria não repete eventos de entrega/devolução nem altera o status da frota.

Ao trocar o veículo ou o status de um contrato, a API ajusta a alocação. Bloqueia a ativação/troca para veículo em manutenção ou com outro contrato ativo e impede trocar um veículo com vistorias vinculadas ao contrato sem antes corrigir esses vínculos. Não altera as regras antigas de criação ou de check-in, cuja revisão está proposta no relatório.

## Implementação

- `editing.py`: consultas individuais, listagem de vistorias e PATCH autenticados para os cinco cadastros.
- `edit_schemas.py`: validação dos valores consolidados, incluindo campos ausentes versus nulos.
- `editing.js`: editor compartilhado, listas auxiliares, erros e atualização das tabelas.
- `index.html`: ações de edição e API na mesma origem da página. Em desenvolvimento, abrir pelo servidor FastAPI, não diretamente como arquivo HTML. Assim, a cópia local usa sua API local.

## Validação local

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
```

A suíte usa bancos SQLite isolados, autenticação e requisições HTTP de teste. Verifica os cinco cadastros, persistência, valores nulos, campos não editados, duplicidades, dados inválidos, relacionamentos, alocação, histórico de vistorias e reflexos no dashboard. PostgreSQL de produção não foi exercitado.

O teste de navegador inicia seu próprio servidor com banco temporário, sem acesso à produção:

```sh
pip install playwright
python -m playwright install chromium
python tests/verify_browser.py
```

Na máquina utilizada nesta entrega (Python 3.9), foi necessário instalar `cryptography==44.0.3` no ambiente temporário para usar uma distribuição binária compatível; as dependências de produção não foram modificadas. O Dockerfile do projeto usa Python 3.12.

Os upgrades estão somente descritos em `analise-e-upgrades.md`.
