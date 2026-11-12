# Análise do Locadora-FL e propostas de evolução

Pesquisa: 12/11/2026. Escopo implementado nesta entrega: edição de cadastros. Todas as evoluções abaixo são propostas, sem implementação. A análise considera o código deste repositório; não houve acesso aos dados nem às configurações de produção.

## Diagnóstico do projeto

O produto atende uma locadora de utilitários que aloca veículos para transportadoras. A base contém veículos, clientes, contratos mensais, vistorias e custos fixos, com autenticação. FastAPI e SQLAlchemy servem a API; uma página HTML com JavaScript concentra a interface. O banco pode ser SQLite local ou PostgreSQL, conforme `DATABASE_URL`.

A ausência de edição era estrutural: havia POST/GET de coleções, mas nenhuma rota de atualização dos cinco cadastros operacionais. A tela também não listava transportadoras nem vistorias anteriores para permitir sua seleção.

### Limitações confirmadas no código e impacto

| Constatação | Evidência | Consequência / proposta |
|---|---|---|
| A franquia é mensal, mas o consumo considerado é acumulado desde o início do contrato. | `main.py`, `get_dashboard_summary`: `km_atual - km_inicial` comparado a `franquia_km_mensal`. | Após vários meses, alertas podem indicar excesso indevido. Criar leituras e fechamento por competência antes de automatizar cobrança. |
| O faturamento soma mensalidades dos contratos atualmente ativos; mês/ano filtram somente custos. | `get_dashboard_summary`. | Consultar um mês anterior não reconstrói sua receita. Separar receita prevista, faturada e recebida por competência. |
| Custos sem mês/ano ficam fora de filtros específicos. Não há calendário que gere recorrências. | Filtros por igualdade em `get_dashboard_summary`; `CustoFixoVeiculo`. | Um custo recorrente pode sumir da análise mensal. Definir recorrência e apropriação antes de chamar o painel de DRE. |
| A revisão usa intervalo fixo de 10.000 KM. Os alertas são gerados somente no loop de contratos ativos. | `main.py`, resumo; `index.html`, `carregarTabelaManutencao`. | Veículo disponível pode precisar de manutenção sem alertar no painel. Criar planos por modelo, tempo e KM. |
| O retorno da vistoria disponibiliza o veículo, mas não encerra seu contrato. A criação de contrato não verifica outra locação ativa. | `registrar_checklist` e `criar_contrato`. | Disponibilidade e receita podem divergir. Definir um fluxo único de entrega, substituição e devolução. As validações de troca na nova edição não corrigem esses fluxos antigos. |
| Foto existe no modelo, mas o formulário original não oferece captura. Não há assinatura nem comparação de avarias. | `Checklist` e `form-checklist-completo`. | A evidência operacional é limitada. Evoluir a vistoria móvel e a comparação entrega/retorno. |
| Não há perfis de acesso, histórico de alterações ou identificação do autor em cada alteração. | `Usuario`, autenticação e rotas. | Toda conta ativa tem o mesmo alcance operacional. Acrescentar permissões e trilha de auditoria. |
| Há segredo JWT e credenciais iniciais de desenvolvimento como fallback. | `auth.py`. | Verificar a configuração real de implantação e exigir configuração apropriada antes da expansão. Não é possível concluir pelo repositório se esses valores são usados em produção. |
| Não há mecanismo de migração versionada; valores monetários usam Float. | `create_all`, `models.py`. | Planejar migrações e Decimal/Numeric antes da expansão financeira. |

## Benchmark de produtos

As funcionalidades foram verificadas em fontes dos próprios fornecedores. Descrições comerciais indicam capacidades anunciadas, não resultados medidos nesta locadora. A prioridade proposta abaixo é nossa avaliação aplicada ao código e ao contexto de locação mensal.

| Produto | Capacidades verificadas | Aplicação ao projeto |
|---|---|---|
| **Locavia — Info Tecnologia** | Faturamento automático, financeiro e inadimplência, manutenção, documentos, multas e reservas RAC/Fleet. | Referência brasileira para integrar contrato, cobrança e operação. [Fonte oficial](https://infosistemas.com.br/locavia/) |
| **Fleetio** | Planos preventivos por KM, horas ou tempo; ordens de serviço, histórico e tratamento de falhas de inspeção. | Referência para transformar o alerta de revisão em trabalho planejado e acompanhado. [Manutenção](https://www.fleetio.com/solutions/fleet-maintenance-software) |
| **LOC1** | Faturamento, extrato de locação, ordens de serviço, despesas e rentabilidade por placa/contrato. | Referência para apuração financeira por veículo. A página consultada é de 2020; serve como evidência de funcionalidades descritas, sem presumir condições comerciais atuais. [Fonte oficial](https://blog.loc1.com.br/loc1-melhora-a-gestao-de-processos-de-locacao) |
| **Rent Centric** | Reservas, contratos digitais, assinaturas, vistoria móvel com fotos/vídeos e integração GPS. | Referência para entrega/devolução e experiência do cliente. As integrações americanas de habilitação e pedágio não devem ser presumidas compatíveis com o Brasil. [Fonte oficial](https://www.rentcentric.com/products/car-rental-software/) |
| **Sofit** | Combustível, pneus, documentos, multas, sinistros, app do condutor e importações. | Referência nacional para expandir o controle de despesas e o acompanhamento operacional. [Recursos oficiais](https://www.sofit4.com.br/recursos/) |

## Backlog recomendado

Complexidade relativa: baixa = extensão localizada; média = novas entidades e fluxos; alta = integração externa ou várias áreas afetadas. Não equivale a estimativa de prazo.

| Ordem | Upgrade proposto e primeira versão útil | Valor para Flávio | Complexidade / dependência | Como medir |
|---|---|---|---|---|
| **1** | **Fechamento mensal de KM:** leitura inicial/final por competência, franquia negociada, cálculo de excesso, revisão e fechamento. Correções após fechamento gerariam ajuste rastreável. | Reduz divergências e ajuda a recuperar receita de excedentes. | Média; definir ciclo contratual, rateio e acúmulo de franquia. | Contratos fechados no mês, ajustes e contestações de KM. |
| **2** | **Cobrança recorrente e contas a receber:** fatura mensal com mensalidade e excedentes, vencimento, baixa e inadimplência; depois Pix/boleto e conciliação. | Dá visibilidade ao dinheiro recebido e ao que falta cobrar. | Alta; depende do fechamento e da escolha do provedor. | Inadimplência, atraso médio e tempo gasto no fechamento. |
| **3** | **Manutenção preventiva e OS:** plano por KM/data, serviços, oficina, orçamento, aprovação, custo e conclusão, atualizando última revisão. | Reduz esquecimentos e permite acompanhar dias parados. | Média; cadastro de planos e oficinas. | Preventivas no prazo, indisponibilidade e custo de manutenção por KM. |
| **4** | **Resultado por veículo e contrato:** receitas e custos na mesma competência; margem, ocupação e custos por KM; depois depreciação e custo total de propriedade. | Mostra quais utilitários e contratos remuneram o investimento. | Média/alta; depende de receitas e custos confiáveis. | Margem por placa, custo/KM e ocupação por período. |
| **5** | **Vistoria móvel com evidências:** fotos por parte do veículo, comparação saída/retorno, identificação de responsável, assinatura e PDF. | Facilita conferência e discussão de avarias. | Média; armazenamento de arquivos e regras de retenção. | Vistorias completas, tempo de devolução e avarias recuperadas. |
| **6** | **Auditoria e perfis:** gestor, operação e financeiro; log de autor, data, campo, antes/depois e motivo nas correções de KM/valores. | Dá rastreabilidade às edições e delimita responsabilidades. | Média; identidade do usuário e permissões por operação. | Alterações rastreáveis e correções sem justificativa. |
| **7** | **Agenda de disponibilidade:** calendário de locações/manutenções, bloqueio de sobreposição e fluxo de substituição/devolução. | Reduz promessa de veículo indisponível e inconsistência de status. | Média; consolidar o ciclo contratual existente. | Conflitos de alocação e tempo entre devolução e nova locação. |
| **8** | **Documentos, multas e repasses:** vencimentos de seguro/licenciamento; vínculo de infração ao contrato e responsável; cobrança acompanhada. | Ajuda a evitar prazos perdidos e despesas sem recuperação. | Média/alta; começar manual, integrar depois. | Vencimentos em atraso e percentual de repasses recuperados. |
| **9** | **Abastecimento e pneus:** litros, valor, KM e comprovante; histórico de troca/rodízio; indicadores de consumo. | Melhora a explicação do custo operacional. | Média; confirmar se o custo é da locadora ou da transportadora. | KM/l, custo/KM e vida útil dos pneus. |
| **10** | **Portal do cliente e telemetria:** consulta de contratos/faturas/vistorias; depois integração de leituras com rastreador, revisão de divergências e alertas. | Reduz digitação e consultas manuais recorrentes. | Alta; depende de permissões, APIs, hardware e qualidade dos dados. | Leituras automáticas válidas e tempo de atendimento. |

O financeiro do Locavia inspira os itens 1–2; os detalhes do fechamento de KM são uma proposta específica para a falha encontrada neste código, sem atribuir ao fornecedor regras não verificadas. [Locavia](https://infosistemas.com.br/locavia/)

Manutenção e rentabilidade têm referências complementares no Fleetio e no LOC1. Para abastecimento, o Fleetio apresenta consumo em KM/l e custos operacionais por distância. [Fleetio manutenção](https://www.fleetio.com/solutions/fleet-maintenance-software), [LOC1](https://blog.loc1.com.br/loc1-melhora-a-gestao-de-processos-de-locacao), [Fleetio combustível](https://www.fleetio.com/solutions/fuel-management-software)

As propostas de vistoria, reservas e portal adaptam os fluxos digitais anunciados pelo Rent Centric; documentos, multas e pneus também têm referência na Sofit. O Fleetio documenta permissões específicas para edição de veículos, odômetros e módulos financeiros; o log antes/depois proposto é uma recomendação nossa. [Rent Centric](https://www.rentcentric.com/products/car-rental-software/), [Sofit](https://www.sofit4.com.br/recursos/), [Permissões Fleetio](https://help.fleetio.com/en_US/fleetio-manage-permissions-reference-1)

## Sequência de evolução sugerida

1. Definir as regras de fechamento e corrigir a competência do painel; adicionar auditoria às alterações sensíveis.
2. Implantar fechamento de KM e cobrança mensal; conectar custos e receitas por placa.
3. Implantar manutenção com OS e vistoria com evidências.
4. Expandir agenda, documentos e portal; integrar rastreamento apenas depois de validar os processos manuais.

Antes de dimensionar a próxima entrega, validar com Flávio: tamanho da frota, responsáveis pelos abastecimentos, regra de franquia (mensal/calendário/aniversário/acumulada), forma de cobrança, rotina de manutenção e rastreador utilizado. Essas respostas refinam o backlog; não foram necessárias para liberar as edições desta entrega.
