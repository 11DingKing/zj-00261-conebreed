from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Set
from datetime import date

from database import engine, get_db, Base
import models
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="龙渠良种基地选育档案管理系统", version="2.0.0")

STAGE_ORDER = ["初选", "复选", "决选", "区域试验"]
IN_SELECTION_STAGES = {"初选", "复选", "决选", "区域试验"}
FINAL_STAGES = {"审定通过", "国家良种"}
CERT_STATUS_REVIEWED = "已审"
CERT_RESULT_PASSED = "通过"
CERT_LEVEL_NATIONAL = "国家级"
TRAIT_FIELDS = [
    "tree_height", "diameter", "survival_rate",
    "cold_resistance_score", "pest_resistance_score", "growth_rate_score"
]
TRAIT_LABELS = {
    "tree_height": "树高",
    "diameter": "胸径",
    "survival_rate": "存活率",
    "cold_resistance_score": "耐寒性评分",
    "pest_resistance_score": "抗虫性评分",
    "growth_rate_score": "生长速率评分"
}


def _has_passed_certification(db: Session, material_id: int, level: Optional[str] = None) -> bool:
    query = db.query(models.CertificationRecord).filter(
        models.CertificationRecord.material_id == material_id,
        models.CertificationRecord.result == CERT_RESULT_PASSED,
        models.CertificationRecord.status == CERT_STATUS_REVIEWED
    )
    if level:
        query = query.filter(models.CertificationRecord.certification_level == level)
    return query.first() is not None


def _has_variety(db: Session, material_id: int) -> bool:
    return db.query(models.Variety).filter(
        models.Variety.material_id == material_id
    ).first() is not None


def _is_material_in_selection(db: Session, material_id: int) -> bool:
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if not db_material:
        return False
    if db_material.current_stage in FINAL_STAGES:
        return False
    if _has_variety(db, material_id):
        return False
    return True


def recalculate_material_stage(db: Session, material_id: int) -> None:
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if not db_material:
        return

    variety = db.query(models.Variety).filter(
        models.Variety.material_id == material_id
    ).first()
    if variety is not None:
        if variety.national_certification_date:
            db_material.current_stage = "国家良种"
        else:
            db_material.current_stage = "审定通过"
        return

    if _has_passed_certification(db, material_id):
        db_material.current_stage = "审定通过"
        return

    stage_records = db.query(models.StageRecord).filter(
        models.StageRecord.material_id == material_id
    ).all()
    recorded_stages = {sr.stage_name for sr in stage_records if sr.stage_name in STAGE_ORDER}
    if recorded_stages:
        max_idx = max(STAGE_ORDER.index(s) for s in recorded_stages)
        db_material.current_stage = STAGE_ORDER[max_idx]
    else:
        db_material.current_stage = "初选"


def _validate_parent_ids(db: Session, mother_id: Optional[int], father_id: Optional[int],
                         material_id: Optional[int] = None) -> None:
    if mother_id is not None:
        if material_id and mother_id == material_id:
            raise HTTPException(status_code=400, detail="母本不能是材料自身")
        mother = db.query(models.BreedingMaterial).filter(
            models.BreedingMaterial.id == mother_id
        ).first()
        if not mother:
            raise HTTPException(status_code=404, detail=f"母本材料(id={mother_id})不存在")
    if father_id is not None:
        if material_id and father_id == material_id:
            raise HTTPException(status_code=400, detail="父本不能是材料自身")
        father = db.query(models.BreedingMaterial).filter(
            models.BreedingMaterial.id == father_id
        ).first()
        if not father:
            raise HTTPException(status_code=404, detail=f"父本材料(id={father_id})不存在")
    if mother_id and father_id and mother_id == father_id:
        raise HTTPException(status_code=400, detail="母本和父本不能是同一份材料")


def _validate_family_id(db: Session, family_id: Optional[int]) -> None:
    if family_id is not None:
        family = db.query(models.Family).filter(
            models.Family.id == family_id
        ).first()
        if not family:
            raise HTTPException(status_code=404, detail=f"家系(id={family_id})不存在")


def _get_ancestors(db: Session, material_id: int, visited: Optional[Set[int]] = None) -> List[models.BreedingMaterial]:
    if visited is None:
        visited = set()
    if material_id in visited:
        return []
    visited.add(material_id)

    material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if not material:
        return []

    ancestors = []
    if material.mother_id:
        mother = db.query(models.BreedingMaterial).filter(
            models.BreedingMaterial.id == material.mother_id
        ).first()
        if mother:
            ancestors.append(mother)
            ancestors.extend(_get_ancestors(db, mother.id, visited))
    if material.father_id:
        father = db.query(models.BreedingMaterial).filter(
            models.BreedingMaterial.id == material.father_id
        ).first()
        if father:
            ancestors.append(father)
            ancestors.extend(_get_ancestors(db, father.id, visited))
    return ancestors


def _get_progeny(db: Session, material_id: int, visited: Optional[Set[int]] = None) -> List[models.BreedingMaterial]:
    if visited is None:
        visited = set()
    if material_id in visited:
        return []
    visited.add(material_id)

    progeny = db.query(models.BreedingMaterial).filter(
        (models.BreedingMaterial.mother_id == material_id) |
        (models.BreedingMaterial.father_id == material_id)
    ).all()

    all_progeny = list(progeny)
    for p in progeny:
        all_progeny.extend(_get_progeny(db, p.id, visited))
    return all_progeny


def _get_latest_stage_record(db: Session, material_id: int) -> Optional[models.StageRecord]:
    stage_records = db.query(models.StageRecord).filter(
        models.StageRecord.material_id == material_id
    ).all()
    if not stage_records:
        return None
    in_order = [sr for sr in stage_records if sr.stage_name in STAGE_ORDER]
    if not in_order:
        return stage_records[0]
    max_idx = max(STAGE_ORDER.index(sr.stage_name) for sr in in_order)
    max_stage = STAGE_ORDER[max_idx]
    for sr in in_order:
        if sr.stage_name == max_stage:
            return sr
    return None


def _recalculate_family_stats(db: Session, family_id: int) -> None:
    family = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not family:
        return
    db.flush()


def recalculate_family_on_pedigree_change(db: Session, material_id: int,
                                          old_family_id: Optional[int] = None,
                                          new_family_id: Optional[int] = None) -> None:
    affected_family_ids = set()
    if old_family_id:
        affected_family_ids.add(old_family_id)
    if new_family_id:
        affected_family_ids.add(new_family_id)

    material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if material and material.family_id:
        affected_family_ids.add(material.family_id)

    for fid in affected_family_ids:
        _recalculate_family_stats(db, fid)


# ==================== 选育材料接口 ====================

@app.post("/materials/", response_model=schemas.BreedingMaterial, summary="创建选育材料")
def create_material(material: schemas.BreedingMaterialCreate, db: Session = Depends(get_db)):
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.code == material.code
    ).first()
    if db_material:
        raise HTTPException(status_code=400, detail="材料编号已存在")
    _validate_parent_ids(db, material.mother_id, material.father_id)
    _validate_family_id(db, material.family_id)
    db_material = models.BreedingMaterial(**material.model_dump())
    db.add(db_material)
    db.flush()
    recalculate_material_stage(db, db_material.id)
    recalculate_family_on_pedigree_change(db, db_material.id, new_family_id=material.family_id)
    db.commit()
    db.refresh(db_material)
    return db_material


@app.get("/materials/", response_model=List[schemas.BreedingMaterial], summary="查询选育材料列表")
def list_materials(
    skip: int = 0,
    limit: int = 100,
    experiment_station: Optional[str] = None,
    current_stage: Optional[str] = None,
    target_trait: Optional[str] = None,
    family_id: Optional[int] = None,
    generation: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.BreedingMaterial)
    if experiment_station:
        query = query.filter(models.BreedingMaterial.experiment_station == experiment_station)
    if current_stage:
        query = query.filter(models.BreedingMaterial.current_stage == current_stage)
        if current_stage in IN_SELECTION_STAGES:
            query = query.outerjoin(models.Variety).filter(models.Variety.id.is_(None))
    if target_trait:
        query = query.filter(models.BreedingMaterial.target_traits.contains(target_trait))
    if family_id:
        query = query.filter(models.BreedingMaterial.family_id == family_id)
    if generation:
        query = query.filter(models.BreedingMaterial.generation == generation)
    return query.offset(skip).limit(limit).all()


@app.get("/materials/{material_id}", response_model=schemas.BreedingMaterialDetail, summary="获取选育材料详情")
def get_material(material_id: int, db: Session = Depends(get_db)):
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="选育材料不存在")
    return db_material


@app.get("/materials/{material_id}/pedigree", response_model=schemas.PedigreeTree, summary="获取材料谱系树")
def get_material_pedigree(material_id: int, db: Session = Depends(get_db)):
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="选育材料不存在")

    material_node = schemas.PedigreeNode(
        id=db_material.id,
        code=db_material.code,
        species=db_material.species,
        generation=db_material.generation,
        current_stage=db_material.current_stage,
        mother_id=db_material.mother_id,
        father_id=db_material.father_id,
        family_id=db_material.family_id
    )

    ancestors = _get_ancestors(db, material_id)
    ancestor_nodes = [
        schemas.PedigreeNode(
            id=m.id,
            code=m.code,
            species=m.species,
            generation=m.generation,
            current_stage=m.current_stage,
            mother_id=m.mother_id,
            father_id=m.father_id,
            family_id=m.family_id
        )
        for m in ancestors
    ]

    progeny = _get_progeny(db, material_id)
    progeny_nodes = [
        schemas.PedigreeNode(
            id=m.id,
            code=m.code,
            species=m.species,
            generation=m.generation,
            current_stage=m.current_stage,
            mother_id=m.mother_id,
            father_id=m.father_id,
            family_id=m.family_id
        )
        for m in progeny
    ]

    return schemas.PedigreeTree(
        material=material_node,
        ancestors=ancestor_nodes,
        progeny=progeny_nodes
    )


@app.put("/materials/{material_id}", response_model=schemas.BreedingMaterial, summary="更新选育材料")
def update_material(material_id: int, material: schemas.BreedingMaterialUpdate, db: Session = Depends(get_db)):
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="选育材料不存在")
    update_data = material.model_dump(exclude_unset=True)
    if "current_stage" in update_data:
        raise HTTPException(status_code=400, detail="current_stage 字段不可直接修改，系统将根据阶段记录和审定记录自动计算")

    old_family_id = db_material.family_id
    new_mother_id = update_data.get("mother_id", db_material.mother_id)
    new_father_id = update_data.get("father_id", db_material.father_id)
    new_family_id = update_data.get("family_id", db_material.family_id)

    _validate_parent_ids(db, new_mother_id, new_father_id, material_id=material_id)
    _validate_family_id(db, new_family_id)

    for key, value in update_data.items():
        setattr(db_material, key, value)

    db.flush()
    recalculate_material_stage(db, material_id)
    recalculate_family_on_pedigree_change(db, material_id,
                                          old_family_id=old_family_id,
                                          new_family_id=new_family_id)
    db.commit()
    db.refresh(db_material)
    return db_material


@app.delete("/materials/{material_id}", summary="删除选育材料")
def delete_material(material_id: int, db: Session = Depends(get_db)):
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="选育材料不存在")

    old_family_id = db_material.family_id

    progeny = db.query(models.BreedingMaterial).filter(
        (models.BreedingMaterial.mother_id == material_id) |
        (models.BreedingMaterial.father_id == material_id)
    ).all()
    for p in progeny:
        if p.mother_id == material_id:
            p.mother_id = None
        if p.father_id == material_id:
            p.father_id = None

    db.delete(db_material)
    db.flush()

    if old_family_id:
        recalculate_family_on_pedigree_change(db, material_id, old_family_id=old_family_id)

    db.commit()
    return {"message": "删除成功"}


# ==================== 选育阶段记录接口 ====================

@app.post("/stage-records/", response_model=schemas.StageRecord, summary="创建选育阶段记录")
def create_stage_record(record: schemas.StageRecordCreate, db: Session = Depends(get_db)):
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == record.material_id
    ).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="选育材料不存在")

    if db_material.current_stage in FINAL_STAGES or _has_variety(db, record.material_id):
        raise HTTPException(status_code=400, detail="该材料已完成审定，不可新增阶段记录")

    existing = db.query(models.StageRecord).filter(
        models.StageRecord.material_id == record.material_id,
        models.StageRecord.stage_name == record.stage_name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该阶段记录已存在")

    db_record = models.StageRecord(**record.model_dump())
    db.add(db_record)
    db.flush()
    recalculate_material_stage(db, record.material_id)
    recalculate_family_on_pedigree_change(db, record.material_id)
    db.commit()
    db.refresh(db_record)
    return db_record


@app.get("/materials/{material_id}/stage-records/", response_model=List[schemas.StageRecord], summary="获取材料的阶段记录")
def list_stage_records(material_id: int, db: Session = Depends(get_db)):
    return db.query(models.StageRecord).filter(
        models.StageRecord.material_id == material_id
    ).order_by(models.StageRecord.year).all()


@app.put("/stage-records/{record_id}", response_model=schemas.StageRecord, summary="更新阶段记录")
def update_stage_record(record_id: int, record: schemas.StageRecordUpdate, db: Session = Depends(get_db)):
    db_record = db.query(models.StageRecord).filter(
        models.StageRecord.id == record_id
    ).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="阶段记录不存在")
    material_id = db_record.material_id
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if db_material and (db_material.current_stage in FINAL_STAGES or _has_variety(db, material_id)):
        raise HTTPException(status_code=400, detail="该材料已完成审定，不可修改阶段记录")

    update_data = record.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_record, key, value)
    db.flush()
    recalculate_material_stage(db, material_id)
    recalculate_family_on_pedigree_change(db, material_id)
    db.commit()
    db.refresh(db_record)
    return db_record


@app.delete("/stage-records/{record_id}", summary="删除阶段记录")
def delete_stage_record(record_id: int, db: Session = Depends(get_db)):
    db_record = db.query(models.StageRecord).filter(
        models.StageRecord.id == record_id
    ).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="阶段记录不存在")
    material_id = db_record.material_id
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if db_material and (db_material.current_stage in FINAL_STAGES or _has_variety(db, material_id)):
        raise HTTPException(status_code=400, detail="该材料已完成审定，不可删除阶段记录")

    db.delete(db_record)
    db.flush()
    recalculate_material_stage(db, material_id)
    recalculate_family_on_pedigree_change(db, material_id)
    db.commit()
    return {"message": "删除成功"}


# ==================== 审定记录接口 ====================

@app.post("/certifications/", response_model=schemas.CertificationRecord, summary="申报审定")
def create_certification(cert: schemas.CertificationRecordCreate, db: Session = Depends(get_db)):
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == cert.material_id
    ).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="选育材料不存在")
    if db_material.current_stage in FINAL_STAGES or _has_variety(db, cert.material_id):
        raise HTTPException(status_code=400, detail="该材料已完成审定，不可重复申报")
    db_cert = models.CertificationRecord(**cert.model_dump())
    db.add(db_cert)
    db.flush()
    recalculate_material_stage(db, cert.material_id)
    recalculate_family_on_pedigree_change(db, cert.material_id)
    db.commit()
    db.refresh(db_cert)
    return db_cert


@app.get("/materials/{material_id}/certifications/", response_model=List[schemas.CertificationRecord], summary="获取材料的审定记录")
def list_certifications(material_id: int, db: Session = Depends(get_db)):
    return db.query(models.CertificationRecord).filter(
        models.CertificationRecord.material_id == material_id
    ).order_by(models.CertificationRecord.application_date.desc()).all()


@app.put("/certifications/{cert_id}", response_model=schemas.CertificationRecord, summary="更新审定结果")
def update_certification(cert_id: int, cert: schemas.CertificationRecordUpdate, db: Session = Depends(get_db)):
    db_cert = db.query(models.CertificationRecord).filter(
        models.CertificationRecord.id == cert_id
    ).first()
    if not db_cert:
        raise HTTPException(status_code=404, detail="审定记录不存在")
    material_id = db_cert.material_id
    if _has_variety(db, material_id):
        raise HTTPException(status_code=400, detail="该材料已分配良种编号，不可修改审定记录")

    update_data = cert.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_cert, key, value)

    db.flush()
    recalculate_material_stage(db, material_id)
    recalculate_family_on_pedigree_change(db, material_id)
    db.commit()
    db.refresh(db_cert)
    return db_cert


# ==================== 良种编号接口 ====================

@app.post("/varieties/assign", response_model=schemas.Variety, summary="分配良种编号（审定通过后）")
def assign_variety_number(variety: schemas.VarietyCreate, db: Session = Depends(get_db)):
    existing_num = db.query(models.Variety).filter(
        models.Variety.variety_number == variety.variety_number
    ).first()
    if existing_num:
        raise HTTPException(status_code=400, detail="良种编号已存在，不可重复")

    if _has_variety(db, variety.material_id):
        raise HTTPException(status_code=400, detail="该材料已有良种编号")

    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == variety.material_id
    ).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="选育材料不存在")

    if not _has_passed_certification(db, variety.material_id):
        raise HTTPException(
            status_code=400,
            detail=f"该材料无有效的审定通过记录（需状态为'{CERT_STATUS_REVIEWED}'且结果为'{CERT_RESULT_PASSED}'），无法分配良种编号"
        )

    if variety.national_certification_date:
        if not _has_passed_certification(db, variety.material_id, level=CERT_LEVEL_NATIONAL):
            raise HTTPException(
                status_code=400,
                detail=f"分配国家良种需提供{CERT_LEVEL_NATIONAL}审定通过记录（需状态为'{CERT_STATUS_REVIEWED}'且结果为'{CERT_RESULT_PASSED}'）"
            )

    db_variety = models.Variety(**variety.model_dump())
    db.add(db_variety)
    db.flush()
    recalculate_material_stage(db, variety.material_id)
    recalculate_family_on_pedigree_change(db, variety.material_id)
    db.commit()
    db.refresh(db_variety)
    return db_variety


@app.get("/varieties/", response_model=List[schemas.Variety], summary="查询良种列表")
def list_varieties(
    skip: int = 0,
    limit: int = 100,
    experiment_station: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Variety)
    if experiment_station:
        query = query.join(models.BreedingMaterial).filter(
            models.BreedingMaterial.experiment_station == experiment_station
        )
    return query.offset(skip).limit(limit).all()


@app.get("/varieties/{variety_id}", response_model=schemas.Variety, summary="获取良种详情")
def get_variety(variety_id: int, db: Session = Depends(get_db)):
    db_variety = db.query(models.Variety).filter(models.Variety.id == variety_id).first()
    if not db_variety:
        raise HTTPException(status_code=404, detail="良种不存在")
    return db_variety


# ==================== 家系管理接口 ====================

@app.post("/families/", response_model=schemas.Family, summary="创建家系")
def create_family(family: schemas.FamilyCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Family).filter(
        models.Family.code == family.code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="家系编号已存在")
    if family.founder_id:
        founder = db.query(models.BreedingMaterial).filter(
            models.BreedingMaterial.id == family.founder_id
        ).first()
        if not founder:
            raise HTTPException(status_code=404, detail=f"始祖材料(id={family.founder_id})不存在")
    db_family = models.Family(**family.model_dump())
    db.add(db_family)
    db.commit()
    db.refresh(db_family)
    return db_family


@app.get("/families/", response_model=List[schemas.Family], summary="查询家系列表")
def list_families(
    skip: int = 0,
    limit: int = 100,
    species: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Family)
    if species:
        query = query.filter(models.Family.species == species)
    return query.offset(skip).limit(limit).all()


@app.get("/families/{family_id}", response_model=schemas.Family, summary="获取家系详情")
def get_family(family_id: int, db: Session = Depends(get_db)):
    db_family = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not db_family:
        raise HTTPException(status_code=404, detail="家系不存在")
    return db_family


@app.put("/families/{family_id}", response_model=schemas.Family, summary="更新家系信息")
def update_family(family_id: int, family: schemas.FamilyUpdate, db: Session = Depends(get_db)):
    db_family = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not db_family:
        raise HTTPException(status_code=404, detail="家系不存在")
    update_data = family.model_dump(exclude_unset=True)
    if "founder_id" in update_data and update_data["founder_id"] is not None:
        founder = db.query(models.BreedingMaterial).filter(
            models.BreedingMaterial.id == update_data["founder_id"]
        ).first()
        if not founder:
            raise HTTPException(status_code=404, detail=f"始祖材料(id={update_data['founder_id']})不存在")
    for key, value in update_data.items():
        setattr(db_family, key, value)
    db.commit()
    db.refresh(db_family)
    return db_family


@app.delete("/families/{family_id}", summary="删除家系")
def delete_family(family_id: int, db: Session = Depends(get_db)):
    db_family = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not db_family:
        raise HTTPException(status_code=404, detail="家系不存在")
    materials = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.family_id == family_id
    ).all()
    for m in materials:
        m.family_id = None
    db.delete(db_family)
    db.commit()
    return {"message": "删除成功"}


@app.get("/families/{family_id}/materials", response_model=List[schemas.BreedingMaterial],
         summary="获取家系下的所有选育材料")
def list_family_materials(family_id: int, db: Session = Depends(get_db)):
    db_family = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not db_family:
        raise HTTPException(status_code=404, detail="家系不存在")
    return db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.family_id == family_id
    ).order_by(models.BreedingMaterial.generation, models.BreedingMaterial.code).all()


@app.get("/families/{family_id}/pedigree-tree", summary="获取家系完整谱系树")
def get_family_pedigree_tree(family_id: int, db: Session = Depends(get_db)):
    db_family = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not db_family:
        raise HTTPException(status_code=404, detail="家系不存在")
    materials = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.family_id == family_id
    ).all()

    nodes = []
    for m in materials:
        nodes.append({
            "id": m.id,
            "code": m.code,
            "generation": m.generation,
            "current_stage": m.current_stage,
            "mother_id": m.mother_id,
            "father_id": m.father_id
        })

    return {
        "family_id": db_family.id,
        "family_code": db_family.code,
        "family_name": db_family.name,
        "total_materials": len(materials),
        "nodes": nodes
    }


# ==================== 统计接口 ====================

def _count_in_selection(db: Session, materials: List[models.BreedingMaterial]) -> int:
    count = 0
    for m in materials:
        if m.current_stage in IN_SELECTION_STAGES:
            if not _has_variety(db, m.id):
                count += 1
    return count


@app.get("/stats/by-station", response_model=List[schemas.StationStats], summary="按试验站统计")
def stats_by_station(db: Session = Depends(get_db)):
    stations = db.query(
        models.BreedingMaterial.experiment_station,
        func.count(models.BreedingMaterial.id).label("total_count")
    ).group_by(models.BreedingMaterial.experiment_station).all()

    result = []
    for station, _ in stations:
        materials = db.query(models.BreedingMaterial).filter(
            models.BreedingMaterial.experiment_station == station
        ).all()

        in_selection_count = _count_in_selection(db, materials)
        certified_count = db.query(models.Variety).join(models.BreedingMaterial).filter(
            models.BreedingMaterial.experiment_station == station
        ).count()

        total_years = sum(2026 - m.start_year for m in materials)
        avg_years = round(total_years / len(materials), 1) if materials else 0

        result.append({
            "experiment_station": station,
            "in_selection_count": in_selection_count,
            "avg_breeding_years": avg_years,
            "certified_count": certified_count
        })
    return result


@app.get("/stats/by-trait", response_model=List[schemas.TraitStats], summary="按选育目标统计")
def stats_by_trait(db: Session = Depends(get_db)):
    trait_keywords = ["耐寒", "速生", "抗虫"]
    result = []

    for trait in trait_keywords:
        materials = db.query(models.BreedingMaterial).filter(
            models.BreedingMaterial.target_traits.contains(trait)
        ).all()

        in_selection_count = _count_in_selection(db, materials)
        certified_count = db.query(models.Variety).join(models.BreedingMaterial).filter(
            models.BreedingMaterial.target_traits.contains(trait)
        ).count()

        total_years = sum(2026 - m.start_year for m in materials)
        avg_years = round(total_years / len(materials), 1) if materials else 0

        result.append({
            "target_trait": trait,
            "in_selection_count": in_selection_count,
            "avg_breeding_years": avg_years,
            "certified_count": certified_count
        })
    return result


@app.get("/stats/by-family", response_model=List[schemas.FamilyStats], summary="按家系统计")
def stats_by_family(db: Session = Depends(get_db)):
    families = db.query(models.Family).all()
    result = []

    for family in families:
        materials = db.query(models.BreedingMaterial).filter(
            models.BreedingMaterial.family_id == family.id
        ).all()

        if not materials:
            result.append({
                "family_id": family.id,
                "family_code": family.code,
                "family_name": family.name,
                "total_materials": 0,
                "in_selection_count": 0,
                "avg_breeding_years": 0.0,
                "certified_count": 0,
                "max_generation": 0
            })
            continue

        in_selection_count = _count_in_selection(db, materials)
        certified_count = db.query(models.Variety).join(models.BreedingMaterial).filter(
            models.BreedingMaterial.family_id == family.id
        ).count()

        total_years = sum(2026 - m.start_year for m in materials)
        avg_years = round(total_years / len(materials), 1)
        max_gen = max(m.generation for m in materials)

        result.append({
            "family_id": family.id,
            "family_code": family.code,
            "family_name": family.name,
            "total_materials": len(materials),
            "in_selection_count": in_selection_count,
            "avg_breeding_years": avg_years,
            "certified_count": certified_count,
            "max_generation": max_gen
        })
    return result


@app.get("/stats/family/{family_id}/genetic-gain",
         response_model=schemas.FamilyGeneticGainStats,
         summary="家系内遗传增益横向对比")
def stats_family_genetic_gain(family_id: int, db: Session = Depends(get_db)):
    family = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not family:
        raise HTTPException(status_code=404, detail="家系不存在")

    materials = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.family_id == family_id
    ).order_by(models.BreedingMaterial.generation, models.BreedingMaterial.code).all()

    if not materials:
        return schemas.FamilyGeneticGainStats(
            family_id=family.id,
            family_code=family.code,
            family_name=family.name,
            total_materials=0,
            generations=[],
            traits=[],
            materials=[],
            generation_avg_gains={}
        )

    material_traits = []
    all_traits = set()
    all_generations = set()

    for m in materials:
        all_generations.add(m.generation)
        latest_record = _get_latest_stage_record(db, m.id)
        trait_data = {
            "material_id": m.id,
            "material_code": m.code,
            "generation": m.generation,
            "stage_name": latest_record.stage_name if latest_record else None
        }
        for field in TRAIT_FIELDS:
            val = getattr(latest_record, field) if latest_record else None
            trait_data[field] = val
            if val is not None:
                all_traits.add(field)
        material_traits.append(schemas.FamilyMaterialTrait(**trait_data))

    sorted_generations = sorted(all_generations)
    sorted_traits = sorted(all_traits, key=lambda x: TRAIT_FIELDS.index(x))

    generation_avg_gains = {}
    if len(sorted_generations) >= 2:
        gen_trait_avgs = {}
        for gen in sorted_generations:
            gen_materials = [mt for mt in material_traits if mt.generation == gen]
            gen_avgs = {}
            for trait in sorted_traits:
                vals = [getattr(mt, trait) for mt in gen_materials if getattr(mt, trait) is not None]
                if vals:
                    gen_avgs[trait] = round(sum(vals) / len(vals), 2)
            gen_trait_avgs[gen] = gen_avgs

        base_gen = sorted_generations[0]
        gains_by_gen = {}
        for gen in sorted_generations[1:]:
            gen_gains = {}
            for trait in sorted_traits:
                base_val = gen_trait_avgs.get(base_gen, {}).get(trait)
                curr_val = gen_trait_avgs.get(gen, {}).get(trait)
                if base_val is not None and curr_val is not None and base_val != 0:
                    gain_pct = round((curr_val - base_val) / base_val * 100, 2)
                    gen_gains[trait] = {
                        "base_value": base_val,
                        "current_value": curr_val,
                        "gain_percent": gain_pct
                    }
            gains_by_gen[f"G{gen}"] = gen_gains
        generation_avg_gains = gains_by_gen

    return schemas.FamilyGeneticGainStats(
        family_id=family.id,
        family_code=family.code,
        family_name=family.name,
        total_materials=len(materials),
        generations=sorted_generations,
        traits=[TRAIT_LABELS.get(t, t) for t in sorted_traits],
        materials=material_traits,
        generation_avg_gains=generation_avg_gains
    )


@app.post("/stats/family/{family_id}/recalculate", summary="重算家系统计数据")
def recalculate_family_stats(family_id: int, db: Session = Depends(get_db)):
    family = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not family:
        raise HTTPException(status_code=404, detail="家系不存在")
    _recalculate_family_stats(db, family_id)
    db.commit()
    return {"message": "家系统计数据重算完成", "family_id": family_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
