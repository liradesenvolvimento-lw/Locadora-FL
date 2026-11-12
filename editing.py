"""Authenticated record editing, preserving fields absent from PATCH requests."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
import auth
import models
import schemas
import edit_schemas as edits
from database import get_db

router = APIRouter(dependencies=[Depends(auth.get_current_user)])


def record(db, model, record_id):
    obj = db.get(model, record_id)
    if obj is None:
        raise HTTPException(404, 'Registro não encontrado.')
    return obj


def merged(obj, patch, schema):
    values = {name: getattr(obj, name) for name in schema.model_fields}
    values.update(patch.model_dump(exclude_unset=True))
    try:
        return schema.model_validate(values)
    except ValidationError as exc:
        messages = ['.'.join(str(p) for p in e['loc']) + ': ' + e['msg'] for e in exc.errors()]
        raise HTTPException(422, 'Verifique os campos: ' + '; '.join(messages))


def save(db, obj, values):
    for name, value in values.model_dump().items():
        setattr(obj, name, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, 'Placa/CNPJ já cadastrado ou vínculo inválido.')
    db.refresh(obj)
    return obj


@router.get('/api/veiculos/{record_id}', response_model=schemas.VeiculoResponse)
def get_vehicle(record_id: int, db: Session = Depends(get_db)):
    return record(db, models.Veiculo, record_id)


@router.patch('/api/veiculos/{record_id}', response_model=schemas.VeiculoResponse)
def edit_vehicle(record_id: int, patch: edits.VeiculoPatch, db: Session = Depends(get_db)):
    obj = record(db, models.Veiculo, record_id)
    values = merged(obj, patch, edits.VeiculoEdit)
    return save(db, obj, values)


@router.get('/api/transportadoras/{record_id}', response_model=schemas.TransportadoraResponse)
def get_customer(record_id: int, db: Session = Depends(get_db)):
    return record(db, models.Transportadora, record_id)


@router.patch('/api/transportadoras/{record_id}', response_model=schemas.TransportadoraResponse)
def edit_customer(record_id: int, patch: edits.TransportadoraPatch, db: Session = Depends(get_db)):
    obj = record(db, models.Transportadora, record_id)
    return save(db, obj, merged(obj, patch, edits.TransportadoraEdit))


@router.get('/api/contratos/{record_id}', response_model=schemas.ContratoResponse)
def get_contract(record_id: int, db: Session = Depends(get_db)):
    return record(db, models.Contrato, record_id)


@router.patch('/api/contratos/{record_id}', response_model=schemas.ContratoResponse)
def edit_contract(record_id: int, patch: edits.ContratoPatch, db: Session = Depends(get_db)):
    obj = record(db, models.Contrato, record_id)
    values = merged(obj, patch, edits.ContratoEdit)
    vehicle = record(db, models.Veiculo, values.veiculo_id)
    record(db, models.Transportadora, values.transportadora_id)
    vehicle_changed = obj.veiculo_id != values.veiculo_id
    allocation_changed = vehicle_changed or obj.status != values.status
    if vehicle_changed and db.query(models.Checklist).filter_by(contrato_id=obj.id).first():
        raise HTTPException(400, 'Corrija os vínculos das vistorias deste contrato antes de trocar o veículo.')
    if allocation_changed and values.status == 'ATIVO':
        other = db.query(models.Contrato).filter(
            models.Contrato.veiculo_id == vehicle.id,
            models.Contrato.status == 'ATIVO', models.Contrato.id != obj.id,
        ).first()
        if other or vehicle.status == 'MANUTENCAO':
            raise HTTPException(400, 'Veículo em manutenção ou com outro contrato ativo.')
    if allocation_changed:
        old_vehicle = record(db, models.Veiculo, obj.veiculo_id)
        other_old = db.query(models.Contrato).filter(
            models.Contrato.veiculo_id == old_vehicle.id,
            models.Contrato.status == 'ATIVO', models.Contrato.id != obj.id,
        ).first()
        if not other_old and old_vehicle.status == 'ALOCADO':
            old_vehicle.status = 'DISPONIVEL'
        if values.status == 'ATIVO':
            vehicle.status = 'ALOCADO'
    return save(db, obj, values)


@router.get('/api/checklists/', response_model=List[schemas.ChecklistResponse])
def list_inspections(db: Session = Depends(get_db)):
    return db.query(models.Checklist).order_by(models.Checklist.data_registro.desc(), models.Checklist.id.desc()).all()


@router.get('/api/checklists/{record_id}', response_model=schemas.ChecklistResponse)
def get_inspection(record_id: int, db: Session = Depends(get_db)):
    return record(db, models.Checklist, record_id)


@router.patch('/api/checklists/{record_id}', response_model=schemas.ChecklistResponse)
def edit_inspection(record_id: int, patch: edits.ChecklistPatch, db: Session = Depends(get_db)):
    obj = record(db, models.Checklist, record_id)
    values = merged(obj, patch, edits.ChecklistEdit)
    vehicle = record(db, models.Veiculo, values.veiculo_id)
    if values.contrato_id is not None:
        contract = record(db, models.Contrato, values.contrato_id)
        if contract.veiculo_id != values.veiculo_id:
            raise HTTPException(400, 'O contrato deve pertencer ao veículo da vistoria.')
    latest = db.query(models.Checklist).filter_by(veiculo_id=obj.veiculo_id).order_by(
        models.Checklist.data_registro.desc(), models.Checklist.id.desc()).first()
    # Only correct a currently mirrored reading. Historical records, reassigned
    # inspections and independently edited odometers do not replay fleet events.
    if (obj.veiculo_id == values.veiculo_id and latest.id == obj.id
            and vehicle.km_atual == obj.km_registrado and values.km_registrado != obj.km_registrado):
        if values.km_registrado < vehicle.km_ultima_revisao:
            raise HTTPException(400, 'Corrija o KM da última revisão na frota antes de reduzir este odômetro.')
        vehicle.km_atual = values.km_registrado
    return save(db, obj, values)


@router.get('/api/custos-fixos/{record_id}', response_model=schemas.CustoFixoResponse)
def get_cost(record_id: int, db: Session = Depends(get_db)):
    return record(db, models.CustoFixoVeiculo, record_id)


@router.patch('/api/custos-fixos/{record_id}', response_model=schemas.CustoFixoResponse)
def edit_cost(record_id: int, patch: edits.CustoPatch, db: Session = Depends(get_db)):
    obj = record(db, models.CustoFixoVeiculo, record_id)
    values = merged(obj, patch, edits.CustoEdit)
    record(db, models.Veiculo, values.veiculo_id)
    return save(db, obj, values)
