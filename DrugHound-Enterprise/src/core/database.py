"""Enterprise database models."""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()

class Drug(Base):
    __tablename__ = 'drugs'
    __table_args__ = (Index('idx_drug_name', 'name'), Index('idx_novelty', 'novelty_score'))
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    synonyms = Column(JSON, default=list)
    drug_class = Column(String(100))
    mechanism = Column(Text)
    novelty_score = Column(Float, default=0)
    novelty_level = Column(String(20))
    pubmed_count = Column(Integer, default=0)
    trials_count = Column(Integer, default=0)
    patent_count = Column(Integer, default=0)
    safety_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    trials = relationship("ClinicalTrial", back_populates="drug", cascade="all, delete-orphan")
    publications = relationship("Publication", back_populates="drug", cascade="all, delete-orphan")
    repurposing_ideas = relationship("RepurposingIdea", back_populates="drug", cascade="all, delete-orphan")
    patents = relationship("Patent", back_populates="drug", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="drug", cascade="all, delete-orphan")

class ClinicalTrial(Base):
    __tablename__ = 'clinical_trials'
    __table_args__ = (Index('idx_trial_status', 'status'), Index('idx_trial_phase', 'phase'))
    
    id = Column(Integer, primary_key=True)
    nct_id = Column(String(50), unique=True, index=True)
    drug_id = Column(Integer, ForeignKey('drugs.id'))
    title = Column(String(500))
    condition = Column(String(300))
    phase = Column(String(50))
    status = Column(String(50))
    start_date = Column(DateTime)
    completion_date = Column(DateTime)
    enrollment = Column(Integer)
    source = Column(String(100))
    url = Column(String(500))
    results_available = Column(Boolean, default=False)
    
    drug = relationship("Drug", back_populates="trials")

class Publication(Base):
    __tablename__ = 'publications'
    
    id = Column(Integer, primary_key=True)
    pmid = Column(String(50), unique=True, index=True)
    drug_id = Column(Integer, ForeignKey('drugs.id'))
    title = Column(String(500))
    journal = Column(String(200))
    year = Column(Integer)
    citations = Column(Integer, default=0)
    abstract = Column(Text)
    doi = Column(String(100))
    url = Column(String(500))
    impact_factor = Column(Float)
    
    drug = relationship("Drug", back_populates="publications")

class RepurposingIdea(Base):
    __tablename__ = 'repurposing_ideas'
    
    id = Column(Integer, primary_key=True)
    drug_id = Column(Integer, ForeignKey('drugs.id'))
    target_condition = Column(String(300))
    mechanism = Column(Text)
    evidence_strength = Column(String(50))
    confidence_score = Column(Float)
    supporting_pubmed_ids = Column(JSON, default=list)
    clinical_trial_ids = Column(JSON, default=list)
    patent_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    validated = Column(Boolean, default=False)
    
    drug = relationship("Drug", back_populates="repurposing_ideas")

class Patent(Base):
    __tablename__ = 'patents'
    
    id = Column(Integer, primary_key=True)
    patent_number = Column(String(50), unique=True)
    drug_id = Column(Integer, ForeignKey('drugs.id'))
    title = Column(String(500))
    assignee = Column(String(200))
    filing_date = Column(DateTime)
    grant_date = Column(DateTime)
    expiration_date = Column(DateTime)
    claims = Column(Text)
    
    drug = relationship("Drug", back_populates="patents")

class Evidence(Base):
    __tablename__ = 'evidence'
    
    id = Column(Integer, primary_key=True)
    drug_id = Column(Integer, ForeignKey('drugs.id'))
    evidence_type = Column(String(50))  # clinical, preclinical, in_silico, anecdotal
    description = Column(Text)
    strength = Column(Float)  # 0-1
    source = Column(String(200))
    source_url = Column(String(500))
    date_added = Column(DateTime, default=datetime.utcnow)
    
    drug = relationship("Drug", back_populates="evidence")

class SearchHistory(Base):
    __tablename__ = 'search_history'
    
    id = Column(Integer, primary_key=True)
    query = Column(String(500))
    results_count = Column(Integer)
    search_type = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_ip = Column(String(50))

def init_database(db_path='drughound_enterprise.db'):
    engine = create_engine(f'sqlite:///{db_path}', echo=False, pool_size=10)
    Base.metadata.create_all(engine)
    return engine

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()
