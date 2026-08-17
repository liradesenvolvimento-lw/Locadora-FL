import os

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

import models
import schemas
from database import engine, get_db

# Recria as tabelas no banco de dados SQLite
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Logmais Fleet API",
    description="API para Gestão de Frota Multiveículos com Vistorias Completas",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    # Serve o frontend (index.html) na raiz do domínio
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(index_path)

@app.get("/api/status", tags=["Status"])
def status_api():
    return {"message": "Logmais Fleet API online", "status": "active"}

# DASHBOARD COM FILTRO TEMPORAL
@app.get("/api/dashboard/resumo", tags=["Dashboard"])
def get_dashboard_summary(
    mes: Optional[int] = Query(None, ge=1, le=12),
    ano: Optional[int] = Query(None, ge=2020, le=2030),
    db: Session = Depends(get_db)
):
    total_veiculos = db.query(models.Veiculo).count()
    veiculos_alocados = db.query(models.Veiculo).filter(models.Veiculo.status == "ALOCADO").count()
    
    contratos_ativos = db.query(models.Contrato).filter(models.Contrato.status == "ATIVO").all()
    faturamento_total = sum(c.valor_mensalidade for c in contratos_ativos)
    
    query_custos = db.query(models.CustoFixoVeiculo).filter(models.CustoFixoVeiculo.status == "ATIVO")
    if mes:
        query_custos = query_custos.filter(models.CustoFixoVeiculo.mes_referencia == mes)
    if ano:
        query_custos = query_custos.filter(models.CustoFixoVeiculo.ano_referencia == ano)
    
    custos_fixos = query_custos.all()
    custos_totais = sum(c.valor_mensal for c in custos_fixos)

    resultado_liquido = faturamento_total - custos_totais

    # Varredura de Alertas
    alertas = []
    for contrato in contratos_ativos:
        veiculo = db.query(models.Veiculo).filter(models.Veiculo.id == contrato.veiculo_id).first()
        transportadora = db.query(models.Transportadora).filter(models.Transportadora.id == contrato.transportadora_id).first()
        
        if veiculo:
            km_rodado = veiculo.km_atual - contrato.km_inicial
            if km_rodado > contrato.franquia_km_mensal:
                excedente = km_rodado - contrato.franquia_km_mensal
                alertas.append({
                    "placa": veiculo.placa,
                    "transportadora": transportadora.razao_social if transportadora else "N/A",
                    "tipo": "EXCEDENTE_KM",
                    "km_excedido": excedente,
                    "mensagem": f"Veículo {veiculo.placa} ({veiculo.modelo}): Franquia excedida em {excedente} KM."
                })
            
            km_proxima_revisao = veiculo.km_ultima_revisao + 10000
            if (km_proxima_revisao - veiculo.km_atual) <= 500:
                alertas.append({
                    "placa": veiculo.placa,
                    "transportadora": transportadora.razao_social if transportadora else "N/A",
                    "tipo": "REVISAO_10K",
                    "km_para_revisao": max(0, km_proxima_revisao - veiculo.km_atual),
                    "mensagem": f"Veículo {veiculo.placa}: Revisão de 10.000 KM próxima (Faltam {km_proxima_revisao - veiculo.km_atual} KM)."
                })

    return {
        "kpis": {
            "frota_total": total_veiculos,
            "frota_ativa": veiculos_alocados,
            "taxa_ocupacao": f"{int((veiculos_alocados/total_veiculos)*100)}%" if total_veiculos > 0 else "0%",
            "faturamento_mensal": faturamento_total,
            "custos_fixos_mensais": custos_totais,
            "resultado_liquido": resultado_liquido
        },
        "alertas_ativos": alertas
    }

# CRUD VEÍCULOS
@app.post("/api/veiculos/", response_model=schemas.VeiculoResponse, tags=["Veículos"])
def criar_veiculo(veiculo: schemas.VeiculoCreate, db: Session = Depends(get_db)):
    veiculo_existente = db.query(models.Veiculo).filter(models.Veiculo.placa == veiculo.placa).first()
    if veiculo_existente:
        raise HTTPException(status_code=400, detail="Veículo com esta placa já cadastrado.")
    
    novo_veiculo = models.Veiculo(**veiculo.model_dump())
    db.add(novo_veiculo)
    db.commit()
    db.refresh(novo_veiculo)
    return novo_veiculo

@app.get("/api/veiculos/", response_model=List[schemas.VeiculoResponse], tags=["Veículos"])
def listar_veiculos(db: Session = Depends(get_db)):
    return db.query(models.Veiculo).all()

# CRUD TRANSPORTADORAS
@app.post("/api/transportadoras/", response_model=schemas.TransportadoraResponse, tags=["Transportadoras"])
def criar_transportadora(transportadora: schemas.TransportadoraCreate, db: Session = Depends(get_db)):
    nova_transp = models.Transportadora(**transportadora.model_dump())
    db.add(nova_transp)
    db.commit()
    db.refresh(nova_transp)
    return nova_transp

@app.get("/api/transportadoras/", response_model=List[schemas.TransportadoraResponse], tags=["Transportadoras"])
def listar_transportadoras(db: Session = Depends(get_db)):
    return db.query(models.Transportadora).all()

# CRUD CONTRATOS
@app.post("/api/contratos/", response_model=schemas.ContratoResponse, tags=["Contratos"])
def criar_contrato(contrato: schemas.ContratoCreate, db: Session = Depends(get_db)):
    veiculo = db.query(models.Veiculo).filter(models.Veiculo.id == contrato.veiculo_id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail=f"Veículo com ID {contrato.veiculo_id} não encontrado no banco.")
    
    veiculo.status = "ALOCADO"
    novo_contrato = models.Contrato(**contrato.model_dump())
    db.add(novo_contrato)
    db.commit()
    db.refresh(novo_contrato)
    return novo_contrato

@app.get("/api/contratos/", response_model=List[schemas.ContratoResponse], tags=["Contratos"])
def listar_contratos(db: Session = Depends(get_db)):
    return db.query(models.Contrato).all()

# CHECKLIST COMPLETO
@app.post("/api/checklists/", tags=["Checklists"])
def registrar_checklist(checklist: schemas.ChecklistCreate, db: Session = Depends(get_db)):
    veiculo = db.query(models.Veiculo).filter(models.Veiculo.id == checklist.veiculo_id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail=f"Veículo ID {checklist.veiculo_id} não encontrado.")

    veiculo.km_atual = checklist.km_registrado
    
    if checklist.tipo == "CHECKIN_RETORNO":
        veiculo.status = "DISPONIVEL"

    novo_checklist = models.Checklist(**checklist.model_dump())
    db.add(novo_checklist)
    db.commit()

    alertas_gerados = []
    km_proxima_revisao = veiculo.km_ultima_revisao + 10000
    if (km_proxima_revisao - checklist.km_registrado) <= 500:
        alertas_gerados.append(f"ALERTA MANUTENÇÃO: Veículo {veiculo.placa} a {km_proxima_revisao - checklist.km_registrado} KM da revisão de 10.000 KM.")

    return {
        "status": "sucesso",
        "tipo_checklist": checklist.tipo,
        "mensagem": f"Checklist ({checklist.tipo}) registrado com sucesso para o veículo {veiculo.placa}.",
        "km_atualizado": checklist.km_registrado,
        "alertas_despertados": alertas_gerados
    }

# CUSTOS FIXOS
@app.post("/api/custos-fixos/", response_model=schemas.CustoFixoResponse, tags=["Financeiro Locadora"])
def cadastrar_custo_fixo(custo: schemas.CustoFixoCreate, db: Session = Depends(get_db)):
    novo_custo = models.CustoFixoVeiculo(**custo.model_dump())
    db.add(novo_custo)
    db.commit()
    db.refresh(novo_custo)
    return novo_custo

@app.get("/api/custos-fixos/", response_model=List[schemas.CustoFixoResponse], tags=["Financeiro Locadora"])
def listar_custos_fixos(db: Session = Depends(get_db)):
    return db.query(models.CustoFixoVeiculo).all()