"""Run manually: python tests/verify_browser.py (requires playwright + chromium).
Starts a local server with a disposable database; never accesses production data.
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='locadora-browser-') as temp:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    env = dict(os.environ, DATABASE_URL=f'sqlite:///{temp}/test.db', ADMIN_USERNAME='browser-test', ADMIN_PASSWORD='local-test-only', JWT_SECRET_KEY='isolated-browser-test-secret')
    with open(f'{temp}/server.log', 'w') as logs:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(port)], cwd=root, env=env, stdout=logs, stderr=logs)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(url + '/api/status', timeout=1)
                    break
                except OSError:
                    time.sleep(.1)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context(viewport={'width':1440, 'height':1000})
                api = context.request
                login = api.post(url + '/api/auth/login', form={'username':'browser-test','password':'local-test-only'})
                assert login.ok, login.text()
                headers = {'Authorization':'Bearer ' + login.json()['access_token']}
                def post(resource, data):
                    r = api.post(url + '/api/' + resource + '/', data=data, headers=headers)
                    assert r.ok, r.text()
                    return r.json()
                def get(resource, id):
                    r = api.get(f'{url}/api/{resource}/{id}', headers=headers)
                    assert r.ok, r.text()
                    return r.json()
                v = post('veiculos', dict(placa='TST1A23',modelo='Fiorino',ano=2024,km_atual=15000,km_ultima_revisao=10000,chassi='12345678901234567'))
                t = post('transportadoras', dict(razao_social='Cliente teste',cnpj='12345678000199',email='teste@example.com',telefone='81999999999'))
                c = post('contratos',dict(veiculo_id=v['id'],transportadora_id=t['id'],km_inicial=14000,franquia_km_mensal=6000,valor_mensalidade=4500,dia_vencimento_fatura=10,data_inicio='2026-11-01'))
                cost = post('custos-fixos',dict(veiculo_id=v['id'],descricao='Seguro',tipo_custo='SEGURO',valor_mensal=300,dia_vencimento=5))
                post('checklists',dict(veiculo_id=v['id'],km_registrado=16000,tipo='VISTORIA_ROTINA',nivel_combustivel='CHEIO'))
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(url)
                page.locator('#login-username').fill('browser-test')
                page.locator('#login-password').fill('local-test-only')
                page.locator('#form-login button[type=submit]').click()
                expect(page.locator('#login-screen')).to_be_hidden()
                page.locator('#nav-frota').click()
                page.locator('#tbl-geral-veiculos button').click()
                expect(page.locator('#edit-km_atual')).to_have_value('16000')
                page.locator('#edit-km_atual').fill('15500')
                page.locator('#edit-km_ultima_revisao').fill('15000')
                page.locator('#edit-capacidade_carga_kg').fill('0')
                page.locator('#edicao-salvar').click()
                expect(page.locator('#modal-edicao')).not_to_be_visible()
                assert get('veiculos',v['id'])['km_atual'] == 15500
                assert get('veiculos',v['id'])['chassi'] == v['chassi']
                expect(page.locator('#tbl-geral-veiculos')).to_contain_text('0 KG')
                # Cancel must not save. Server validation must leave the editor open.
                page.locator('#tbl-geral-veiculos button').click()
                page.locator('#edit-modelo').fill('Descartar')
                page.locator('#edicao-cancelar').click()
                assert get('veiculos',v['id'])['modelo'] == 'Fiorino'
                page.locator('#tbl-geral-veiculos button').click()
                page.locator('#edit-km_ultima_revisao').fill('20000')
                page.locator('#edicao-salvar').click()
                expect(page.locator('#edicao-erro')).to_contain_text('última revisão')
                page.locator('#edicao-cancelar').click()
                # Remaining four record types.
                for nav, table, field, value, resource, rid, expected in [
                    ('contratos','tbl-edicao-transportadoras','telefone','81888888888','transportadoras',t['id'],'81888888888'),
                    ('contratos','tbl-geral-contratos','valor_mensalidade','4700.25','contratos',c['id'],4700.25),
                    ('financeiro','tbl-geral-custos','valor_mensal','350.75','custos-fixos',cost['id'],350.75),
                    ('checklist','tbl-edicao-checklists','km_registrado','15800','checklists',1,15800),
                ]:
                    page.locator('#nav-' + nav).click()
                    page.locator('#' + table + ' button').click()
                    page.locator('#edit-' + field).fill(value)
                    page.locator('#edicao-salvar').click()
                    expect(page.locator('#modal-edicao')).not_to_be_visible()
                    assert get(resource,rid)[field] == expected
                # Reload persistence and mobile editor layout.
                page.reload()
                page.locator('#nav-manutencao').click()
                page.locator('#tbl-geral-manutencao button').click()
                expect(page.locator('#edit-km_atual')).to_have_value('15500')
                page.set_viewport_size({'width':390,'height':844})
                box = page.locator('#modal-edicao').bounding_box()
                assert box['width'] <= 390 and box['x'] >= 0
                page.screenshot(path='/tmp/locadora-edicao-mobile.png')
                page.set_viewport_size({'width':1440,'height':1000})
                page.screenshot(path='/tmp/locadora-edicao-desktop.png')
                assert not errors, errors
                browser.close()
                print('Browser OK: five editors, persistence, cancel, validation, preserved odometer and mobile layout.')
        finally:
            process.terminate()
            process.wait(timeout=10)
