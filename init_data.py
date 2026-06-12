from database import SessionLocal, engine, Base
import models
from datetime import date


def init_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(models.BreedingMaterial).count() > 0:
            print("数据已存在，跳过初始化")
            return

        materials = [
            {
                "code": "QHYS-2015-001",
                "species": "青海云杉",
                "mother_tree_source": "祁连山国家级自然保护区大野口母树林",
                "experiment_station": "龙渠良种基地",
                "generation": 2,
                "target_traits": "耐寒、速生",
                "current_stage": "区域试验",
                "start_year": 2015,
                "description": "大野口种群优良家系，耐寒性突出，生长量较对照高15%"
            },
            {
                "code": "QHYS-2018-007",
                "species": "青海云杉",
                "mother_tree_source": "东大山自然保护区一号母树林",
                "experiment_station": "龙渠良种基地",
                "generation": 1,
                "target_traits": "抗虫、速生",
                "current_stage": "决选",
                "start_year": 2018,
                "description": "东大山种群初选优良单株，对云杉叶锈病抗性较强"
            },
            {
                "code": "QHYS-2020-015",
                "species": "青海云杉",
                "mother_tree_source": "龙渠林场初选优树",
                "experiment_station": "龙渠良种基地",
                "generation": 1,
                "target_traits": "耐寒、抗虫",
                "current_stage": "复选",
                "start_year": 2020,
                "description": "本地优选家系，适应本地气候条件"
            },
            {
                "code": "QHYS-2022-023",
                "species": "青海云杉",
                "mother_tree_source": "祁连山国家公园冰沟河种群",
                "experiment_station": "龙渠良种基地",
                "generation": 1,
                "target_traits": "速生",
                "current_stage": "初选",
                "start_year": 2022,
                "description": "冰沟种群速生型单株，初选生长表现优异"
            },
            {
                "code": "QHYS-2008-003",
                "species": "青海云杉",
                "mother_tree_source": "寺大隆林场优良母树",
                "experiment_station": "龙渠良种基地",
                "generation": 3,
                "target_traits": "耐寒、速生、抗虫",
                "current_stage": "国家良种",
                "start_year": 2008,
                "description": "经多世代选育的优良家系，综合性状优良"
            },
            {
                "code": "QHYS-2010-012",
                "species": "青海云杉",
                "mother_tree_source": "西水自然保护区二号母树林",
                "experiment_station": "西水试验站",
                "generation": 2,
                "target_traits": "耐寒、抗虫",
                "current_stage": "区域试验",
                "start_year": 2010,
                "description": "西水种群耐寒抗虫家系，高海拔适应性强"
            },
            {
                "code": "QHYS-2016-009",
                "species": "青海云杉",
                "mother_tree_source": "马场垣试验林场优树",
                "experiment_station": "马场垣试验站",
                "generation": 1,
                "target_traits": "速生",
                "current_stage": "复选",
                "start_year": 2016,
                "description": "马场垣速生型单株，胸径生长量显著高于对照"
            }
        ]

        created_materials = []
        for m in materials:
            db_material = models.BreedingMaterial(**m)
            db.add(db_material)
            db.flush()
            created_materials.append(db_material)

        stage_records = [
            # QHYS-2015-001 区域试验阶段
            {"material_idx": 0, "stage_name": "初选", "year": 2015, "tree_height": 1.2, "survival_rate": 95.0,
             "cold_resistance_score": 8.5, "growth_rate_score": 7.8, "observation_data": "初选共120株，入选20株",
             "conclusion": "生长表现优良，入选复选"},
            {"material_idx": 0, "stage_name": "复选", "year": 2018, "tree_height": 3.5, "diameter": 6.2,
             "survival_rate": 92.0, "cold_resistance_score": 8.8, "growth_rate_score": 8.2,
             "observation_data": "复试验苗期3年，平均树高3.5m", "conclusion": "综合性状优良，入选决选"},
            {"material_idx": 0, "stage_name": "决选", "year": 2021, "tree_height": 6.8, "diameter": 11.5,
             "survival_rate": 90.0, "cold_resistance_score": 9.0, "growth_rate_score": 8.5,
             "pest_resistance_score": 7.5, "observation_data": "决选试验林5年生，生长量较对照高18%",
             "conclusion": "决选通过，进入区域试验"},
            {"material_idx": 0, "stage_name": "区域试验", "year": 2024, "tree_height": 9.2, "diameter": 15.8,
             "survival_rate": 88.0, "cold_resistance_score": 8.8, "growth_rate_score": 8.7,
             "pest_resistance_score": 7.8, "observation_data": "区域试验点3个，3年生试验林生长表现稳定",
             "conclusion": "区域试验表现良好，准备申报审定"},

            # QHYS-2018-007 决选阶段
            {"material_idx": 1, "stage_name": "初选", "year": 2018, "tree_height": 0.9, "survival_rate": 93.0,
             "pest_resistance_score": 8.5, "growth_rate_score": 8.0, "observation_data": "初选80株，入选15株",
             "conclusion": "抗虫性表现突出，入选复选"},
            {"material_idx": 1, "stage_name": "复选", "year": 2021, "tree_height": 3.0, "diameter": 5.5,
             "survival_rate": 90.0, "pest_resistance_score": 8.8, "growth_rate_score": 8.2,
             "observation_data": "复选4年生，叶锈病发病率低于对照30%", "conclusion": "抗虫性状稳定，入选决选"},
            {"material_idx": 1, "stage_name": "决选", "year": 2024, "tree_height": 5.8, "diameter": 10.0,
             "survival_rate": 87.0, "pest_resistance_score": 9.0, "growth_rate_score": 8.0,
             "cold_resistance_score": 7.5, "observation_data": "决选试验林6年生，抗虫性状稳定",
             "conclusion": "决选试验进行中"},

            # QHYS-2020-015 复选阶段
            {"material_idx": 2, "stage_name": "初选", "year": 2020, "tree_height": 0.8, "survival_rate": 96.0,
             "cold_resistance_score": 8.2, "pest_resistance_score": 8.0,
             "observation_data": "初选100株，入选25株", "conclusion": "本地适应性强，入选复选"},
            {"material_idx": 2, "stage_name": "复选", "year": 2023, "tree_height": 2.5, "diameter": 4.8,
             "survival_rate": 92.0, "cold_resistance_score": 8.5, "pest_resistance_score": 8.3,
             "observation_data": "复选3年生，越冬存活率95%以上", "conclusion": "复选试验进行中"},

            # QHYS-2022-023 初选阶段
            {"material_idx": 3, "stage_name": "初选", "year": 2022, "tree_height": 0.6, "survival_rate": 94.0,
             "growth_rate_score": 9.0, "observation_data": "初选60株，速生性状明显",
             "conclusion": "初选阶段生长表现优异"},

            # QHYS-2008-003 已审定良种
            {"material_idx": 4, "stage_name": "初选", "year": 2008, "tree_height": 1.0, "survival_rate": 94.0,
             "cold_resistance_score": 8.8, "growth_rate_score": 8.5, "pest_resistance_score": 8.0,
             "observation_data": "初选150株，入选30株", "conclusion": "综合性状优良，入选复选"},
            {"material_idx": 4, "stage_name": "复选", "year": 2012, "tree_height": 4.2, "diameter": 7.5,
             "survival_rate": 92.0, "cold_resistance_score": 9.0, "growth_rate_score": 8.8,
             "pest_resistance_score": 8.2, "observation_data": "复选4年生，平均树高4.2m",
             "conclusion": "性状表现优异，入选决选"},
            {"material_idx": 4, "stage_name": "决选", "year": 2016, "tree_height": 8.5, "diameter": 14.2,
             "survival_rate": 90.0, "cold_resistance_score": 9.2, "growth_rate_score": 9.0,
             "pest_resistance_score": 8.5, "observation_data": "决选8年生，生长量超对照22%",
             "conclusion": "决选通过，进入区域试验"},
            {"material_idx": 4, "stage_name": "区域试验", "year": 2020, "tree_height": 12.5, "diameter": 20.0,
             "survival_rate": 88.0, "cold_resistance_score": 9.0, "growth_rate_score": 9.0,
             "pest_resistance_score": 8.5, "observation_data": "区域试验5个试点，4年生试验林表现稳定",
             "conclusion": "区域试验通过，可申报审定"},

            # QHYS-2010-012 区域试验阶段
            {"material_idx": 5, "stage_name": "初选", "year": 2010, "tree_height": 1.1, "survival_rate": 95.0,
             "cold_resistance_score": 9.0, "pest_resistance_score": 8.2,
             "observation_data": "初选100株，入选20株", "conclusion": "高海拔适应性强，入选复选"},
            {"material_idx": 5, "stage_name": "复选", "year": 2014, "tree_height": 3.8, "diameter": 6.8,
             "survival_rate": 93.0, "cold_resistance_score": 9.2, "pest_resistance_score": 8.5,
             "observation_data": "复选4年生，海拔2800m试验点存活率92%",
             "conclusion": "耐寒抗虫性状稳定，入选决选"},
            {"material_idx": 5, "stage_name": "决选", "year": 2018, "tree_height": 7.2, "diameter": 12.0,
             "survival_rate": 90.0, "cold_resistance_score": 9.3, "pest_resistance_score": 8.8,
             "observation_data": "决选8年生，高海拔试验点表现突出",
             "conclusion": "决选通过，进入区域试验"},
            {"material_idx": 5, "stage_name": "区域试验", "year": 2022, "tree_height": 10.0, "diameter": 16.5,
             "survival_rate": 88.0, "cold_resistance_score": 9.0, "pest_resistance_score": 8.5,
             "observation_data": "区域试验4个试点，4年生试验林",
             "conclusion": "区域试验进行中"},

            # QHYS-2016-009 复选阶段
            {"material_idx": 6, "stage_name": "初选", "year": 2016, "tree_height": 1.0, "survival_rate": 92.0,
             "growth_rate_score": 9.2, "observation_data": "初选80株，入选15株",
             "conclusion": "速生性状明显，入选复选"},
            {"material_idx": 6, "stage_name": "复选", "year": 2020, "tree_height": 3.8, "diameter": 7.0,
             "survival_rate": 88.0, "growth_rate_score": 9.0,
             "observation_data": "复选4年生，胸径生长量超对照25%",
             "conclusion": "复选试验进行中"}
        ]

        for sr in stage_records:
            material_id = created_materials[sr["material_idx"]].id
            record_data = {k: v for k, v in sr.items() if k != "material_idx"}
            db_record = models.StageRecord(material_id=material_id, **record_data)
            db.add(db_record)

        certifications = [
            # QHYS-2008-003 省级审定通过
            {
                "material_idx": 4,
                "application_date": date(2021, 3, 15),
                "certification_level": "省级",
                "status": "已审",
                "result": "通过",
                "result_date": date(2021, 12, 20),
                "review_opinion": "经多世代选育，综合性状优良，区域试验表现稳定，同意通过省级审定",
                "supplement_notes": None
            },
            # QHYS-2008-003 国家级审定通过
            {
                "material_idx": 4,
                "application_date": date(2022, 4, 10),
                "certification_level": "国家级",
                "status": "已审",
                "result": "通过",
                "result_date": date(2022, 10, 15),
                "review_opinion": "经多区域试点验证，性状表现稳定优良，同意通过国家级林木良种审定",
                "supplement_notes": None
            },
            # QHYS-2015-001 准备申报
            {
                "material_idx": 0,
                "application_date": date(2025, 5, 10),
                "certification_level": "省级",
                "status": "待审",
                "result": None,
                "result_date": None,
                "review_opinion": None,
                "supplement_notes": None
            }
        ]

        for cert in certifications:
            material_id = created_materials[cert["material_idx"]].id
            cert_data = {k: v for k, v in cert.items() if k != "material_idx"}
            db_cert = models.CertificationRecord(material_id=material_id, **cert_data)
            db.add(db_cert)

        varieties = [
            {
                "variety_number": "国S-SV-PP-001-2022",
                "material_idx": 4,
                "certification_date": date(2021, 12, 20),
                "national_certification_date": date(2022, 10, 15),
                "variety_name": "龙祁云杉1号"
            }
        ]

        for v in varieties:
            material_id = created_materials[v["material_idx"]].id
            variety_data = {k: val for k, val in v.items() if k != "material_idx"}
            db_variety = models.Variety(material_id=material_id, **variety_data)
            db.add(db_variety)

        db.commit()
        print(f"初始化完成：{len(created_materials)}份选育材料，{len(stage_records)}条阶段记录，"
              f"{len(certifications)}条审定记录，{len(varieties)}个良种")

    finally:
        db.close()


if __name__ == "__main__":
    init_data()
