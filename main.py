from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date

from database import engine, get_db, Base
import models
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="龙渠良种基地选育档案管理系统", version="1.0.0")


# ==================== 选育材料接口 ====================

@app.post("/materials/", response_model=schemas.BreedingMaterial, summary="创建选育材料")
def create_material(material: schemas.BreedingMaterialCreate, db: Session = Depends(get_db)):
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.code == material.code
    ).first()
    if db_material:
        raise HTTPException(status_code=400, detail="材料编号已存在")
    db_material = models.BreedingMaterial(**material.model_dump())
    db.add(db_material)
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
    db: Session = Depends(get_db)
):
    query = db.query(models.BreedingMaterial)
    if experiment_station:
        query = query.filter(models.BreedingMaterial.experiment_station == experiment_station)
    if current_stage:
        query = query.filter(models.BreedingMaterial.current_stage == current_stage)
    if target_trait:
        query = query.filter(models.BreedingMaterial.target_traits.contains(target_trait))
    return query.offset(skip).limit(limit).all()


@app.get("/materials/{material_id}", response_model=schemas.BreedingMaterialDetail, summary="获取选育材料详情")
def get_material(material_id: int, db: Session = Depends(get_db)):
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="选育材料不存在")
    return db_material


@app.put("/materials/{material_id}", response_model=schemas.BreedingMaterial, summary="更新选育材料")
def update_material(material_id: int, material: schemas.BreedingMaterialUpdate, db: Session = Depends(get_db)):
    db_material = db.query(models.BreedingMaterial).filter(
        models.BreedingMaterial.id == material_id
    ).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="选育材料不存在")
    update_data = material.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_material, key, value)
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
    db.delete(db_material)
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

    existing = db.query(models.StageRecord).filter(
        models.StageRecord.material_id == record.material_id,
        models.StageRecord.stage_name == record.stage_name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该阶段记录已存在")

    db_record = models.StageRecord(**record.model_dump())
    db.add(db_record)
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
    update_data = record.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_record, key, value)
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
    db.delete(db_record)
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
    db_cert = models.CertificationRecord(**cert.model_dump())
    db.add(db_cert)
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
    update_data = cert.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_cert, key, value)
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

    existing_material = db.query(models.Variety).filter(
        models.Variety.material_id == variety.material_id
    ).first()
    if existing_material:
        raise HTTPException(status_code=400, detail="该材料已有良种编号")

    db_variety = models.Variety(**variety.model_dump())
    db.add(db_variety)
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


# ==================== 统计接口 ====================

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

        in_selection = [m for m in materials if m.current_stage != "审定通过"]
        certified_count = db.query(models.Variety).join(models.BreedingMaterial).filter(
            models.BreedingMaterial.experiment_station == station
        ).count()

        total_years = sum(2026 - m.start_year for m in materials)
        avg_years = round(total_years / len(materials), 1) if materials else 0

        result.append({
            "experiment_station": station,
            "in_selection_count": len(in_selection),
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

        in_selection = [m for m in materials if m.current_stage != "审定通过"]
        certified_count = db.query(models.Variety).join(models.BreedingMaterial).filter(
            models.BreedingMaterial.target_traits.contains(trait)
        ).count()

        total_years = sum(2026 - m.start_year for m in materials)
        avg_years = round(total_years / len(materials), 1) if materials else 0

        result.append({
            "target_trait": trait,
            "in_selection_count": len(in_selection),
            "avg_breeding_years": avg_years,
            "certified_count": certified_count
        })
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
