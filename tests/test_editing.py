import os
os.environ['DATABASE_URL'] = 'sqlite://'

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import auth
import models
from database import get_db
import main
from main import app


@pytest.fixture
def client(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    models.Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(models.Usuario(username='tester', hashed_password='unused', is_active=True))
        db.commit()
    def database():
        with factory() as db:
            yield db
    monkeypatch.setattr(main, "SessionLocal", factory)
    app.dependency_overrides[get_db] = database
    with TestClient(app, headers={'Authorization': 'Bearer ' + auth.create_access_token({'sub': 'tester'})}) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def vehicle(client, placa='ABC1D23', **values):
    res = client.post('/api/veiculos/', json=dict(placa=placa, modelo='Fiorino', ano=2024, km_atual=12000, **values))
    assert res.status_code == 200, res.text
    return res.json()


def customer(client, cnpj='12345678000199'):
    return client.post('/api/transportadoras/', json=dict(razao_social='Transportes', cnpj=cnpj, email='frota@example.com', telefone='81999999999')).json()


def contract(client, v, t):
    return client.post('/api/contratos/', json=dict(veiculo_id=v['id'], transportadora_id=t['id'], km_inicial=10000, franquia_km_mensal=6000, valor_mensalidade=4500, dia_vencimento_fatura=10, data_inicio='2026-01-01')).json()


def inspection(client, v, km, **extra):
    res = client.post('/api/checklists/', json=dict(veiculo_id=v['id'], km_registrado=km, nivel_combustivel='CHEIO', tipo='VISTORIA_ROTINA', **extra))
    assert res.status_code == 200, res.text
    return client.get('/api/checklists/').json()[0]


def test_vehicle_km_persists_preserves_fields_and_dashboard(client):
    v = vehicle(client, marca='Fiat', chassi='12345678901234567')
    contract(client, v, customer(client))
    res = client.patch(f"/api/veiculos/{v['id']}", json={'km_atual': 16500, 'km_ultima_revisao': 16000, 'capacidade_carga_kg': 0})
    assert res.status_code == 200, res.text
    saved = client.get(f"/api/veiculos/{v['id']}").json()
    assert saved['km_atual'] == 16500 and saved['km_ultima_revisao'] == 16000
    assert saved['marca'] == 'Fiat' and saved['chassi'] == v['chassi'] and saved['capacidade_carga_kg'] == 0
    alerts = client.get('/api/dashboard/resumo').json()['alertas_ativos']
    assert any(a['tipo'] == 'EXCEDENTE_KM' and a['km_excedido'] == 500 for a in alerts)
    assert client.patch(f"/api/veiculos/{v['id']}", json={'km_atual': 16050}).status_code == 200


@pytest.mark.parametrize('patch', [{'km_atual': -1}, {'km_atual': None}, {'km_atual': 1.5}, {'km_ultima_revisao': 13000}, {'status': 'INVALID'}, {'id': 99}, {'modelo': ''}])
def test_bad_vehicle_edits_are_atomic(client, patch):
    v = vehicle(client)
    assert client.patch(f"/api/veiculos/{v['id']}", json=patch).status_code == 422
    assert client.get(f"/api/veiculos/{v['id']}").json() == v


def test_unique_and_optional_fields(client):
    first = vehicle(client)
    second = vehicle(client, 'XYZ9A87')
    assert client.patch(f"/api/veiculos/{second['id']}", json={'placa': first['placa']}).status_code == 400
    t = customer(client)
    t2 = customer(client, '98765432000111')
    assert client.patch(f"/api/transportadoras/{t2['id']}", json={'cnpj': t['cnpj']}).status_code == 400
    url = f"/api/transportadoras/{t['id']}"
    assert client.patch(url, json={'nome_fantasia':'Teste','telefone':'123'}).json()['telefone'] == '123'
    assert client.patch(url, json={'nome_fantasia':None}).json()['nome_fantasia'] is None
    assert client.get(url).json()['razao_social'] == 'Transportes'


def test_contract_edits_and_vehicle_status(client):
    v, v2, t = vehicle(client), vehicle(client, 'XYZ9A87'), customer(client)
    c = contract(client, v, t)
    url = f"/api/contratos/{c['id']}"
    res = client.patch(url, json={'veiculo_id':v2['id'], 'km_inicial':11500, 'franquia_km_mensal':7000, 'valor_mensalidade':5000.25})
    assert res.status_code == 200, res.text
    assert client.get(f"/api/veiculos/{v['id']}").json()['status'] == 'DISPONIVEL'
    assert client.get(f"/api/veiculos/{v2['id']}").json()['status'] == 'ALOCADO'
    assert client.get(url).json()['valor_mensalidade'] == 5000.25
    assert client.patch(url, json={'status':'FINALIZADO','data_fim':'2026-11-12'}).status_code == 200
    assert client.get(f"/api/veiculos/{v2['id']}").json()['status'] == 'DISPONIVEL'
    assert client.patch(url, json={'data_fim':'2025-01-01'}).status_code == 422
    assert client.patch(url, json={'transportadora_id':999}).status_code == 404


def test_conflicting_contract_and_linked_inspections(client):
    v, v2, t = vehicle(client), vehicle(client, 'XYZ9A87'), customer(client)
    c, c2 = contract(client, v, t), contract(client, v2, t)
    url = f"/api/contratos/{c['id']}"
    assert client.patch(url, json={'veiculo_id':v2['id']}).status_code == 400
    inspection(client, v, 12500, contrato_id=c['id'])
    assert client.patch(url, json={'veiculo_id':v2['id'], 'status':'FINALIZADO'}).status_code == 400
    assert client.get(url).json()['veiculo_id'] == v['id']


def test_inspection_history_does_not_rewind_odometer(client):
    v = vehicle(client)
    old = inspection(client, v, 12500)
    new = inspection(client, v, 13000, foto_evidencia_base64='existing-photo')
    assert client.patch(f"/api/checklists/{old['id']}", json={'km_registrado':12100}).status_code == 200
    assert client.get(f"/api/veiculos/{v['id']}").json()['km_atual'] == 13000
    url = f"/api/checklists/{new['id']}"
    res = client.patch(url, json={'km_registrado':12900, 'crlv_ok':False,'avarias_observacoes':'Corrigida'})
    assert res.status_code == 200, res.text
    assert res.json()['foto_evidencia_base64'] == 'existing-photo'
    assert res.json()['crlv_ok'] is False
    assert client.get(f"/api/veiculos/{v['id']}").json()['km_atual'] == 12900
    client.patch(f"/api/veiculos/{v['id']}", json={'km_atual':14000})
    client.patch(url, json={'km_registrado':12800})
    assert client.get(f"/api/veiculos/{v['id']}").json()['km_atual'] == 14000


def test_inspection_links_and_revision_validation(client):
    v, other, t = vehicle(client), vehicle(client, 'XYZ9A87'), customer(client)
    c = contract(client, other, t)
    chk = inspection(client, v, 12500)
    url = f"/api/checklists/{chk['id']}"
    assert client.patch(url, json={'contrato_id':c['id']}).status_code == 400
    client.patch(f"/api/veiculos/{v['id']}", json={'km_ultima_revisao':12000})
    assert client.patch(url, json={'km_registrado':11000}).status_code == 400
    assert client.get(url).json()['km_registrado'] == 12500


def test_cost_edit_and_period_dashboard(client):
    v = vehicle(client)
    cost = client.post('/api/custos-fixos/', json=dict(veiculo_id=v['id'],descricao='Seguro',tipo_custo='SEGURO',valor_mensal=100,dia_vencimento=10,mes_referencia=11,ano_referencia=2026)).json()
    url = f"/api/custos-fixos/{cost['id']}"
    result = client.patch(url,json={'valor_mensal':125.50,'parcelas_totais':12,'parcela_atual':2})
    assert result.status_code == 200, result.text
    assert client.get('/api/dashboard/resumo?mes=11&ano=2026').json()['kpis']['custos_fixos_mensais'] == 125.50
    for patch in [{'parcela_atual':13}, {'dia_vencimento':32}, {'mes_referencia':0}, {'valor_mensal':-1}]:
        assert client.patch(url,json=patch).status_code == 422
    assert client.patch(url,json={'mes_referencia':None, 'ano_referencia':None}).status_code == 200
    assert client.patch(url,json={'veiculo_id':999}).status_code == 404


@pytest.mark.parametrize('resource', ['veiculos','transportadoras','contratos','checklists','custos-fixos'])
def test_auth_and_missing_record(client, resource):
    assert client.patch(f'/api/{resource}/999',json={}).status_code == 404
    assert client.get(f'/api/{resource}/999').status_code == 404
    client.headers.pop('Authorization')
    assert client.patch(f'/api/{resource}/1',json={}).status_code == 401
    assert client.get(f'/api/{resource}/1').status_code == 401
