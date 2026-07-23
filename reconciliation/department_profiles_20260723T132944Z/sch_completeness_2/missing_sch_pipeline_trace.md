# Missing SCH Pipeline Traces

## CPEN 431

Representative:  — 2020_fall 431 1

| Stage | Result | Evidence |
|---|---|---|
| raw_schedule_record | found | {"Area of LLC": "", "CRN": "8067", "Capacity": "17", "Course": "CPEN 431", "Days": "MW", "Enrolled": "16", "Hours": "3", "Instructor": "Dali Wang", "Instructor Type": "Full Time", "Location": "Ferguson Center for the Arts 208", "Low Cost Textbook": "", "Seats Still Available": "1", "Section": "1", "Status": "OPEN", "Term": "Fall Semester 2020", "Time": "1000-1115", "Title": "Computer Engineering Design", "Type": "Lec"} |
| normalized_schedule | credit_conflict | {"observation_id": "f10a11ead983ef717e692be7853c5c8d3a5b3977fcbf5d97dfa9d14a9b9e3f47", "published_credit_values": ["3", "4"], "source_rows": [184, 7973]} |
| course_lookup | matched | ["CPEN", "431"] |
| credit_lookup | resolved_from_explicit_revision_pattern | {"evidence_key": "CPEN|431|2020_fall|2022_fall", "field": "credits", "later_stable_credit": 3.0, "method": "historical_credit_revision_resolution", "notes": "Later unambiguous observations unanimously publish one of two values preserved on the earlier repeated snapshots; the other explicit value is retained as the pre-revision credit.", "observation_id": "f10a11ead983ef717e692be7853c5c8d3a5b3977fcbf5d97dfa9d14a9b9e3f47", "published_conflicting_values": [3.0, 4.0], "section_key": "2020_fall|8067|CPEN|CPEN 431|1", "supporting_observation_id": "7c3565184d2c799c08c712d9b01a860b8587d35cf5f66c327227f9160069810c", "supporting_term": "2022_fall", "value": 4.0} |
| enrollment_lookup | explicit | 16 |
| sch_calculation | ready | 64.0 |

Working comparison: {"course_code": "CPEN 431", "credit_resolution_method": "direct_source_assertion", "credits": 3, "section": "1", "source_observation_id": "7c3565184d2c799c08c712d9b01a860b8587d35cf5f66c327227f9160069810c", "term": "2022_fall"}

## CPEN 498

Representative:  — 2020_fall 498 1

| Stage | Result | Evidence |
|---|---|---|
| raw_schedule_record | found | {"Area of LLC": "WI", "CRN": "8068", "Capacity": "19", "Course": "CPEN 498", "Days": "MWF", "Enrolled": "22", "Hours": "2", "Instructor": "Toni Riedl", "Instructor Type": "Full Time", "Location": "Joseph W. Luter III Hall 258", "Low Cost Textbook": "", "Seats Still Available": "-3", "Section": "1", "Status": "CLOSED", "Term": "Fall Semester 2020", "Time": "1300-1350", "Title": "Computer Engineering Capstn 2", "Type": "Ind"} |
| normalized_schedule | credit_conflict | {"observation_id": "1ff8bfcf4bf8376ca5ee48f74828dfbccffa4a42e7e9e882c1c891e735ae1936", "published_credit_values": ["2", "1"], "source_rows": [13728, 18907]} |
| course_lookup | matched | ["CPEN", "498"] |
| credit_lookup | resolved_from_explicit_revision_pattern | {"evidence_key": "CPEN|498|2020_fall|2023_spring", "field": "credits", "later_stable_credit": 2.0, "method": "historical_credit_revision_resolution", "notes": "Later unambiguous observations unanimously publish one of two values preserved on the earlier repeated snapshots; the other explicit value is retained as the pre-revision credit.", "observation_id": "1ff8bfcf4bf8376ca5ee48f74828dfbccffa4a42e7e9e882c1c891e735ae1936", "published_conflicting_values": [1.0, 2.0], "section_key": "2020_fall|8068|CPEN|CPEN 498|1", "supporting_observation_id": "e70ae592058f17541e39d91a166c70ef8cefc959463972114700b65cf4491b24", "supporting_term": "2023_spring", "value": 1.0} |
| enrollment_lookup | explicit | 22 |
| sch_calculation | ready | 22.0 |

Working comparison: {"course_code": "CPEN 498", "credit_resolution_method": "direct_source_assertion", "credits": 2, "section": "1", "source_observation_id": "e70ae592058f17541e39d91a166c70ef8cefc959463972114700b65cf4491b24", "term": "2023_spring"}

## EENG 498

Representative:  — 2020_fall 498 1

| Stage | Result | Evidence |
|---|---|---|
| raw_schedule_record | found | {"Area of LLC": "WI", "CRN": "8074", "Capacity": "16", "Course": "EENG 498", "Days": "MWF", "Enrolled": "15", "Hours": "2", "Instructor": "Jonathan Backens", "Instructor Type": "Full Time", "Location": "Joseph W. Luter III Hall 322", "Low Cost Textbook": "", "Seats Still Available": "1", "Section": "1", "Status": "OPEN", "Term": "Fall Semester 2020", "Time": "1300-1350", "Title": "Electrical Engineerng Capstn 2", "Type": "Ind"} |
| normalized_schedule | credit_conflict | {"observation_id": "3259d3c9046ca7c68ac69cd2f09bed23695fa12d4a2e378aa8a9c0543b2ccd39", "published_credit_values": ["2", "1"], "source_rows": [7663, 18237]} |
| course_lookup | matched | ["EENG", "498"] |
| credit_lookup | resolved_from_explicit_revision_pattern | {"evidence_key": "EENG|498|2020_fall|2022_fall", "field": "credits", "later_stable_credit": 2.0, "method": "historical_credit_revision_resolution", "notes": "Later unambiguous observations unanimously publish one of two values preserved on the earlier repeated snapshots; the other explicit value is retained as the pre-revision credit.", "observation_id": "3259d3c9046ca7c68ac69cd2f09bed23695fa12d4a2e378aa8a9c0543b2ccd39", "published_conflicting_values": [1.0, 2.0], "section_key": "2020_fall|8074|EENG|EENG 498|1", "supporting_observation_id": "238620a169518929b1581424d67cfe0e5fbe9fe2169f67936d029185fef4c2d3", "supporting_term": "2022_fall", "value": 1.0} |
| enrollment_lookup | explicit | 15 |
| sch_calculation | ready | 15.0 |

Working comparison: {"course_code": "EENG 498", "credit_resolution_method": "direct_source_assertion", "credits": 2, "section": "1", "source_observation_id": "238620a169518929b1581424d67cfe0e5fbe9fe2169f67936d029185fef4c2d3", "term": "2022_fall"}

## ENGL 491

Representative:  — 2020_fall 491 ON1

| Stage | Result | Evidence |
|---|---|---|
| raw_schedule_record | found | {"Area of LLC": "LETR", "CRN": "8752", "Capacity": "0", "Course": "ENGL 491", "Days": "", "Enrolled": "2", "Hours": "3", "Instructor": "Nicole Emmelhainz", "Instructor Type": "Full Time", "Location": "Synchronous Online Course ", "Low Cost Textbook": "", "Seats Still Available": "-2", "Section": "ON1", "Status": "CLOSED", "Term": "Fall Semester 2020", "Time": "-", "Title": "Internship in Writing", "Type": "Int"} |
| normalized_schedule | credit_conflict | {"observation_id": "5e0f06684a912568a84fd38c66df02b6be56de45843b56428cdbce7c91b43202", "published_credit_values": ["3", "1"], "source_rows": [8069, 8070]} |
| course_lookup | matched | ["ENGL", "491"] |
| credit_lookup | resolved_from_explicit_revision_pattern | {"evidence_key": "ENGL|491|2020_fall|2022_fall", "field": "credits", "later_stable_credit": 1.0, "method": "historical_credit_revision_resolution", "notes": "Later unambiguous observations unanimously publish one of two values preserved on the earlier repeated snapshots; the other explicit value is retained as the pre-revision credit.", "observation_id": "5e0f06684a912568a84fd38c66df02b6be56de45843b56428cdbce7c91b43202", "published_conflicting_values": [1.0, 3.0], "section_key": "2020_fall|8752|ENGL|ENGL 491|ON1", "supporting_observation_id": "1e3112489ac44d561f187972eba14591a191c69c7c99ba275ad838c437c197ad", "supporting_term": "2022_fall", "value": 3.0} |
| enrollment_lookup | explicit | 2 |
| sch_calculation | ready | 6.0 |

Working comparison: {"course_code": "ENGL 491", "credit_resolution_method": "direct_source_assertion", "credits": 1, "section": "1", "source_observation_id": "1e3112489ac44d561f187972eba14591a191c69c7c99ba275ad838c437c197ad", "term": "2022_fall"}

## HIST 295

Representative:  — 2022_fall 295 1M

| Stage | Result | Evidence |
|---|---|---|
| raw_schedule_record | found | {"Area of LLC": "", "CRN": "9240", "Capacity": "19", "Course": "HIST 295", "Days": "MW", "Enrolled": "12", "Hours": "3", "Instructor": "James Allegro", "Instructor Type": "Adjunct", "Location": "Lewis McMurran Hall 162", "Low Cost Textbook": "", "Seats Still Available": "7", "Section": "1M", "Status": "OPEN", "Term": "Fall Semester 2022", "Time": "1600-1715", "Title": "Special Topics", "Type": "Lec"} |
| normalized_schedule | credit_conflict | {"observation_id": "7f675c1ac9357c6f29ae7071784ea7bf22fc4d0a1eb0b45207ee0656dc35548e", "published_credit_values": ["3", "1"], "source_rows": [7534, 10213]} |
| course_lookup | matched | ["HIST", "295"] |
| credit_lookup | resolved_from_explicit_revision_pattern | {"evidence_key": "HIST|295|2022_fall|2025_spring", "field": "credits", "later_stable_credit": 1.0, "method": "historical_credit_revision_resolution", "notes": "Later unambiguous observations unanimously publish one of two values preserved on the earlier repeated snapshots; the other explicit value is retained as the pre-revision credit.", "observation_id": "7f675c1ac9357c6f29ae7071784ea7bf22fc4d0a1eb0b45207ee0656dc35548e", "published_conflicting_values": [1.0, 3.0], "section_key": "2022_fall|9240|HIST|HIST 295|1M", "supporting_observation_id": "4cd73a65171de6270aa603b6a1c9c728485fabf285031dba88763c7dee6ee7fa", "supporting_term": "2025_spring", "value": 3.0} |
| enrollment_lookup | explicit | 12 |
| sch_calculation | ready | 36.0 |

Working comparison: {"course_code": "HIST 295", "credit_resolution_method": "direct_source_assertion", "credits": 1, "section": "2", "source_observation_id": "4cd73a65171de6270aa603b6a1c9c728485fabf285031dba88763c7dee6ee7fa", "term": "2025_spring"}

## MATH 140

Representative:  — 2020_fall 140 1M

| Stage | Result | Evidence |
|---|---|---|
| raw_schedule_record | found | {"Area of LLC": "GE, LLF, LLFM, MATH", "CRN": "8263", "Capacity": "35", "Course": "MATH 140", "Days": "MTWRF", "Enrolled": "32", "Hours": "3", "Instructor": "Ryan Carpenter", "Instructor Type": "Full Time", "Location": "Lewis McMurran Hall 101", "Low Cost Textbook": "", "Seats Still Available": "3", "Section": "1M", "Status": "OPEN", "Term": "Fall Semester 2020", "Time": "0800-0850", "Title": "Calculus and Analytic Geometry", "Type": "Lec"} |
| normalized_schedule | credit_conflict | {"observation_id": "6dcb6a1a1da53d56e9173255a81c14df8d608c588f93818fc19b07464bca8d59", "published_credit_values": ["3", "4"], "source_rows": [3027, 8261]} |
| course_lookup | matched | ["MATH", "140"] |
| credit_lookup | resolved_from_explicit_revision_pattern | {"evidence_key": "MATH|140|2020_fall|2025_fall", "field": "credits", "later_stable_credit": 3.0, "method": "historical_credit_revision_resolution", "notes": "Later unambiguous observations unanimously publish one of two values preserved on the earlier repeated snapshots; the other explicit value is retained as the pre-revision credit.", "observation_id": "6dcb6a1a1da53d56e9173255a81c14df8d608c588f93818fc19b07464bca8d59", "published_conflicting_values": [3.0, 4.0], "section_key": "2020_fall|8263|MATH|MATH 140|1M", "supporting_observation_id": "2776944a6b786725582a40f40fa0041d6e7f7afdf3c84cf8abef03d68317f375", "supporting_term": "2025_fall", "value": 4.0} |
| enrollment_lookup | explicit | 32 |
| sch_calculation | ready | 128.0 |

Working comparison: {"course_code": "MATH 140", "credit_resolution_method": "direct_source_assertion", "credits": 3, "section": "1M", "source_observation_id": "2776944a6b786725582a40f40fa0041d6e7f7afdf3c84cf8abef03d68317f375", "term": "2025_fall"}

## MATH 240

Representative:  — 2020_fall 240 2

| Stage | Result | Evidence |
|---|---|---|
| raw_schedule_record | found | {"Area of LLC": "GE, LLF, LLFM, MATH", "CRN": "8272", "Capacity": "30", "Course": "MATH 240", "Days": "MW", "Enrolled": "25", "Hours": "3", "Instructor": "Hongwei Chen", "Instructor Type": "Full Time", "Location": "Joseph W. Luter III Hall 269", "Low Cost Textbook": "", "Seats Still Available": "5", "Section": "2", "Status": "OPEN", "Term": "Fall Semester 2020", "Time": "1000-1115", "Title": "Intermediate Calculus", "Type": "Lec"} |
| normalized_schedule | credit_conflict | {"observation_id": "1b3668cba8900c57e234f1c19c11588c33c340c16d0ab37f65c595f959d2640f", "published_credit_values": ["3", "4"], "source_rows": [7142, 7143, 9793, 17713]} |
| course_lookup | matched | ["MATH", "240"] |
| credit_lookup | resolved_from_explicit_revision_pattern | {"evidence_key": "MATH|240|2020_fall|2026_fall", "field": "credits", "later_stable_credit": 3.0, "method": "historical_credit_revision_resolution", "notes": "Later unambiguous observations unanimously publish one of two values preserved on the earlier repeated snapshots; the other explicit value is retained as the pre-revision credit.", "observation_id": "1b3668cba8900c57e234f1c19c11588c33c340c16d0ab37f65c595f959d2640f", "published_conflicting_values": [3.0, 4.0], "section_key": "2020_fall|8272|MATH|MATH 240|2", "supporting_observation_id": "22fcc26ae56758a6dbae48ed68b4ab51ea3b8f8ab6c408d229a94f9ecb6d922f", "supporting_term": "2026_fall", "value": 4.0} |
| enrollment_lookup | explicit | 25 |
| sch_calculation | ready | 100.0 |

Working comparison: {"course_code": "MATH 240", "credit_resolution_method": "direct_source_assertion", "credits": 3, "section": "3", "source_observation_id": "22fcc26ae56758a6dbae48ed68b4ab51ea3b8f8ab6c408d229a94f9ecb6d922f", "term": "2026_fall"}

## THEA 395

Representative:  — 2022_extended_summer 395 S10

| Stage | Result | Evidence |
|---|---|---|
| raw_schedule_record | found | {"Area of LLC": "LETR", "CRN": "4011", "Capacity": "16", "Course": "THEA 395", "Days": "", "Enrolled": "5", "Hours": "1", "Instructor": "Grace Godwin", "Instructor Type": "Full Time", "Location": "To Be Arranged ", "Low Cost Textbook": "", "Seats Still Available": "11", "Section": "S10", "Status": "OPEN", "Term": "Extended Summer 2022", "Time": "-", "Title": "Special Topics", "Type": "Lec"} |
| normalized_schedule | credit_conflict | {"observation_id": "9f866747b79e62fa651b8902347f3ed357f226ba500154662fac6e03a76ec565", "published_credit_values": ["1", "3"], "source_rows": [116, 18463]} |
| course_lookup | matched | ["THEA", "395"] |
| credit_lookup | resolved_from_explicit_revision_pattern | {"evidence_key": "THEA|395|2022_extended_summer|2026_spring", "field": "credits", "later_stable_credit": 1.0, "method": "historical_credit_revision_resolution", "notes": "Later unambiguous observations unanimously publish one of two values preserved on the earlier repeated snapshots; the other explicit value is retained as the pre-revision credit.", "observation_id": "9f866747b79e62fa651b8902347f3ed357f226ba500154662fac6e03a76ec565", "published_conflicting_values": [1.0, 3.0], "section_key": "2022_extended_summer|4011|THEA|THEA 395|S10", "supporting_observation_id": "e65683ac0ea92e6fc0b14ac15d4cafea02cbb58a53f1a31cefa976b53bf23928", "supporting_term": "2026_spring", "value": 3.0} |
| enrollment_lookup | explicit | 5 |
| sch_calculation | ready | 15.0 |

Working comparison: {"course_code": "THEA 395", "credit_resolution_method": "direct_source_assertion", "credits": 1, "section": "1", "source_observation_id": "e65683ac0ea92e6fc0b14ac15d4cafea02cbb58a53f1a31cefa976b53bf23928", "term": "2026_spring"}
