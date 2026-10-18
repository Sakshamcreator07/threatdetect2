from backend.app.database import SessionLocal, create_all, settings
from backend.app.demo import reset_demo_data


def main() -> None:
    create_all()
    assert SessionLocal is not None
    with SessionLocal() as db:
        reset_demo_data(db, settings)
        db.commit()
    print("Demo data reset complete.")


if __name__ == "__main__":
    main()
