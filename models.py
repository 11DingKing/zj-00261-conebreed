from sqlalchemy import Column, Integer, String, Date, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class BreedingMaterial(Base):
    __tablename__ = "breeding_materials"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    species = Column(String(100), nullable=False, default="青海云杉")
    mother_tree_source = Column(String(200), nullable=False)
    experiment_station = Column(String(100), nullable=False, index=True)
    generation = Column(Integer, nullable=False, default=1)
    target_traits = Column(String(200), nullable=False)
    current_stage = Column(String(50), nullable=False, default="初选")
    start_year = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)

    stage_records = relationship("StageRecord", back_populates="material", cascade="all, delete-orphan")
    certifications = relationship("CertificationRecord", back_populates="material", cascade="all, delete-orphan")
    variety = relationship("Variety", back_populates="material", uselist=False)


class StageRecord(Base):
    __tablename__ = "stage_records"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("breeding_materials.id"), nullable=False)
    stage_name = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    tree_height = Column(Float, nullable=True)
    diameter = Column(Float, nullable=True)
    survival_rate = Column(Float, nullable=True)
    cold_resistance_score = Column(Float, nullable=True)
    pest_resistance_score = Column(Float, nullable=True)
    growth_rate_score = Column(Float, nullable=True)
    observation_data = Column(Text, nullable=True)
    conclusion = Column(String(200), nullable=True)

    material = relationship("BreedingMaterial", back_populates="stage_records")

    __table_args__ = (UniqueConstraint('material_id', 'stage_name', name='_material_stage_uc'),)


class CertificationRecord(Base):
    __tablename__ = "certification_records"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("breeding_materials.id"), nullable=False)
    application_date = Column(Date, nullable=False)
    certification_level = Column(String(50), nullable=False, default="省级")
    status = Column(String(50), nullable=False, default="待审")
    result = Column(String(50), nullable=True)
    result_date = Column(Date, nullable=True)
    review_opinion = Column(Text, nullable=True)
    supplement_notes = Column(Text, nullable=True)

    material = relationship("BreedingMaterial", back_populates="certifications")


class Variety(Base):
    __tablename__ = "varieties"

    id = Column(Integer, primary_key=True, index=True)
    variety_number = Column(String(50), unique=True, nullable=False)
    material_id = Column(Integer, ForeignKey("breeding_materials.id"), nullable=False, unique=True)
    certification_date = Column(Date, nullable=False)
    national_certification_date = Column(Date, nullable=True)
    variety_name = Column(String(100), nullable=False)

    material = relationship("BreedingMaterial", back_populates="variety")
