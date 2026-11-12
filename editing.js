// Reuse a single editor, submitting only changed fields so hidden data is retained.
function textoSeguro(value) {
  const span = document.createElement('span');
  span.textContent = value ?? '';
  return span.innerHTML;
}
function botaoEditar(tipo, id) {
  return `<button type="button" onclick="editarRegistro('${tipo}', ${id})" class="border border-dark-border rounded-lg px-3 py-2 text-xs text-brand-green hover:bg-brand-navy" aria-label="Editar registro ${id}">Editar</button>`;
}
const campo = (key, label, type = 'text', options = {}) => ({key, label, type, ...options});
const numero = (key, label, options = {}) => campo(key, label, 'number', {min: 0, step: 1, ...options});
const escolha = (key, label, values, options = {}) => campo(key, label, 'select', {values, ...options});
const veiculoCampo = () => escolha('veiculo_id', 'Veículo', 'veiculos', {numeric: true});
const camposEdicao = {
  veiculos: {title: 'Editar veículo', fields: [
    campo('placa', 'Placa', 'text', {maxLength: 8}), campo('categoria', 'Categoria', 'text', {maxLength: 50}),
    campo('modelo', 'Modelo', 'text', {maxLength: 100}), campo('marca', 'Marca', 'text', {optional: true, maxLength: 50}),
    numero('ano', 'Ano', {min: 1900, max: 2100}), numero('capacidade_carga_kg', 'Capacidade de carga (KG)', {step: 'any', optional: true}),
    campo('chassi', 'Chassi', 'text', {optional: true, maxLength: 17}), numero('km_atual', 'KM atual'),
    numero('km_ultima_revisao', 'KM da última revisão'), escolha('status', 'Status', ['DISPONIVEL','ALOCADO','MANUTENCAO'])
  ]},
  transportadoras: {title: 'Editar transportadora', fields: [
    campo('razao_social', 'Razão social', 'text', {maxLength: 150}), campo('nome_fantasia', 'Nome fantasia', 'text', {optional: true, maxLength: 100}),
    campo('cnpj', 'CNPJ', 'text', {maxLength: 18}), campo('email', 'E-mail', 'email', {maxLength: 100}),
    campo('telefone', 'Telefone', 'text', {maxLength: 20}), campo('responsavel_nome', 'Responsável', 'text', {optional: true, maxLength: 100})
  ]},
  contratos: {title: 'Editar contrato', fields: [
    veiculoCampo(), escolha('transportadora_id', 'Transportadora', 'transportadoras', {numeric: true}),
    numero('km_inicial', 'KM inicial'), numero('franquia_km_mensal', 'Franquia mensal (KM)'),
    numero('valor_km_excedente', 'Valor do KM excedente (R$)', {step: 'any'}), numero('valor_mensalidade', 'Mensalidade (R$)', {step: 'any'}),
    numero('dia_vencimento_fatura', 'Dia de vencimento', {min: 1, max: 31}), campo('data_inicio', 'Data inicial', 'date'),
    campo('data_fim', 'Data final', 'date', {optional: true}), escolha('status', 'Status', ['ATIVO','FINALIZADO','CANCELADO'])
  ]},
  checklists: {title: 'Editar vistoria', note: 'A correção do KM da última vistoria atualiza a frota somente se o odômetro ainda corresponder àquela leitura. Vistorias anteriores e trocas de veículo não alteram o KM atual. Corrija o KM e o status na Frota quando necessário.', fields: [
    veiculoCampo(), escolha('contrato_id', 'Contrato', 'contratos', {optional: true, numeric: true}),
    escolha('tipo', 'Tipo de vistoria', ['CHECKOUT_SAIDA','CHECKIN_RETORNO','VISTORIA_ROTINA']), numero('km_registrado', 'KM registrado'),
    escolha('nivel_combustivel', 'Nível de combustível', ['RESERVA','1/4','1/2','3/4','CHEIO']),
    ...[['crlv_ok','CRLV presente'],['manual_ok','Manual presente'],['cartao_seguro_ok','Cartão do seguro presente'],
      ['estepe_ok','Estepe OK'],['kit_ferramentas_ok','Kit de ferramentas OK'],['pneus_sulco_ok','Pneus OK'],
      ['limpeza_interna_ok','Limpeza interna OK'],['luzes_farois_ok','Luzes e faróis OK'],['ar_condicionado_ok','Ar-condicionado OK']].map(([k,l]) => campo(k,l,'checkbox')),
    campo('avarias_observacoes', 'Avarias / observações', 'textarea', {optional: true})
  ]},
  'custos-fixos': {title: 'Editar custo fixo', fields: [
    veiculoCampo(), campo('descricao', 'Descrição', 'text', {maxLength: 100}), campo('tipo_custo', 'Tipo de custo', 'text', {maxLength: 50}),
    numero('valor_mensal', 'Valor mensal (R$)', {step: 'any'}), numero('dia_vencimento', 'Dia de vencimento', {min: 1, max: 31}),
    numero('mes_referencia', 'Mês de referência', {optional: true, min: 1, max: 12}), numero('ano_referencia', 'Ano de referência', {optional: true, min: 1900, max: 2100}),
    numero('parcelas_totais', 'Total de parcelas', {min: 1}), numero('parcela_atual', 'Parcela atual', {min: 1}), escolha('status', 'Status', ['ATIVO','INATIVO'])
  ]}
};

async function apiEdicao(path, options = {}) {
  const res = await fetch(`${API_URL}/api/${path}`, options);
  let data;
  try { data = await res.json(); } catch { throw new Error('O servidor não retornou uma resposta válida.'); }
  if (!res.ok) {
    const detail = data.detail;
    throw new Error(Array.isArray(detail) ? detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join('; ') : detail || 'Não foi possível salvar.');
  }
  return data;
}

async function carregarListasEdicao(tipo) {
  const body = document.getElementById(`tbl-edicao-${tipo}`);
  try {
    const [rows, vehicles] = await Promise.all([apiEdicao(`${tipo}/`), tipo === 'checklists' ? apiEdicao('veiculos/') : Promise.resolve([])]);
    body.replaceChildren();
    if (!rows.length) {
      const row = body.insertRow(); const cell = row.insertCell(); cell.colSpan = 5;
      cell.textContent = 'Nenhum registro cadastrado.'; cell.className = 'py-4 text-dark-subtext';
    }
    rows.forEach(item => {
      const row = body.insertRow();
      const vehicle = vehicles.find(v => v.id === item.veiculo_id);
      const values = tipo === 'checklists' ? [new Date(item.data_registro + (/(?:Z|[+-]\d{2}:\d{2})$/.test(item.data_registro) ? '' : 'Z')).toLocaleString('pt-BR'), vehicle?.placa || `#${item.veiculo_id}`, item.tipo, item.km_registrado] : [item.razao_social, item.cnpj, item.email, item.telefone];
      values.forEach(value => { const cell = row.insertCell(); cell.textContent = value ?? ''; cell.className = 'py-3'; });
      row.insertCell().innerHTML = botaoEditar(tipo, item.id);
    });
  } catch (err) { body.textContent = 'Não foi possível carregar os registros.'; toast(err.message, 'error'); }
}

const editor = document.createElement('dialog');
editor.id = 'modal-edicao';
editor.className = 'bg-dark-card text-dark-text border border-dark-border rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto';
editor.setAttribute('aria-labelledby', 'edicao-titulo');
editor.innerHTML = `<form id="form-edicao"><h2 id="edicao-titulo" class="text-lg font-bold mb-3"></h2><p id="edicao-nota" class="text-xs text-dark-subtext mb-4"></p><div id="edicao-campos" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div><p id="edicao-erro" role="alert" class="text-sm text-red-400 my-3"></p><div class="flex justify-end gap-3 mt-6"><button type="button" id="edicao-cancelar" class="px-4 py-2 border border-dark-border rounded-lg">Cancelar</button><button type="submit" id="edicao-salvar" class="px-4 py-2 bg-brand-green text-brand-navy font-bold rounded-lg">Salvar alterações</button></div></form>`;
document.body.appendChild(editor);
let edicaoAtual = null;
let salvandoEdicao = false;
document.getElementById('edicao-cancelar').onclick = () => editor.close();
editor.addEventListener('cancel', e => { if (salvandoEdicao) e.preventDefault(); });

async function editarRegistro(tipo, id) {
  if (editor.open) return;
  try {
    const config = camposEdicao[tipo];
    const original = await apiEdicao(`${tipo}/${id}`);
    const references = {};
    await Promise.all([...new Set(config.fields.filter(f => typeof f.values === 'string').map(f => f.values))].map(async resource => {
      references[resource] = await apiEdicao(`${resource}/`);
    }));
    document.getElementById('edicao-titulo').textContent = `${config.title} #${id}`;
    document.getElementById('edicao-nota').textContent = config.note || 'Altere os dados abaixo e salve. Cancelar mantém o cadastro como está.';
    document.getElementById('edicao-erro').textContent = '';
    const container = document.getElementById('edicao-campos'); container.replaceChildren();
    for (const field of config.fields) {
      const label = document.createElement('label'); label.className = 'block text-xs text-dark-subtext';
      label.textContent = field.label + (field.optional ? ' (opcional)' : '');
      const input = document.createElement(field.type === 'select' ? 'select' : field.type === 'textarea' ? 'textarea' : 'input');
      input.id = `edit-${field.key}`; input.name = field.key;
      if (!['select','textarea'].includes(field.type)) input.type = field.type;
      input.className = field.type === 'checkbox' ? 'ml-2' : 'block w-full mt-1 bg-dark-bg border border-dark-border rounded-lg p-2.5 text-dark-text';
      if (field.type === 'select') {
        if (field.optional) input.add(new Option('Sem vínculo', ''));
        const options = Array.isArray(field.values) ? field.values.map(v => [v,v]) : references[field.values].map(r => [r.id, r.placa ? `${r.placa} - ${r.modelo}` : r.razao_social || `Contrato #${r.id} · veículo #${r.veiculo_id} · ${r.status}`]);
        // Keep legacy options visible instead of silently replacing their value.
        if (original[field.key] != null && !options.some(([value]) => String(value) === String(original[field.key]))) options.push([original[field.key], original[field.key]]);
        options.forEach(([value, text]) => input.add(new Option(text, value)));
      }
      if (field.type === 'checkbox') input.checked = original[field.key];
      else input.value = original[field.key] ?? '';
      input.required = !field.optional && field.type !== 'checkbox';
      for (const key of ['min','max','step','maxLength']) if (field[key] !== undefined) input[key] = field[key];
      label.appendChild(input); container.appendChild(label);
    }
    edicaoAtual = {tipo, id, original};
    editor.showModal();
  } catch (err) { toast(err.message || 'Não foi possível abrir a edição.', 'error'); }
}

document.getElementById('form-edicao').addEventListener('submit', async e => {
  e.preventDefault();
  if (salvandoEdicao || !edicaoAtual) return;
  const {tipo, id, original} = edicaoAtual;
  const payload = {};
  for (const field of camposEdicao[tipo].fields) {
    const input = document.getElementById(`edit-${field.key}`);
    let value = field.type === 'checkbox' ? input.checked : input.value.trim();
    if (value === '' && field.optional) value = null;
    else if (field.type === 'number' || field.numeric) value = Number(value);
    if (value !== original[field.key]) payload[field.key] = value;
  }
  if (!Object.keys(payload).length) { editor.close(); return; }
  salvandoEdicao = true;
  const save = document.getElementById('edicao-salvar'); const cancel = document.getElementById('edicao-cancelar');
  save.disabled = cancel.disabled = true; save.textContent = 'Salvando…';
  document.getElementById('edicao-erro').textContent = '';
  try {
    await apiEdicao(`${tipo}/${id}`, {method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    editor.close(); toast('Alterações salvas com sucesso!', 'success');
  } catch (err) { document.getElementById('edicao-erro').textContent = err.message; return; }
  finally { salvandoEdicao = false; save.disabled = cancel.disabled = false; save.textContent = 'Salvar alterações'; }
  const results = await Promise.allSettled([carregarDashboard(), carregarTabelaFrota(), carregarTabelaContratos(), carregarTabelaManutencao(), carregarTabelaCustos(), carregarListasEdicao('transportadoras'), carregarListasEdicao('checklists')]);
  if (results.some(r => r.status === 'rejected')) toast('Dados salvos. Recarregue a página para atualizar as listas.', 'warning');
});
