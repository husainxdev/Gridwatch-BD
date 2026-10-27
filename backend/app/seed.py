"""Idempotent demo-only seed. No real accounts, official notices or feeder claims."""

import uuid

from sqlalchemy import select

from .config import get_settings
from .db import SessionLocal
from .models import DemoArea


def main():
    settings = get_settings()
    if settings.app_env not in {"development", "test"} or not settings.demo_enabled:
        raise SystemExit("Demo seed requires development/test and DEMO_ENABLED=true")
    with SessionLocal.begin() as db:
        for number, name in enumerate(["নমুনা এলাকা ক", "নমুনা এলাকা খ"], 1):
            key = uuid.uuid5(uuid.NAMESPACE_URL, f"gridwatch:demo:area:{number}")
            if db.scalar(select(DemoArea).where(DemoArea.id == key)) is None:
                db.add(
                    DemoArea(
                        id=key,
                        name_bn=name,
                        description="সিলেট পাইলটের ইন্টারফেস প্রদর্শন। এটি বাস্তব প্রশাসনিক এলাকা বা ফিডার ম্যাপিং নয়।",
                        sort_order=number,
                    )
                )
    print("Demo seed complete: two fictional areas; operational tables unchanged.")


if __name__ == "__main__":
    main()
