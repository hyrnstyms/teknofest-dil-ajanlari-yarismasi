from fastapi import APIRouter, Depends, HTTPException
from backend.app.auth.dependencies import CurrentUser, get_current_user
from backend.app.auth.principals import DEMO_USERS
from backend.app.demo.scenarios import DemoScenarioService, demo_enabled

router = APIRouter(prefix="/api/demo", tags=["demo"])

def enabled():
    if not demo_enabled(): raise HTTPException(status_code=404, detail={"code": "demo_mode_disabled", "message": "Demo yardımcıları kapalı."})

def registry(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    enabled()
    if user.role != "EVRAK_KAYIT": raise HTTPException(status_code=403, detail={"code": "action_forbidden", "message": "Demo senaryolarını evrak kayıt personeli hazırlar."})
    return user

@router.get("/personas", dependencies=[Depends(enabled)])
def personas(): return {"items": [{"user_key": p.user_key, "name": p.name, "role": p.role, "institution_id": p.institution_id, "department_code": p.department_code} for p in DEMO_USERS.values()]}

@router.post("/citizen-examples/{scenario_key}", dependencies=[Depends(enabled)])
def prepare_citizen_example(scenario_key: str):
    labels = {
        "yol_onarim": "Yol Onarım Başvurusunu Görüntüle",
        "eksik_adres": "Bilgi Bekleyen Başvuruyu Görüntüle",
        "tamamlanmis_dosya": "Sonuçlanmış Başvuruyu Görüntüle",
    }
    if scenario_key not in labels:
        raise HTTPException(status_code=404, detail={"code": "demo_case_not_found", "message": "Örnek vatandaş başvurusu bulunamadı."})
    result = DemoScenarioService().prepare(scenario_key, "belediye")
    return {"label": labels[scenario_key], "scenario_key": scenario_key, "case": result["case"], "citizen_url": result["citizen_url"]}

@router.get("/scenarios")
def scenarios(user: CurrentUser = Depends(registry)): return {"items": DemoScenarioService().list(user.institution_id)}

@router.post("/scenarios/{scenario_key}/prepare")
def prepare(scenario_key: str, user: CurrentUser = Depends(registry)):
    try: return DemoScenarioService().prepare(scenario_key, user.institution_id)
    except KeyError as exc: raise HTTPException(status_code=404, detail={"code": "scenario_not_found", "message": "Demo senaryosu bulunamadı."}) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail={"code": "institution_scope_violation", "message": "Demo senaryosu aktif kurum kapsamında değil."}) from exc

@router.post("/scenarios/reset")
def reset(_: CurrentUser = Depends(registry)): return DemoScenarioService().reset()

@router.get("/cases/{case_id}/citizen-access")
def citizen_access(case_id: str, user: CurrentUser = Depends(registry)):
    service = DemoScenarioService()
    for row in service.list(user.institution_id):
        existing = service._existing(row["key"])
        if existing and existing.id == case_id: return service._result(existing, row["key"], created=False)
    raise HTTPException(status_code=404, detail={"code": "demo_case_not_found", "message": "Demo vatandaş bağlantısı bulunamadı."})
