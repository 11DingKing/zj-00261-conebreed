# 龙渠良种基地选育档案管理系统 — 阶段流转与审定晋升设计说明

## 一、系统全景

本系统管理青海云杉良种选育全生命周期，核心业务线为：

> 选育材料创建 → 阶段观测记录推进 → 审定申报 → 良种编号分配 → 国家良种晋升

五张核心数据表构成业务骨架：

| 表 | 模型 | 职责 |
|---|---|---|
| `families` | `Family` | 家系分组，可追溯始祖材料 |
| `breeding_materials` | `BreedingMaterial` | 选育材料主表，`current_stage` 由系统自动计算 |
| `stage_records` | `StageRecord` | 每个选育阶段的观测数据快照 |
| `certification_records` | `CertificationRecord` | 省级/国家级审定申报与结果 |
| `varieties` | `Variety` | 良种编号，含省级审定日期与国家级审定日期 |

---

## 二、选育阶段流转

### 2.1 阶段定义

系统定义了 6 种阶段状态，分为两组：

```
选育中阶段（IN_SELECTION_STAGES）：初选 → 复选 → 决选 → 区域试验
终态阶段（FINAL_STAGES）         ：审定通过、国家良种
```

对应代码常量见 [main.py](file:///Users/ding/Documents/SOLOCODE%203/0612/macmini/zj-00261-conebreed-5/main.py#L15-L17)：

```python
STAGE_ORDER = ["初选", "复选", "决选", "区域试验"]
IN_SELECTION_STAGES = {"初选", "复选", "决选", "区域试验"}
FINAL_STAGES = {"审定通过", "国家良种"}
```

### 2.2 阶段记录如何挂载

每条 `StageRecord` 通过 `material_id` 外键挂到选育材料上，**每个材料每个阶段只能有一条记录**（由 `_material_stage_uc` 唯一约束保证，见 [models.py#L69](file:///Users/ding/Documents/SOLOCODE%203/0612/macmini/zj-00261-conebreed-5/models.py#L69)）。

一条阶段记录承载的信息：

| 字段 | 含义 | 录入时机 |
|---|---|---|
| `stage_name` | 初选/复选/决选/区域试验 | 创建阶段记录时指定 |
| `year` | 该阶段观测年份 | 与实际观测年度对应 |
| `tree_height` | 树高 (m) | 各阶段均可采集 |
| `diameter` | 胸径 (cm) | 复选及以后阶段才有 |
| `survival_rate` | 存活率 (%) | 各阶段均可采集 |
| `cold_resistance_score` | 耐寒性评分 | 按需采集 |
| `pest_resistance_score` | 抗虫性评分 | 按需采集 |
| `growth_rate_score` | 生长速率评分 | 按需采集 |
| `observation_data` | 自由文本观测记录 | 各阶段补充说明 |
| `conclusion` | 阶段结论 | 如"入选复选"、"决选通过"等 |

### 2.3 状态如何往前推——`recalculate_material_stage`

材料的 `current_stage` **不可由用户直接修改**（见 [main.py#L343](file:///Users/ding/Documents/SOLOCODE%203/0612/macmini/zj-00261-conebreed-5/main.py#L343) 的校验），而是由系统函数 `recalculate_material_stage` 在每次数据变更后自动重算。

重算逻辑的优先级（见 [main.py#L65-L94](file:///Users/ding/Documents/SOLOCODE%203/0612/macmini/zj-00261-conebreed-5/main.py#L65-L94)）：

```
1. 先查 Variety 表
   ├─ 有记录 且 national_certification_date 非空 → "国家良种"
   └─ 有记录 但 national_certification_date 为空 → "审定通过"

2. 再查 CertificationRecord 表
   └─ 存在 status="已审" 且 result="通过" 的记录 → "审定通过"

3. 最后查 StageRecord 表
   ├─ 有阶段记录 → 取 STAGE_ORDER 中最大索引对应的阶段名
   └─ 无任何阶段记录 → "初选"（默认值）
```

**关键结论**：阶段推进的驱动力是 **写入 StageRecord**。给材料创建一条"复选"的阶段记录，材料的 `current_stage` 就会被自动推到"复选"。而审定相关状态则由审定记录和良种编号记录驱动，优先级高于阶段记录。

### 2.4 写入阶段记录的约束

创建/修改/删除阶段记录时，系统会做以下校验（见 [main.py#L399-L477](file:///Users/ding/Documents/SOLOCODE%203/0612/macmini/zj-00261-conebreed-5/main.py#L399-L477)）：

1. **材料已进入终态（审定通过/国家良种）或已分配良种编号 → 禁止新增/修改/删除阶段记录**
2. **同一材料同一阶段 → 禁止重复创建**（由数据库唯一约束兜底）

---

## 三、审定晋升线

### 3.1 两条审定线

系统支持两种审定级别：

| 级别 | `certification_level` 值 | 含义 |
|---|---|---|
| 省级审定 | `"省级"` | 由省级林木品种审定委员会审定 |
| 国家级审定 | `"国家级"` | 由国家林木品种审定委员会审定 |

一条 `CertificationRecord` 包含：

| 字段 | 含义 |
|---|---|
| `application_date` | 申报日期 |
| `certification_level` | 省级 / 国家级 |
| `status` | 待审 / 已审 |
| `result` | 通过 / 未通过 |
| `result_date` | 审定结果日期 |
| `review_opinion` | 审定意见 |
| `supplement_notes` | 补充说明 |

### 3.2 审定线与选育线的衔接点

**衔接发生在"区域试验"之后。** 一份材料走完初选→复选→决选→区域试验四个阶段后，进入审定通道：

```
区域试验（选育最后阶段）
     │
     │  申报审定（POST /certifications/）
     ▼
省级审定（CertificationRecord: level=省级, status=待审）
     │
     │  审定结果录入（PUT /certifications/{id}, status=已审, result=通过）
     ▼
审定通过（current_stage 自动变为 "审定通过"）
     │
     │  分配良种编号（POST /varieties/assign）
     ▼
获得良种编号（Variety 记录创建, variety_number 全局唯一）
     │
     │  国家级审定通过 + 录入 national_certification_date
     ▼
国家良种（current_stage 自动变为 "国家良种"）
```

### 3.3 良种编号分配的前置条件

分配良种编号（`POST /varieties/assign`）有严格的前置校验（见 [main.py#L533-L570](file:///Users/ding/Documents/SOLOCODE%203/0612/macmini/zj-00261-conebreed-5/main.py#L533-L570)）：

1. `variety_number` 必须全局唯一
2. 该材料必须尚未分配良种编号
3. **必须有审定通过的记录**（`status="已审"` 且 `result="通过"`）
4. 如果提交时带了 `national_certification_date`，则还必须有 **国家级审定通过** 的记录

### 3.4 审定记录的修改约束

- 材料已分配良种编号 → 禁止修改审定记录
- 材料已进入终态或已有良种编号 → 禁止重复申报审定

---

## 四、完整状态流转图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         选育材料生命周期                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  创建材料（current_stage 默认="初选"）                                    │
│       │                                                                 │
│       ▼                                                                 │
│  ┌────────┐   写入初选StageRecord   ┌────────┐   写入复选StageRecord    │
│  │  初选  │ ──────────────────────→ │  复选  │ ─────────────────────→   │
│  └────────┘                         └────────┘                          │
│                                           │                             │
│       ┌───────────────────────────────────┘                             │
│       ▼                                                                 │
│  ┌────────┐   写入决选StageRecord   ┌──────────┐                       │
│  │  决选  │ ─────────────────────→ │ 区域试验  │                       │
│  └────────┘                         └──────────┘                       │
│                                           │                             │
│                  ═══════ 衔接点 ═══════     │                             │
│                                           ▼                             │
│                                 申报省级审定                               │
│                                    (CertificationRecord)                │
│                                    level=省级, status=待审               │
│                                           │                             │
│                              ┌────────────┴────────────┐                │
│                              ▼                         ▼                │
│                         result=通过               result=未通过           │
│                              │                    (留在区域试验)          │
│                              ▼                                         │
│                      ┌──────────┐                                      │
│                      │ 审定通过  │  ← current_stage 自动重算              │
│                      └──────────┘                                      │
│                           │                                            │
│            分配良种编号(POST /varieties/assign)                         │
│            variety_number 全局唯一                                      │
│                           │                                            │
│                           ▼                                            │
│                    Variety 记录创建                                      │
│            certification_date = 省级审定通过日期                          │
│                           │                                            │
│              ┌────────────┴────────────┐                                │
│              ▼                         ▼                                │
│    national_certification_date     national_certification_date          │
│          为空                        有值                                │
│              │                         │                                │
│              ▼                         ▼                                │
│        仍为"审定通过"            ┌──────────┐                             │
│                                │ 国家良种  │                             │
│                                └──────────┘                             │
│                                                                         │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│  注: 虚线以下为"终态"，进入后不可再新增/修改/删除阶段记录                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 五、统计口径数据来源

### 5.1 按试验站统计 — `GET /stats/by-station`

| 输出字段 | 计算方式 |
|---|---|
| `experiment_station` | `BreedingMaterial.experiment_station` GROUP BY |
| `in_selection_count` | 该站下 `current_stage ∈ IN_SELECTION_STAGES` 且无 Variety 记录的材料数 |
| `avg_breeding_years` | 该站下仍在选中的材料的 `当前年份 - start_year` 之均值 |
| `certified_count` | 该站下 Variety 表中存在记录的材料数（JOIN BreedingMaterial） |

### 5.2 按选育目标统计 — `GET /stats/by-trait`

遍历三个固定关键词 `["耐寒", "速生", "抗虫"]`，对每个关键词：

| 输出字段 | 计算方式 |
|---|---|
| `target_trait` | 当前遍历的关键词 |
| `in_selection_count` | `target_traits.contains(trait)` 且在选中且无 Variety |
| `avg_breeding_years` | 同上材料的 `当前年份 - start_year` 均值 |
| `certified_count` | `target_traits.contains(trait)` 且有 Variety 记录 |

注意：`target_traits` 字段是自由文本（如 `"耐寒、速生"`），系统用 SQLite 的 `contains` 做子串匹配，因此一份材料可能同时被"耐寒"和"速生"两个口径统计到。

### 5.3 按家系统计 — `GET /stats/by-family`

| 输出字段 | 计算方式 |
|---|---|
| `total_materials` | `family_id` 等于该家系的材料总数 |
| `in_selection_count` | 同上，在选中且无 Variety |
| `avg_breeding_years` | 同上，选育年限均值 |
| `certified_count` | 同上，有 Variety 记录 |
| `max_generation` | 该家系下材料的最大 `generation` 值 |

### 5.4 家系遗传增益横向对比 — `GET /stats/family/{family_id}/genetic-gain`

这是最复杂的统计接口，流程为：

1. 取该家系下所有材料，按 `generation` 和 `code` 排序
2. 对每个材料取其 **最新阶段记录**（`_get_latest_stage_record`：在 STAGE_ORDER 中取索引最大的那条）
3. 提取 6 项性状指标（树高、胸径、存活率、耐寒性、抗虫性、生长速率）
4. 按 generation 分组计算各性状均值
5. 以最低世代为基准，计算后续各世代相对基准的增益百分比：

```
gain_percent = (当前世代均值 - 基准世代均值) / 基准世代均值 × 100%
```

---

## 六、关键设计要点速查

| 要点 | 说明 |
|---|---|
| `current_stage` 不可直接改 | 更新接口会拒绝携带 `current_stage` 的请求，由 `recalculate_material_stage` 自动维护 |
| 每阶段唯一一条记录 | `stage_records` 表的 `_material_stage_uc` 约束保证 |
| 终态锁定 | 一旦进入"审定通过"或"国家良种"，禁止对阶段记录做增删改 |
| 良种编号全局唯一 | `varieties.variety_number` 字段有 unique 约束 |
| 审定通过才可分配编号 | `_has_passed_certification` 校验 `status="已审"` 且 `result="通过"` |
| 国家良种需国家级审定 | 分配编号时若带 `national_certification_date`，需有国家级审定通过记录 |
| 每次数据变更触发重算 | 创建/修改/删除阶段记录、审定记录、良种编号后均调用 `recalculate_material_stage` |
