"""Offline source/equation ledger checks. No web access, estimation or graduation verdict."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse

LEVELS={'ABSTRACT','SECTIONS','PDF_PARSED_SECTIONS','METADATA','OFFICIAL_TEXT','OFFICIAL_CODE','FULL_TEXT'}
TYPES={'JOURNAL_ARTICLE','PERSPECTIVE','WORKING_PAPER','OFFICIAL_DATA_NOTE','OFFICIAL_MODEL_DOCUMENTATION','POLICY_DOCUMENT'}


def unpack(library):
    columns=library['columns']
    required={'id','title','publication_type','url','reading_level','parts_read','limits','doi'}
    if not required.issubset(columns): raise ValueError('missing required columns')
    if len(set(columns)) != len(columns): raise ValueError('duplicate columns')
    if any(len(row)!=len(columns) for row in library['records']):raise ValueError('row width mismatch')
    return [dict(zip(columns,row)) for row in library['records']]


def validate(library,blueprint):
    errors=[]
    try: records=unpack(library)
    except (ValueError,KeyError,TypeError) as exc:return [f'INVALID_LIBRARY:{exc}']
    ids=[r['id'] for r in records]
    if not ids or len(set(ids))!=len(ids):errors.append('EMPTY_OR_DUPLICATE_SOURCES')
    seen=set()
    for r in records:
        ident=r['id'];doi=r.get('doi')
        if not r.get('title') or not r.get('parts_read') or not r.get('limits'):errors.append(f'INCOMPLETE_EVIDENCE:{ident}')
        if r.get('reading_level') not in LEVELS:errors.append(f'INVALID_READING_LEVEL:{ident}')
        if r.get('publication_type') not in TYPES:errors.append(f'INVALID_PUBLICATION_TYPE:{ident}')
        u=urlparse(r.get('url',''))
        if u.scheme!='https' or not u.netloc:errors.append(f'INVALID_SOURCE_URL:{ident}')
        if doi:
            canonical=doi.lower().strip()
            if not canonical.startswith('10.') or '/' not in canonical:errors.append(f'INVALID_DOI:{ident}')
            if canonical in seen:errors.append(f'DUPLICATE_DOI:{ident}')
            seen.add(canonical)
    full=sum(r['reading_level']=='FULL_TEXT' for r in records)
    if full!=library.get('full_text_read_count'):errors.append('FULL_TEXT_COUNT_MISMATCH')
    policies={r['id'] for r in records if r['publication_type']=='POLICY_DOCUMENT'}
    times=library.get('policy_timelines',[])
    if set(t['id'] for t in times)!=policies or len(times)!=len(policies):errors.append('POLICY_TIMELINE_COVERAGE')
    cutoff=date(2025,9,30)
    for t in times:
        parsed={}
        for k in ('issued_date','public_date','effective_date'):
            if t.get(k):
                try:parsed[k]=date.fromisoformat(t[k])
                except (ValueError,TypeError):errors.append(f'INVALID_POLICY_DATE:{t["id"]}:{k}')
        if t.get('date_conflict') and (t.get('issued_date') or not t.get('conflict_source') or len(t.get('issued_date_candidates',[]))<2):errors.append(f'CONFLICT_HIDDEN:{t["id"]}')
        if t.get('historical_sample_relation')=='AFTER_FROZEN_SAMPLE' and parsed.get('effective_date'):
            if parsed['effective_date']<=cutoff:errors.append(f'WRONG_AFTER_SAMPLE:{t["id"]}')
    rel=blueprint.get('relations',[]);rids=[r['id'] for r in rel]
    if not rel or len(rids)!=len(set(rids)) or len(rel)!=blueprint.get('relation_group_count'):errors.append('RELATION_COUNT_OR_DUPLICATE')
    for r in rel:
        if not r.get('sources') or not set(r['sources']).issubset(ids):errors.append(f'UNKNOWN_RELATION_SOURCE:{r["id"]}')
        if r.get('source_role')!='CONCEPT_BOUNDARY_OR_METHOD_NOT_VERBATIM_EQUATION':errors.append(f'UNVERIFIED_EXACT_ATTRIBUTION:{r["id"]}')
        if r.get('status')!='DRAFT_NOT_ESTIMATED':errors.append(f'UNVERIFIED_RELATION_RESULT:{r["id"]}')
    if blueprint.get('estimated') or blueprint.get('calibrated') or library.get('empirical_estimation'):errors.append('EMPIRICAL_CLAIM_WITHOUT_RUN')
    if blueprint.get('free_parameter_count') is not None:errors.append('UNFROZEN_PARAMETER_COUNT')
    if blueprint.get('closure_choice')!='PENDING':errors.append('UNAPPROVED_CLOSURE_CHOICE')
    for group in blueprint.get('incompatible_active_groups',[]):
        if not set(group).issubset(rids):errors.append('UNKNOWN_INCOMPATIBLE_GROUP')
    return errors


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=ap.parse_args()
    try:
        lib=json.loads((args.root/'data/metadata/industry_literature_library_20260918.json').read_text(encoding='utf-8-sig'))
        bp=json.loads((args.root/'configs/industry_equation_blueprint_v2.json').read_text(encoding='utf-8-sig'))
        errors=validate(lib,bp);rows=unpack(lib)
        result={'status':'PASS' if not errors else 'FAIL','errors':errors,'sources':len(rows),'by_type':dict(Counter(x['publication_type'] for x in rows)),'by_reading':dict(Counter(x['reading_level'] for x in rows)),'relation_groups':len(bp['relations']),'scope':'OFFLINE_METADATA_CHECK_ONLY','scientific_validity_certified':False}
    except (OSError,ValueError,KeyError,TypeError) as exc:result={'status':'FAIL','errors':[str(exc)]}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='PASS' else 2

if __name__=='__main__':raise SystemExit(main())
