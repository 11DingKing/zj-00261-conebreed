from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from enum import Enum


class StageEnum(str, Enum):
    primary = "初选"
    secondary = "复选"
    final = "决选"
    regional = "区域试验"


class CertificationStatusEnum(str, Enum):
    pending = "待审"
    reviewed = "已审"


class CertificationResultEnum(str, Enum):
    passed = "通过"
    rejected = "未通过"


class FamilyBase(BaseModel):
    code: str
    name: str
    species: str = "青海云杉"
    founder_id: Optional[int] = None
    description: Optional[str] = None


class FamilyCreate(FamilyBase):
    pass


class FamilyUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    founder_id: Optional[int] = None
    description: Optional[str] = None


class Family(FamilyBase):
    id: int

    class Config:
        from_attributes = True


class FamilySimple(BaseModel):
    id: int
    code: str
    name: str

    class Config:
        from_attributes = True


class BreedingMaterialBase(BaseModel):
    code: str
    species: str = "青海云杉"
    mother_tree_source: str
    experiment_station: str
    generation: int = 1
    target_traits: str
    current_stage: str = "初选"
    start_year: int
    description: Optional[str] = None
    mother_id: Optional[int] = None
    father_id: Optional[int] = None
    family_id: Optional[int] = None


class BreedingMaterialCreate(BreedingMaterialBase):
    pass


class BreedingMaterialUpdate(BaseModel):
    mother_tree_source: Optional[str] = None
    experiment_station: Optional[str] = None
    generation: Optional[int] = None
    target_traits: Optional[str] = None
    current_stage: Optional[str] = None
    start_year: Optional[int] = None
    description: Optional[str] = None
    mother_id: Optional[int] = None
    father_id: Optional[int] = None
    family_id: Optional[int] = None


class BreedingMaterialSimple(BaseModel):
    id: int
    code: str
    species: str
    generation: int
    current_stage: str

    class Config:
        from_attributes = True


class BreedingMaterial(BreedingMaterialBase):
    id: int

    class Config:
        from_attributes = True


class StageRecordBase(BaseModel):
    stage_name: str
    year: int
    tree_height: Optional[float] = None
    diameter: Optional[float] = None
    survival_rate: Optional[float] = None
    cold_resistance_score: Optional[float] = None
    pest_resistance_score: Optional[float] = None
    growth_rate_score: Optional[float] = None
    observation_data: Optional[str] = None
    conclusion: Optional[str] = None


class StageRecordCreate(StageRecordBase):
    material_id: int


class StageRecordUpdate(BaseModel):
    year: Optional[int] = None
    tree_height: Optional[float] = None
    diameter: Optional[float] = None
    survival_rate: Optional[float] = None
    cold_resistance_score: Optional[float] = None
    pest_resistance_score: Optional[float] = None
    growth_rate_score: Optional[float] = None
    observation_data: Optional[str] = None
    conclusion: Optional[str] = None


class StageRecord(StageRecordBase):
    id: int
    material_id: int

    class Config:
        from_attributes = True


class CertificationRecordBase(BaseModel):
    application_date: date
    certification_level: str = "省级"
    status: CertificationStatusEnum = CertificationStatusEnum.pending
    result: Optional[CertificationResultEnum] = None
    result_date: Optional[date] = None
    review_opinion: Optional[str] = None
    supplement_notes: Optional[str] = None


class CertificationRecordCreate(CertificationRecordBase):
    material_id: int


class CertificationRecordUpdate(BaseModel):
    status: Optional[CertificationStatusEnum] = None
    result: Optional[CertificationResultEnum] = None
    result_date: Optional[date] = None
    review_opinion: Optional[str] = None
    supplement_notes: Optional[str] = None


class CertificationRecord(CertificationRecordBase):
    id: int
    material_id: int

    class Config:
        from_attributes = True


class VarietyBase(BaseModel):
    variety_number: str
    material_id: int
    certification_date: date
    national_certification_date: Optional[date] = None
    variety_name: str


class VarietyCreate(VarietyBase):
    pass


class Variety(VarietyBase):
    id: int

    class Config:
        from_attributes = True


class BreedingMaterialDetail(BreedingMaterial):
    stage_records: List[StageRecord] = []
    certifications: List[CertificationRecord] = []
    variety: Optional[Variety] = None
    mother: Optional[BreedingMaterialSimple] = None
    father: Optional[BreedingMaterialSimple] = None
    family: Optional[FamilySimple] = None


class PedigreeNode(BaseModel):
    id: int
    code: str
    species: str
    generation: int
    current_stage: str
    mother_id: Optional[int] = None
    father_id: Optional[int] = None
    family_id: Optional[int] = None


class PedigreeTree(BaseModel):
    material: PedigreeNode
    ancestors: List[PedigreeNode] = []
    progeny: List[PedigreeNode] = []


class FamilyMaterialTrait(BaseModel):
    material_id: int
    material_code: str
    generation: int
    tree_height: Optional[float] = None
    diameter: Optional[float] = None
    survival_rate: Optional[float] = None
    cold_resistance_score: Optional[float] = None
    pest_resistance_score: Optional[float] = None
    growth_rate_score: Optional[float] = None
    stage_name: Optional[str] = None


class FamilyGeneticGainStats(BaseModel):
    family_id: int
    family_code: str
    family_name: str
    total_materials: int
    generations: List[int]
    traits: List[str]
    materials: List[FamilyMaterialTrait]
    generation_avg_gains: dict


class StationStats(BaseModel):
    experiment_station: str
    in_selection_count: int
    avg_breeding_years: float
    certified_count: int


class TraitStats(BaseModel):
    target_trait: str
    in_selection_count: int
    avg_breeding_years: float
    certified_count: int


class FamilyStats(BaseModel):
    family_id: int
    family_code: str
    family_name: str
    total_materials: int
    in_selection_count: int
    avg_breeding_years: float
    certified_count: int
    max_generation: int
