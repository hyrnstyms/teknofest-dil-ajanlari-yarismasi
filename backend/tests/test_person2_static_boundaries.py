from pathlib import Path


INTELLIGENCE_DIR = Path(__file__).resolve().parents[1] / "app" / "intelligence"


def test_person2_intelligence_has_no_database_imports():
    forbidden = (
        "backend.app.db",
        "sqlalchemy",
        "from backend.app.cases",
    )
    for path in INTELLIGENCE_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8").casefold()
        for token in forbidden:
            assert token.casefold() not in source, f"{token} found in {path.name}"


def test_preview_router_is_mounted_once_by_integrated_main():
    main_path = INTELLIGENCE_DIR.parent / "main.py"
    source = main_path.read_text(encoding="utf-8")
    assert source.count("from backend.app.intelligence.preview_router import") == 1
    assert source.count("app.include_router(ai_preview_router, dependencies=[Depends(get_current_user)])") == 1
