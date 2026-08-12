from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Transportadora(Base):
    __tablename__ = "transportadoras"

    id = Column(Integer, primary_key=True, index=True)
    razao_social = Column(String(150), nullable=False)
    nome_fantasia = Column(String(100), nullable=True)
    cnpj = Column(String(18), unique=True, index=True, nullable=False)
    email = Column(String(100), nullable=False)
    telefone = Column(String(20), nullable=False)
    responsavel_nome = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contratos = relationship("Contrato", back_populates="transportadora")


class Veiculo(Base):
    __tablename__ = "veiculos"

    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(8), unique=True, index=True, nullable=False)
    categoria = Column(String(50), default="Utilitário Leve") # Fiorino, Sprinter, Master, HR...
    modelo = Column(String(100), nullable=False)              # Ex: Fiorino Baú 1.4 EVO / Renault Master L3H2
    marca = Column(String(50), nullable=True)                 # Fiat, Renault, Mercedes
    ano = Column(Integer, nullable=False)
    capacidade_carga_kg = Column(Float, nullable=True)        # Cap. em KG
    chassi = Column(String(17), nullable=True)
    km_atual = Column(Integer, default=0)
    km_ultima_revisao = Column(Integer, default=0)
    status = Column(String(20), default="DISPONIVEL")         # DISPONIVEL, ALOCADO, MANUTENCAO
    created_at = Column(DateTime, default=datetime.utcnow)

    contratos = relationship("Contrato", back_populates="veiculo")
    checklists = relationship("Checklist", back_populates="veiculo")
    custos_fixos = relationship("CustoFixoVeiculo", back_populates="veiculo")


class Contrato(Base):
    __tablename__ = "contratos"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    transportadora_id = Column(Integer, ForeignKey("transportadoras.id"), nullable=False)
    km_inicial = Column(Integer, nullable=False)
    franquia_km_mensal = Column(Integer, nullable=False)
    valor_km_excedente = Column(Float, default=0.50, nullable=False)
    valor_mensalidade = Column(Float, nullable=False)
    dia_vencimento_fatura = Column(Integer, nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=True)
    status = Column(String(20), default="ATIVO")              # ATIVO, FINALIZADO, CANCELADO
    created_at = Column(DateTime, default=datetime.utcnow)

    veiculo = relationship("Veiculo", back_populates="contratos")
    transportadora = relationship("Transportadora", back_populates="contratos")
    checklists = relationship("Checklist", back_populates="contrato")


class Checklist(Base):
    __tablename__ = "checklists"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    contrato_id = Column(Integer, ForeignKey("contratos.id"), nullable=True)
    tipo = Column(String(20), nullable=False)                 # CHECKOUT_SAIDA, CHECKIN_RETORNO, VISTORIA_ROTINA
    
    # Leitura operacional
    km_registrado = Column(Integer, nullable=False)
    nivel_combustivel = Column(String(20), nullable=False)     # RESERVA, 1/4, 1/2, 3/4, CHEIO
    
    # Documentos & Acessórios
    crlv_ok = Column(Boolean, default=True)
    manual_ok = Column(Boolean, default=True)
    cartao_seguro_ok = Column(Boolean, default=True)
    
    # Emergência & Rodagem
    estepe_ok = Column(Boolean, default=True)
    kit_ferramentas_ok = Column(Boolean, default=True)         # Macaco, Chave Roda, Triângulo
    pneus_sulco_ok = Column(Boolean, default=True)
    
    # Estado Geral & Higiene
    limpeza_interna_ok = Column(Boolean, default=True)
    luzes_farois_ok = Column(Boolean, default=True)
    ar_condicionado_ok = Column(Boolean, default=True)
    
    # Detalhes de Danos e Foto
    avarias_observacoes = Column(Text, nullable=True)
    foto_evidencia_base64 = Column(Text, nullable=True)        # String Base64 da Foto capturada
    
    data_registro = Column(DateTime, default=datetime.utcnow)

    veiculo = relationship("Veiculo", back_populates="checklists")
    contrato = relationship("Contrato", back_populates="checklists")


class CustoFixoVeiculo(Base):
    __tablename__ = "custos_fixos_veiculo"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    descricao = Column(String(100), nullable=False)
    tipo_custo = Column(String(50), nullable=False)           # FINANCIAMENTO, SEGURO, IPVA, MANUTENCAO
    valor_mensal = Column(Float, nullable=False)
    dia_vencimento = Column(Integer, nullable=False)
    mes_referencia = Column(Integer, nullable=True)            # 1 a 12
    ano_referencia = Column(Integer, nullable=True)            # Ex: 2026
    parcelas_totais = Column(Integer, default=1)
    parcela_atual = Column(Integer, default=1)
    status = Column(String(20), default="ATIVO")
    created_at = Column(DateTime, default=datetime.utcnow)

    veiculo = relationship("Veiculo", back_populates="custos_fixos")